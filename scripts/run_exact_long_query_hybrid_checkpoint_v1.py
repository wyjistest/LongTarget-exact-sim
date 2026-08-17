#!/usr/bin/env python3
"""Run and audit the clean exact long-query hybrid checkpoint."""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/exact_long_query_hybrid_checkpoint_v1/checkpoint_fixtures.tsv"
DEFAULT_PROMOTER_CONTRACT = ROOT / "docs/exact_long_query_hybrid_checkpoint_v1/production_promoter_contract.json"
BENCHMARK_SOURCE_COMMIT = "61da9b6f1b3d998043d512f5703dc95671d2383e"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
RUNTIME_PATHS = (
    "cuda/prealign_cuda.cu",
    "cuda/prealign_cuda.h",
    "cuda/prealign_cuda_stub.cpp",
    "fasim/Fasim-LongTarget.cpp",
    "fasim/fastsim.h",
    "fasim/gasal2_align_bridge.cpp",
    "fasim/gasal2_align_bridge.h",
    "fasim/gasal2_align_bridge_stub.cpp",
    "fasim/ssw.h",
    "fasim/sswNew.cpp",
    "fasim/ssw_cpp.cpp",
    "fasim/ssw_cpp.h",
)
MODES = ("lite", "tfosorted")
FALLBACK_METRICS = (
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks",
    "benchmark.fasim_gasal2_fallbacks",
)
CANDIDATE_ENV = {
    "FASIM_ALIGN_GASAL2": "1",
    "FASIM_ENABLE_PREALIGN_CUDA": "1",
    "FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE": "1",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "2812",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION": "1",
}


class CheckpointError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckpointError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None and rows, f"empty TSV: {path}")
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return rows


def fasta_length(path: Path) -> int:
    total = 0
    records = 0
    with path.open("r", encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith(">"):
                records += 1
            elif line:
                require(records == 1, f"sequence before or after the sole FASTA record: {path}")
                require(set(line.upper()) <= set("ACGTN"), f"invalid FASTA base: {path}")
                total += len(line)
    require(records == 1 and total > 0, f"expected one non-empty FASTA record: {path}")
    return total


def command_output(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()


def validate_runtime_identity() -> dict[str, object]:
    subprocess.run(["git", "cat-file", "-e", f"{BENCHMARK_SOURCE_COMMIT}^{{commit}}"], cwd=ROOT, check=True)
    status = subprocess.run(
        ["git", "diff", "--quiet", BENCHMARK_SOURCE_COMMIT, "--", *RUNTIME_PATHS],
        cwd=ROOT,
    )
    require(status.returncode == 0, "runtime-path source differs from benchmark source commit")
    tree_rows = []
    for relative in RUNTIME_PATHS:
        path = ROOT / relative
        tree_rows.append({"path": relative, "sha256": sha256_file(path)})
    return {
        "benchmark_source_commit": BENCHMARK_SOURCE_COMMIT,
        "checkpoint_harness_commit": command_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
        "runtime_path_diff_empty": True,
        "runtime_paths": tree_rows,
    }


def validate_build_source_report(path: Path, binary: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    require(report.get("source_commit") == BENCHMARK_SOURCE_COMMIT, "build report source commit mismatch")
    require(report.get("source_diff_sha256") == EMPTY_SHA256, "build report source diff is not empty")
    require(report.get("binary_sha256") == sha256_file(binary), "binary does not match clean build report")
    if report.get("schema_version") == "exact_long_query_hybrid_clean_build_v1":
        require(report.get("status") == "clean_build_pass", "clean build report did not pass")
        require(report.get("source_status_before") == "", "source was dirty before clean build")
        require(report.get("source_status_after") == "", "source was dirty after clean build")
        require(
            report.get("dependency", {}).get("commit")
            == "106d94ee53fc847214fb05f2f9f892538a5d3baf",
            "GASAL2 build dependency mismatch",
        )
    return report


def validate_promoter_contract(path: Path, verify_shards: bool) -> dict[str, object]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    require(contract.get("schema_version") == "exact_long_query_hybrid_production_promoter_contract_v1", "promoter contract schema mismatch")
    root = Path(contract["target_root"])
    forbidden = Path(contract["forbidden_target"]["path"])
    require(root.resolve() != forbidden.resolve(), "eligible and forbidden promoter roots collide")
    require("selected_genes_all_tss" not in str(root), "old expanded-TSS target is forbidden")
    require(sha256_file(Path(contract["source_rows"]["path"])) == contract["source_rows"]["sha256"], "human_genes20cells source digest mismatch")
    for relative, expected in contract["artifact_files"].items():
        require(sha256_file(root / relative) == expected, f"promoter artifact digest mismatch: {relative}")
    for dependency in contract["downstream_dependencies"].values():
        require(sha256_file(Path(dependency["path"])) == dependency["sha256"], f"downstream dependency digest mismatch: {dependency['path']}")

    audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
    require(audit.get("annotation_release") == contract["annotation"], "promoter annotation/source-row contract mismatch")
    require(audit.get("serialization_schema") == contract["required_rules"]["serialization_schema"], "promoter serialization schema mismatch")
    for key, expected in contract["required_counts"].items():
        require(audit["counts"].get(key) == expected, f"promoter count mismatch: {key}")
    for key in ("cross_component_hit_rule", "reference_n_hit_rule", "sequence_orientation", "promoter_coordinates"):
        require(audit["rules"].get(key) == contract["required_rules"][key], f"promoter rule mismatch: {key}")

    components = read_tsv(root / "promoter_components.tsv")
    require(len(components) == contract["required_counts"]["component_count"], "component row count mismatch")
    previous_end = 0
    for ordinal, row in enumerate(components, start=1):
        start = int(row["logical_concat_start0"])
        end = int(row["logical_concat_end0"])
        require(row["component_id"] == f"c_{ordinal:06d}", "component ordinal mismatch")
        require(start == previous_end and end > start, "component concat is not contiguous")
        require(int(row["component_length_bp"]) == end - start, "component length mismatch")
        previous_end = end
    require(previous_end == contract["required_counts"]["component_union_bp"], "component union length mismatch")

    verified_shards = 0
    if verify_shards:
        for relative, expected in contract["shard_file_sha256"].items():
            require(sha256_file(root / relative) == expected, f"promoter shard digest mismatch: {relative}")
            verified_shards += 1
    return {
        "status": "identity_gate_pass",
        "target_root": str(root),
        "tss_entries": audit["counts"]["tss_entries"],
        "component_count": len(components),
        "component_union_bp": previous_end,
        "verified_shards": verified_shards,
        "scientific_output_validated": False,
    }


def validate_manifest(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in read_tsv(path):
        fixture_id = raw["fixture_id"]
        require(fixture_id not in seen, f"duplicate fixture ID: {fixture_id}")
        seen.add(fixture_id)
        query = Path(raw["query_path"])
        target = Path(raw["target_path"])
        require(sha256_file(query) == raw["query_sha256"], f"query digest mismatch: {fixture_id}")
        require(fasta_length(query) == int(raw["query_length_nt"]), f"query length mismatch: {fixture_id}")
        require(sha256_file(target) == raw["target_sha256"], f"target digest mismatch: {fixture_id}")
        require(fasta_length(target) == int(raw["target_length_bp"]), f"target length mismatch: {fixture_id}")
        rows.append({**raw, "query_path": query, "target_path": target, "query_length_nt": int(raw["query_length_nt"]), "target_length_bp": int(raw["target_length_bp"])})
    require([row["query_length_nt"] for row in rows] == [4006, 8181, 12397], "checkpoint must contain exactly the three discrete fixtures")
    return rows


def cuda_attributes(device: int) -> dict[str, int]:
    runtime = ctypes.CDLL("libcudart.so")
    runtime.cudaSetDevice.argtypes = [ctypes.c_int]
    runtime.cudaSetDevice.restype = ctypes.c_int
    runtime.cudaDeviceGetAttribute.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]
    runtime.cudaDeviceGetAttribute.restype = ctypes.c_int
    require(runtime.cudaSetDevice(device) == 0, f"cudaSetDevice({device}) failed")

    def attribute(code: int) -> int:
        value = ctypes.c_int()
        require(runtime.cudaDeviceGetAttribute(ctypes.byref(value), code, device) == 0, f"cudaDeviceGetAttribute({code}) failed")
        return value.value

    return {
        "device_index": device,
        "default_shared_memory_per_block_bytes": attribute(8),
        "optin_shared_memory_per_block_bytes": attribute(97),
    }


def parse_key_values(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            result[key] = value
    return result


def output_path(directory: Path, mode: str) -> Path:
    pattern = "*-TFOsorted.lite" if mode == "lite" else "*-TFOsorted"
    values = sorted(path for path in directory.glob(pattern) if path.is_file())
    require(len(values) == 1, f"expected exactly one {mode} output in {directory}")
    return values[0]


def summarize_consumer(path: Path, expected_tasks: int) -> dict[str, object]:
    rows = read_tsv(path)
    require(len(rows) == expected_tasks, f"consumer task count mismatch: {len(rows)} != {expected_tasks}")
    totals = {key: 0 for key in (
        "scoreinfo_groups", "attempts", "gpu_scored_attempts", "cpu_oracle_attempts",
        "cpu_reference_align_attempts", "control_selected_attempts", "cpu_continuation_calls",
        "cpu_continuation_failures", "cpu_align_attempts",
    )}
    timings = {key: 0.0 for key in (
        "score_seconds", "gpu_kernel_seconds", "h2d_seconds", "d2h_seconds",
        "select_seconds", "traceback_seconds", "convert_seconds", "total_seconds",
    )}
    for row in rows:
        require(row["ok"] == "1" and row["output_equal"] == "-1", "replacement task did not fail closed")
        require(row["authority_comparison_available"] == "0" and row["validation_enabled"] == "0", "CPU oracle unexpectedly enabled")
        require(row["error"] == "none", f"consumer task error: {row['error']}")
        for key in totals:
            totals[key] += int(row[key])
        for key in timings:
            timings[key] += float(row[key])
    require(totals["attempts"] == totals["gpu_scored_attempts"], "incomplete GPU attempt coverage")
    require(totals["cpu_oracle_attempts"] == 0 and totals["cpu_reference_align_attempts"] == 0, "CPU all-attempt oracle/replay occurred")
    require(totals["control_selected_attempts"] == totals["cpu_continuation_calls"] == totals["cpu_align_attempts"], "selected continuation accounting mismatch")
    require(totals["cpu_continuation_failures"] == 0, "CPU continuation failed")
    return {"task_rows": len(rows), **totals, **timings}


def run_one(binary: Path, fixture: Mapping[str, object], mode: str, arm: str, repeat: int, gpu: int, cpu_set: str, root: Path) -> dict[str, object]:
    directory = root / str(fixture["fixture_id"]) / mode / f"{arm}_{repeat}"
    directory.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.update({
        "CUDA_VISIBLE_DEVICES": str(gpu),
        "FASIM_OUTPUT_MODE": mode,
        "FASIM_VERBOSE": "0",
        "OMP_NUM_THREADS": "1",
    })
    if arm == "baseline":
        environment.update({"FASIM_ALIGN_GASAL2": "0", "FASIM_ENABLE_PREALIGN_CUDA": "0"})
    else:
        environment.update(CANDIDATE_ENV)
        environment["FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT"] = str(directory / "consumer.tsv")
    command = [
        "/usr/bin/time", "-f", "wall_seconds=%e\nmax_rss_kb=%M\nexit_status=%x",
        "-o", str(directory / "time.txt"), "taskset", "-c", cpu_set,
        str(binary), "-f1", str(fixture["target_path"]), "-f2", str(fixture["query_path"]),
        "-r", "0", "-na", "512", "-O", str(directory),
    ]
    atomic_json(directory / "invocation.json", {
        "started_utc": utc_now(),
        "command": command,
        "environment": {key: environment[key] for key in sorted(environment) if key.startswith("FASIM_") or key in {"CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS"}},
    })
    with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        completed = subprocess.run(command, env=environment, stdout=stdout, stderr=stderr)
    require(completed.returncode == 0, f"{fixture['fixture_id']} {mode} {arm} repeat {repeat} failed")
    output = output_path(directory, mode)
    timing = parse_key_values(directory / "time.txt")
    require(timing.get("exit_status") == "0", "time receipt exit status mismatch")
    result: dict[str, object] = {
        "fixture_id": fixture["fixture_id"],
        "mode": mode,
        "arm": arm,
        "repeat": repeat,
        "wall_seconds": float(timing["wall_seconds"]),
        "max_rss_kb": int(timing["max_rss_kb"]),
        "output_path": str(output),
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256_file(output),
    }
    if arm == "candidate":
        metrics = parse_key_values(directory / "stderr.log")
        for key in FALLBACK_METRICS:
            require(metrics.get(key) == "0", f"nonzero or missing fallback metric: {key}")
        require(metrics.get("benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds") == "0", "CPU prealignment unexpectedly ran")
        result["consumer"] = summarize_consumer(directory / "consumer.tsv", 10368)
    atomic_json(directory / "run_receipt.json", result)
    return result


def environment_receipt(gpu: int) -> dict[str, object]:
    return {
        "captured_utc": utc_now(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
        "compiler": command_output(["g++", "--version"]).splitlines()[0],
        "nvcc": command_output(["/usr/local/cuda/bin/nvcc", "--version"]).splitlines()[-1],
        "nvidia_smi": command_output(["nvidia-smi", "--query-gpu=index,uuid,name,driver_version,memory.total", "--format=csv,noheader"]).splitlines(),
        "cpu_model": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "unknown"),
        "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "cuda_attributes": cuda_attributes(gpu),
        "scoring_contract": {
            "match": 5,
            "mismatch_penalty": 4,
            "gap_open": 16,
            "gap_extend": 4,
            "continuation_numeric_path": "WORD16",
            "runtime_parameter_guard_implemented": False,
            "int16_range_guard_implemented": False,
        },
    }


def run_checkpoint(args: argparse.Namespace) -> dict[str, object]:
    require(args.repeats >= 1, "repeats must be positive")
    require(args.speedup_gate >= 1.0, "speedup gate must be at least one")
    require(args.binary.is_file() and os.access(args.binary, os.X_OK), f"missing binary: {args.binary}")
    require(not args.work.exists(), f"refusing to overwrite checkpoint work root: {args.work}")

    fixtures = validate_manifest(args.manifest)
    promoter = validate_promoter_contract(args.promoter_contract, args.verify_promoter_shards)
    source_identity = validate_runtime_identity()
    build_source = validate_build_source_report(args.build_source_report, args.binary)
    environment = environment_receipt(args.gpu)
    args.work.mkdir(parents=True)
    atomic_json(args.work / "preflight.json", {
        "source_identity": source_identity,
        "build_source": build_source,
        "binary_sha256": sha256_file(args.binary),
        "promoter_contract": promoter,
        "environment": environment,
    })

    runs: list[dict[str, object]] = []
    fixture_results: list[dict[str, object]] = []
    for fixture in fixtures:
        shared_bytes = 3 * ((int(fixture["query_length_nt"]) + 31) // 32) * 32 * 2
        require(shared_bytes <= environment["cuda_attributes"]["optin_shared_memory_per_block_bytes"], f"fixture exceeds device shared-memory limit: {fixture['fixture_id']}")
        mode_results = []
        for mode in MODES:
            baseline_runs = []
            candidate_runs = []
            paired_speedups = []
            for repeat in range(1, args.repeats + 1):
                baseline = run_one(args.binary, fixture, mode, "baseline", repeat, args.gpu, args.cpu_set, args.work)
                candidate = run_one(args.binary, fixture, mode, "candidate", repeat, args.gpu, args.cpu_set, args.work)
                require(baseline["output_sha256"] == candidate["output_sha256"], f"paired output mismatch: {fixture['fixture_id']} {mode} repeat {repeat}")
                expected = fixture["expected_lite_sha256" if mode == "lite" else "expected_tfosorted_sha256"]
                if expected != "pending_clean_checkpoint":
                    require(baseline["output_sha256"] == expected, f"frozen output digest changed: {fixture['fixture_id']} {mode}")
                paired_speedups.append(float(baseline["wall_seconds"]) / float(candidate["wall_seconds"]))
                baseline_runs.append(baseline)
                candidate_runs.append(candidate)
                runs.extend((baseline, candidate))
            baseline_digests = {row["output_sha256"] for row in baseline_runs}
            candidate_digests = {row["output_sha256"] for row in candidate_runs}
            require(len(baseline_digests) == len(candidate_digests) == 1 and baseline_digests == candidate_digests, f"nondeterministic output: {fixture['fixture_id']} {mode}")
            median_speedup = statistics.median(paired_speedups)
            require(median_speedup >= args.speedup_gate, f"speedup gate failed: {fixture['fixture_id']} {mode} {median_speedup:.6f}x")
            mode_results.append({
                "mode": mode,
                "output_sha256": next(iter(baseline_digests)),
                "paired_speedups": paired_speedups,
                "median_paired_speedup": median_speedup,
                "deterministic": True,
                "byte_equal": True,
            })
        fixture_results.append({
            "fixture_id": fixture["fixture_id"],
            "gene_id": fixture["gene_id"],
            "gene_symbol": fixture["gene_symbol"],
            "query_length_nt": fixture["query_length_nt"],
            "required_dynamic_smem_bytes": shared_bytes,
            "resource_fit": True,
            "modes": mode_results,
        })

    receipt = {
        "schema_version": "exact_long_query_hybrid_checkpoint_v1",
        "status": "checkpoint_gate_pass",
        "completed_utc": utc_now(),
        "artifact_role": "engineering_checkpoint_only",
        "implementation": "stateful_gpu_scoreinfo_plus_gpu_endpoint_plus_host_selection_plus_selected_cpu_continuation",
        "gpu_only_traceback": False,
        "validated_continuous_range": False,
        "production_target_scientific_contract_validated": False,
        "production_authorized": False,
        "bioinformatics_v2_state_modified": False,
        "repeats": args.repeats,
        "speedup_gate": args.speedup_gate,
        "binary_sha256": sha256_file(args.binary),
        "source_identity": source_identity,
        "build_source": build_source,
        "promoter_identity_gate": promoter,
        "environment": environment,
        "fixtures": fixture_results,
        "run_count": len(runs),
    }
    atomic_json(args.work / "checkpoint_receipt.json", receipt)
    with (args.work / "runs.tsv").open("w", encoding="utf-8", newline="") as handle:
        fields = ("fixture_id", "mode", "arm", "repeat", "wall_seconds", "max_rss_kb", "output_bytes", "output_sha256", "output_path")
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(runs)
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    result.add_argument("--promoter-contract", type=Path, default=DEFAULT_PROMOTER_CONTRACT)
    result.add_argument("--binary", type=Path, required=True)
    result.add_argument("--build-source-report", type=Path, required=True)
    result.add_argument("--work", type=Path, required=True)
    result.add_argument("--gpu", type=int, default=0)
    result.add_argument("--cpu-set", default="0")
    result.add_argument("--repeats", type=int, default=3)
    result.add_argument("--speedup-gate", type=float, default=1.5)
    result.add_argument("--verify-promoter-shards", action="store_true")
    result.add_argument("--preflight-only", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.preflight_only:
            value = {
                "fixtures": [{"fixture_id": row["fixture_id"], "query_length_nt": row["query_length_nt"]} for row in validate_manifest(args.manifest)],
                "promoter_contract": validate_promoter_contract(args.promoter_contract, args.verify_promoter_shards),
                "source_identity": validate_runtime_identity(),
                "build_source": validate_build_source_report(args.build_source_report, args.binary),
                "environment": environment_receipt(args.gpu),
            }
        else:
            value = run_checkpoint(args)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (CheckpointError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
