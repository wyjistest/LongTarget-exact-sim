#!/usr/bin/env python3
"""Run one frozen CPU or exact-hybrid real-promoter validation case."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from exact_long_query_promoter_mapping import PromoterMapping, read_single_fasta, sha256_file


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs/exact_long_query_hybrid_promoter_panel_v1"
RUN_ROOT = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_promoter_panel_v1"
)
BINARY = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_checkpoint_v1/clean_build_61da9b6/"
    "fasim_longtarget_gasal2_61da9b6"
)
BINARY_SHA256 = "6e9d5cec5ff50c9652b9aeb05a8a5533a9d707e0799d9925b2686377cdfdd7ee"
SHAKE_QUERY = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_checkpoint_v1/inputs/ENSG00000229613.fa"
)
SHAKE_QUERY_ID = "ENSG00000229613"
SHAKE_QUERY_SYMBOL = "LINC01501"
SHAKE_QUERY_LENGTH = 4006
SHAKE_QUERY_SEQUENCE_SHA256 = "896e9e632f321c87539268390c3668baab3d40f1007cd2433b44321561ebc657"
FORWARD_PREFIX = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_"
FALLBACK_METRICS = (
    FORWARD_PREFIX + "fallback_batches",
    FORWARD_PREFIX + "gpu_minscore_fallbacks",
    FORWARD_PREFIX + "realpath_fallbacks",
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
CONSUMER_FIELDS = (
    "task_index", "execution_mode", "authority_comparison_available", "validation_enabled", "ok",
    "output_equal", "scoreinfo_groups", "attempts", "gpu_scored_attempts", "endpoint_batches",
    "cpu_oracle_attempts", "attempt_mismatch_rows", "score_mismatches", "query_end_mismatches",
    "ref_end_local_mismatches", "terminal_mismatches", "control_selected_attempts",
    "cpu_control_selected_attempts", "consumer_selection_equal", "cpu_reference_align_attempts",
    "consumer_attempt_prefix_equal", "cpu_continuation_requested", "cpu_continuation_active",
    "cpu_continuation_calls", "cpu_continuation_failures", "replay_attempts", "cpu_align_attempts",
    "threshold_groups", "best_fallback_groups", "last_groups", "empty_groups", "score_seconds",
    "gpu_kernel_seconds", "h2d_seconds", "d2h_seconds", "cpu_oracle_seconds", "select_seconds",
    "traceback_seconds", "convert_seconds", "total_seconds", "missing_rows", "extra_rows",
    "first_attempt_mismatch", "first_consumer_mismatch", "error",
)
INTEGER_TOTAL_FIELDS = (
    "scoreinfo_groups", "attempts", "gpu_scored_attempts", "endpoint_batches", "cpu_oracle_attempts",
    "attempt_mismatch_rows", "score_mismatches", "query_end_mismatches", "ref_end_local_mismatches",
    "terminal_mismatches", "control_selected_attempts", "cpu_control_selected_attempts",
    "cpu_reference_align_attempts", "cpu_continuation_calls", "cpu_continuation_failures",
    "replay_attempts", "cpu_align_attempts", "threshold_groups", "best_fallback_groups", "last_groups",
    "empty_groups", "missing_rows", "extra_rows",
)
TIMING_TOTAL_FIELDS = (
    "score_seconds", "gpu_kernel_seconds", "h2d_seconds", "d2h_seconds", "cpu_oracle_seconds",
    "select_seconds", "traceback_seconds", "convert_seconds", "total_seconds",
)


class CaseError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaseError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def read_tsv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None and rows, f"empty TSV: {path}")
    require(all(None not in row for row in rows), f"malformed TSV: {path}")
    return tuple(reader.fieldnames), rows


def parse_key_values(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        require(key not in result, f"duplicate metric {key}: {path}")
        result[key] = value
    return result


def runtime_environment(arm: str, gpu: int, report: Path) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("FASIM_")
    }
    environment.update({
        "CUDA_VISIBLE_DEVICES": str(gpu),
        "FASIM_OUTPUT_MODE": "tfosorted",
        "FASIM_VERBOSE": "0",
        "OMP_NUM_THREADS": "1",
    })
    if arm == "baseline":
        environment.update({"FASIM_ALIGN_GASAL2": "0", "FASIM_ENABLE_PREALIGN_CUDA": "0"})
    else:
        environment.update(CANDIDATE_ENV)
        environment["FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT"] = str(report)
    return environment


def summarize_consumer(path: Path) -> dict[str, int | float]:
    totals: dict[str, int | float] = {key: 0 for key in INTEGER_TOTAL_FIELDS}
    totals.update({key: 0.0 for key in TIMING_TOTAL_FIELDS})
    zero_fields = (
        "cpu_oracle_attempts", "attempt_mismatch_rows", "score_mismatches", "query_end_mismatches",
        "ref_end_local_mismatches", "terminal_mismatches", "cpu_control_selected_attempts",
        "cpu_reference_align_attempts", "cpu_continuation_failures", "missing_rows", "extra_rows",
    )
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == CONSUMER_FIELDS, f"consumer schema mismatch: {path}")
        for index, row in enumerate(reader):
            rows += 1
            label = f"{path}: task {index}"
            require(None not in row and int(row["task_index"]) == index, f"consumer task order mismatch: {label}")
            require(row["execution_mode"] == "replacement_prototype", f"consumer mode mismatch: {label}")
            require(row["authority_comparison_available"] == row["validation_enabled"] == "0", f"CPU oracle enabled: {label}")
            require(row["ok"] == "1" and row["output_equal"] == "-1", f"consumer task failure: {label}")
            require(row["first_attempt_mismatch"] == row["first_consumer_mismatch"] == row["error"] == "none", f"consumer mismatch: {label}")
            require(all(int(row[key]) == 0 for key in zero_fields), f"consumer failure counter: {label}")
            groups = int(row["scoreinfo_groups"])
            attempts = int(row["attempts"])
            selected = int(row["control_selected_attempts"])
            active = int(groups > 0)
            require(attempts == 4 * groups == int(row["gpu_scored_attempts"]), f"GPU attempt coverage mismatch: {label}")
            require(
                groups == sum(int(row[key]) for key in ("threshold_groups", "best_fallback_groups", "last_groups", "empty_groups")),
                f"consumer outcome partition mismatch: {label}",
            )
            require(
                selected == sum(int(row[key]) for key in ("threshold_groups", "best_fallback_groups", "last_groups")),
                f"selected outcome partition mismatch: {label}",
            )
            require(selected == int(row["cpu_continuation_calls"]) == int(row["cpu_align_attempts"]), f"selected continuation mismatch: {label}")
            for key in (
                "endpoint_batches", "consumer_selection_equal", "consumer_attempt_prefix_equal",
                "cpu_continuation_requested", "cpu_continuation_active",
            ):
                require(int(row[key]) == active, f"consumer activity mismatch for {key}: {label}")
            require(float(row["cpu_oracle_seconds"]) == 0.0, f"CPU oracle time is nonzero: {label}")
            for key in INTEGER_TOTAL_FIELDS:
                totals[key] = int(totals[key]) + int(row[key])
            for key in TIMING_TOTAL_FIELDS:
                value = float(row[key])
                require(value >= 0.0, f"negative timing for {key}: {label}")
                totals[key] = float(totals[key]) + value
    require(rows > 0, f"empty consumer report: {path}")
    totals["task_rows"] = rows
    return totals


def query_record(stage: str, gene_id: str) -> dict[str, object]:
    if stage == "observed_query_shard9_shake_down":
        require(gene_id == SHAKE_QUERY_ID, "unexpected shake-down query")
        _, sequence = read_single_fasta(SHAKE_QUERY)
        require(len(sequence) == SHAKE_QUERY_LENGTH, "shake query length mismatch")
        require(hashlib.sha256(sequence.encode("ascii")).hexdigest() == SHAKE_QUERY_SEQUENCE_SHA256, "shake query sequence drift")
        return {
            "gene_id": gene_id,
            "gene_symbol": SHAKE_QUERY_SYMBOL,
            "query_length_nt": SHAKE_QUERY_LENGTH,
            "sequence_sha256": SHAKE_QUERY_SEQUENCE_SHA256,
            "runtime_fasta": str(SHAKE_QUERY),
            "runtime_fasta_sha256": sha256_file(SHAKE_QUERY),
        }
    _, rows = read_tsv(DOC_ROOT / "fresh_queries.tsv")
    matches = [row for row in rows if row["gene_id"] == gene_id]
    require(len(matches) == 1, f"fresh query not found: {gene_id}")
    row = matches[0]
    query = Path(row["runtime_fasta"])
    _, sequence = read_single_fasta(query)
    require(len(sequence) == int(row["query_length_nt"]), f"fresh query length drift: {gene_id}")
    require(hashlib.sha256(sequence.encode("ascii")).hexdigest() == row["sequence_sha256"], f"fresh query sequence drift: {gene_id}")
    require(sha256_file(query) == row["runtime_fasta_sha256"], f"fresh runtime FASTA drift: {gene_id}")
    return {**row, "query_length_nt": int(row["query_length_nt"])}


def check_freshness(gene_id: str) -> None:
    roots = Path("/data/wenyujianData/linjieData/longtarget_runs")
    matches = sorted(roots.glob(f"human_genes20cells_ge2048_*/raw_jobs/{gene_id}"))
    require(not matches, f"fresh query acquired an external production-target job after freeze: {matches}")


def select_matrix_row(workload_id: str, arm: str, repeat: int) -> dict[str, str]:
    _, rows = read_tsv(DOC_ROOT / "execution_matrix.tsv")
    matches = [
        row for row in rows
        if row["workload_id"] == workload_id and row["arm"] == arm and int(row["repeat"]) == repeat
    ]
    require(len(matches) == 1, "execution matrix row not found or duplicated")
    row = matches[0]
    if row["stage"] == "fresh_full_promoter_panel":
        addendum = DOC_ROOT / "formal_execution_addendum.json"
        require(addendum.is_file(), "formal panel remains pending shake-down gate")
        value = json.loads(addendum.read_text(encoding="utf-8"))
        require(value.get("formal_panel_authorized") is True, "formal execution addendum did not authorize panel")
    else:
        require(row["authorization"] == "authorized_pre_formal_gate", "shake-down is not authorized")
    return row


def sole_output(directory: Path) -> Path:
    outputs = sorted(path for path in directory.glob("*-TFOsorted") if path.is_file())
    require(len(outputs) == 1, f"expected one complete TFOsorted output: {directory}")
    return outputs[0]


def run(args: argparse.Namespace) -> dict[str, object]:
    row = select_matrix_row(args.workload_id, args.arm, args.repeat)
    query = query_record(row["stage"], row["gene_id"])
    if row["stage"] == "fresh_full_promoter_panel":
        check_freshness(row["gene_id"])
    preexecution = json.loads((DOC_ROOT / "preexecution_decision.json").read_text(encoding="utf-8"))
    require(preexecution["predecessor"]["formal_binary_sha256"] == BINARY_SHA256, "preexecution binary identity mismatch")
    require(BINARY.is_file() and sha256_file(BINARY) == BINARY_SHA256, "formal binary digest mismatch")
    mapping = PromoterMapping(Path(json.loads((DOC_ROOT / "target_execution_contract.json").read_text())["target_root"]))
    context = mapping.target_context(row["target_artifact_id"])
    require(str(context.path) == row["target_path"], "execution matrix target path mismatch")
    require(context.length_bp == int(row["target_length_bp"]), "execution matrix target length mismatch")
    require(not args.output.exists(), f"refusing to overwrite case root: {args.output}")
    args.output.mkdir(parents=True)
    runtime_output = args.output / "runtime_output"
    runtime_output.mkdir()
    environment = runtime_environment(args.arm, args.gpu, args.output / "consumer.tsv")
    command = [
        "/usr/bin/time", "-f", "wall_seconds=%e\nmax_rss_kb=%M\nexit_status=%x",
        "-o", str(args.output / "time.txt"), "taskset", "-c", args.cpu_set,
        str(BINARY), "-f1", str(context.path), "-f2", str(query["runtime_fasta"]),
        "-r", "0", "-na", "512", "-O", str(runtime_output),
    ]
    atomic_json(args.output / "invocation.json", {
        "schema_version": "exact_long_query_hybrid_promoter_case_invocation_v1",
        "started_utc": utc_now(),
        "workload_id": args.workload_id,
        "arm": args.arm,
        "repeat": args.repeat,
        "command": command,
        "environment": {key: environment[key] for key in sorted(environment) if key.startswith("FASIM_") or key in {"CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS"}},
    })
    with (args.output / "stdout.log").open("wb") as stdout, (args.output / "stderr.log").open("wb") as stderr:
        completed = subprocess.run(command, env=environment, stdout=stdout, stderr=stderr)
    require(completed.returncode == 0, f"runtime failed with exit code {completed.returncode}")
    timing = parse_key_values(args.output / "time.txt")
    require(timing.get("exit_status") == "0", "time receipt reports failure")
    output = sole_output(runtime_output)
    receipt: dict[str, object] = {
        "schema_version": "exact_long_query_hybrid_promoter_case_receipt_v1",
        "status": "complete",
        "completed_utc": utc_now(),
        "workload_id": args.workload_id,
        "stage": row["stage"],
        "arm": args.arm,
        "backend": "cpu" if args.arm == "baseline" else "exact_long_query_hybrid",
        "repeat": args.repeat,
        "technical_contract_pass": True,
        "binary": {"path": str(BINARY), "sha256": BINARY_SHA256},
        "query": {
            "gene_id": row["gene_id"],
            "gene_symbol": query["gene_symbol"],
            "path": query["runtime_fasta"],
            "file_sha256": query["runtime_fasta_sha256"],
            "sequence_sha256": query["sequence_sha256"],
            "length_nt": int(query["query_length_nt"]),
        },
        "target": {
            "artifact_id": context.artifact_id,
            "path": str(context.path),
            "file_sha256": context.file_sha256,
            "length_bp": context.length_bp,
            "logical_offset0": context.logical_offset0,
        },
        "wall_seconds": float(timing["wall_seconds"]),
        "max_rss_kb": int(timing["max_rss_kb"]),
        "artifacts": [{
            "role": "complete_tfosorted",
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
        }],
    }
    if args.arm == "candidate":
        metrics = parse_key_values(args.output / "stderr.log")
        for key in FALLBACK_METRICS:
            require(metrics.get(key) == "0", f"fallback metric missing or nonzero: {key}")
        require(metrics.get(FORWARD_PREFIX + "cpu_prealign_seconds") == "0", "CPU prealignment ran")
        consumer = summarize_consumer(args.output / "consumer.tsv")
        expected_tasks = int(metrics[FORWARD_PREFIX + "tasks"])
        require(consumer["task_rows"] == expected_tasks, "consumer/forward task count mismatch")
        require(int(metrics[FORWARD_PREFIX + "gpu_tasks"]) == expected_tasks, "incomplete forward GPU task coverage")
        require(int(metrics[FORWARD_PREFIX + "realpath_used"]) == expected_tasks, "incomplete replacement task coverage")
        require(int(metrics[FORWARD_PREFIX + "realpath_extend_calls"]) == expected_tasks, "replacement call count mismatch")
        require(int(consumer["attempts"]) == int(consumer["gpu_scored_attempts"]), "incomplete endpoint GPU coverage")
        require(int(consumer["cpu_oracle_attempts"]) == int(consumer["cpu_reference_align_attempts"]) == 0, "CPU all-attempt oracle/replay observed")
        require(int(consumer["cpu_continuation_failures"]) == 0, "selected continuation failed")
        receipt["consumer"] = consumer
        receipt["forward"] = {
            "tasks": expected_tasks,
            "gpu_tasks": int(metrics[FORWARD_PREFIX + "gpu_tasks"]),
            "total_seconds": float(metrics[FORWARD_PREFIX + "total_seconds"]),
            "kernel_seconds": float(metrics[FORWARD_PREFIX + "kernel_seconds"]),
            "h2d_seconds": float(metrics[FORWARD_PREFIX + "h2d_seconds"]),
            "d2h_seconds": float(metrics[FORWARD_PREFIX + "d2h_seconds"]),
        }
    atomic_json(args.output / "receipt.json", receipt)
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workload-id", required=True)
    result.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    result.add_argument("--repeat", type=int, required=True)
    result.add_argument("--gpu", type=int, default=0)
    result.add_argument("--cpu-set", default="0")
    result.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    require(args.repeat > 0, "repeat must be positive")
    value = run(args)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CaseError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
