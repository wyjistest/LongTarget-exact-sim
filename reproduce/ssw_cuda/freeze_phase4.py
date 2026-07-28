#!/usr/bin/env python3
"""Freeze and validate the bounded Phase 4 upstream architecture spike."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/upstream"
SOURCE_ROOT = ARTIFACT_ROOT / "sources"
LOG_ROOT = ARTIFACT_ROOT / "logs"
SNAPSHOT = ROOT / "paper/ssw_cuda/upstream_snapshot.tsv"
RECEIPT = ROOT / "paper/ssw_cuda/upstream_build_receipt.json"
SEMANTIC_DIFF = ROOT / "paper/ssw_cuda/upstream_semantic_diff.tsv"
DECISION = ROOT / "paper/ssw_cuda/architecture_decision.md"

SCHEMA_VERSION = 1
PHASE3_HEAD = "21832757d3431da7e6ec8b38b0072528f228988f"
NVCC = Path("/usr/local/cuda/bin/nvcc")

UPSTREAMS = {
    "accelign": {
        "repository_url": "https://github.com/fkallen/Accelign.git",
        "commit": "c7ecd32d59e256716cca193556110051c171570f",
        "license_spdx": "Apache-2.0",
        "documented_toolchain": "CUDA Toolkit >=12.9; C++17",
        "local_dir": "Accelign",
        "role": "forward_batching_length_bins_tile_scheduling_reference",
        "reuse_policy": "design_reference_only_in_tree_semantics",
    },
    "g3sa": {
        "repository_url": "https://github.com/sunwookim028/G3SA.git",
        "commit": "f0e0c130631dc2e06f92822b66c0494683f77eef",
        "license_spdx": "GPL-3.0",
        "documented_toolchain": "Ubuntu 22.04; CUDA Toolkit 12.1",
        "local_dir": "G3SA",
        "role": "checkpoint_recompute_block_boundary_cigar_structure_reference",
        "reuse_policy": "paper_and_structure_reference_only_no_code_copy_or_link",
    },
}

SNAPSHOT_FIELDS = (
    "upstream_id",
    "repository_url",
    "commit",
    "commit_date",
    "tree_sha1",
    "tracked_file_count",
    "tracked_bytes",
    "license_spdx",
    "license_path",
    "license_sha256",
    "documented_toolchain",
    "local_snapshot_path",
    "role",
    "reuse_policy",
)

BUILD_ATTEMPTS = (
    {
        "attempt_id": "accelign_build01",
        "upstream_id": "accelign",
        "log": "accelign_build01.log",
        "time": "accelign_build01.time",
        "command": [
            "make",
            "alignment_endpoints",
            "GPUARCH=89",
            "GPUARCH_NUM_COMPILE_THREADS=4",
        ],
        "working_directory": "examples/low-level",
        "expected_returncode": 0,
        "classification": "pass",
        "repair": "none",
        "binary": "Accelign/examples/low-level/alignment_endpoints",
    },
    {
        "attempt_id": "g3sa_build01",
        "upstream_id": "g3sa",
        "log": "g3sa_build01.log",
        "time": "g3sa_build01.time",
        "command": [
            "make",
            "-j4",
            "OBJ_DIR=obj-phase4",
            "BIN_DIR=bin-phase4",
            "TARGET=bin-phase4/minimap2-gpu",
            "NVCC=/usr/local/cuda/bin/nvcc",
            "NVCCFLAGS=-arch=sm_89 -DMAX_QUERY_LEN=10000 -DN_CODE=0x4E -Iinclude",
        ],
        "working_directory": "minimap2",
        "expected_returncode": 2,
        "classification": "failed_hardcoded_cuda_12_1_header",
        "repair": "none",
        "binary": None,
    },
    {
        "attempt_id": "g3sa_build02",
        "upstream_id": "g3sa",
        "log": "g3sa_build02.log",
        "time": "g3sa_build02.time",
        "command": [
            "make",
            "-j4",
            "OBJ_DIR=obj-phase4-attempt02",
            "BIN_DIR=bin-phase4-attempt02",
            "TARGET=bin-phase4-attempt02/minimap2-gpu",
            "NVCC=/usr/local/cuda/bin/nvcc",
            "NVCCFLAGS=-arch=sm_89 -DMAX_QUERY_LEN=10000 -DN_CODE=0x4E -Iinclude",
        ],
        "working_directory": "minimap2",
        "expected_returncode": 2,
        "classification": "failed_missing_cuda_include_for_host_compiler",
        "repair": "replace_two_absolute_cuda_12_1_includes_with_cuda_runtime_angle_include",
        "binary": None,
    },
    {
        "attempt_id": "g3sa_build03",
        "upstream_id": "g3sa",
        "log": "g3sa_build03.log",
        "time": "g3sa_build03.time",
        "command": [
            "make",
            "-j4",
            "OBJ_DIR=obj-phase4-attempt03",
            "BIN_DIR=bin-phase4-attempt03",
            "TARGET=bin-phase4-attempt03/minimap2-gpu",
            "CXX=g++",
            "NVCC=/usr/local/cuda/bin/nvcc",
            "CXXFLAGS=-std=c++11 -DMAX_QUERY_LEN=10000 -DN_CODE=0x4E -Iinclude -I/usr/local/cuda/include",
            "NVCCFLAGS=-arch=sm_89 -DMAX_QUERY_LEN=10000 -DN_CODE=0x4E -Iinclude",
        ],
        "working_directory": "minimap2",
        "expected_returncode": 0,
        "classification": "pass_after_bounded_portability_repair",
        "repair": "attempt02_header_patch_plus_explicit_host_cuda_include",
        "binary": "G3SA/minimap2/bin-phase4-attempt03/minimap2-gpu",
    },
)

RUN_ATTEMPTS = (
    {
        "attempt_id": "accelign_run01",
        "upstream_id": "accelign",
        "log": "accelign_run01.log",
        "time": "accelign_run01.time",
        "command": [
            "./alignment_endpoints",
            "8",
            "64",
            "64",
            "--checkResults",
            "--randomSeqs",
        ],
        "working_directory": "examples/low-level",
        "timeout_seconds": 120,
        "expected_returncode": 0,
        "classification": "single_tile_upstream_self_check_pass",
        "required_markers": [
            "oneToOne_singleTile score+endpos 32bit",
            "oneToOne_singleTile startPos 32bit",
            "scalar gpu scores and positions ok",
        ],
    },
    {
        "attempt_id": "accelign_run02",
        "upstream_id": "accelign",
        "log": "accelign_run02.log",
        "time": "accelign_run02.time",
        "command": [
            "./alignment_endpoints",
            "2",
            "2812",
            "2812",
            "--checkResults",
            "--randomSeqs",
        ],
        "working_directory": "examples/low-level",
        "timeout_seconds": 120,
        "expected_returncode": 0,
        "classification": "multi_tile_upstream_self_check_pass",
        "required_markers": [
            "oneToOne_multiTile score+endpos 32bit",
            "oneToOne_multiTile startPos 32bit",
            "scalar gpu scores and positions ok",
        ],
    },
    {
        "attempt_id": "g3sa_run01",
        "upstream_id": "g3sa",
        "log": "g3sa_run01.log",
        "time": "g3sa_run01.time",
        "command": ["./bin-phase4-attempt03/minimap2-gpu", "-h"],
        "working_directory": "minimap2",
        "timeout_seconds": 30,
        "expected_returncode": 1,
        "classification": "unsupported_help_flag_treated_as_input",
        "required_markers": ["Number of gpus: 1", "failed to open file '-h'"],
    },
    {
        "attempt_id": "g3sa_run02",
        "upstream_id": "g3sa",
        "log": "g3sa_run02.log",
        "time": "g3sa_run02.time",
        "command": ["./bin-phase4-attempt03/minimap2-gpu"],
        "working_directory": "minimap2",
        "timeout_seconds": 30,
        "expected_returncode": 139,
        "classification": "no_argument_operational_smoke_sigsegv_no_correctness_claim",
        "required_markers": ["Number of gpus: 1"],
    },
)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def run(arguments: Sequence[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if check:
        require(
            completed.returncode == 0,
            completed.stderr.strip() or f"command failed: {' '.join(arguments)}",
        )
    return completed


def git(repo: Path, *arguments: str) -> str:
    return run(("git", *arguments), cwd=repo).stdout.strip()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def snapshot_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for upstream_id, metadata in UPSTREAMS.items():
        repo = SOURCE_ROOT / metadata["local_dir"]
        require(repo.is_dir() and not repo.is_symlink(), f"missing upstream snapshot: {repo}")
        require(git(repo, "rev-parse", "HEAD") == metadata["commit"], f"{upstream_id} commit drift")
        tree = git(repo, "rev-parse", "HEAD^{tree}")
        listing = git(repo, "ls-tree", "-r", "-l", "HEAD").splitlines()
        tracked_bytes = 0
        for line in listing:
            fields = line.split(None, 4)
            require(len(fields) == 5 and fields[3].isdigit(), f"{upstream_id} tree listing drift")
            tracked_bytes += int(fields[3])
        license_path = repo / "LICENSE"
        rows.append(
            {
                "upstream_id": upstream_id,
                "repository_url": metadata["repository_url"],
                "commit": metadata["commit"],
                "commit_date": git(repo, "show", "-s", "--format=%cI", "HEAD"),
                "tree_sha1": tree,
                "tracked_file_count": len(listing),
                "tracked_bytes": tracked_bytes,
                "license_spdx": metadata["license_spdx"],
                "license_path": "LICENSE",
                "license_sha256": sha256_file(license_path),
                "documented_toolchain": metadata["documented_toolchain"],
                "local_snapshot_path": str(repo.relative_to(ROOT)),
                "role": metadata["role"],
                "reuse_policy": metadata["reuse_policy"],
            }
        )
    return rows


def parse_elapsed(value: str) -> float:
    pieces = value.split(":")
    require(len(pieces) in (2, 3), f"invalid GNU time elapsed value: {value}")
    if len(pieces) == 2:
        minutes, seconds = pieces
        return int(minutes) * 60 + float(seconds)
    hours, minutes, seconds = pieces
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_attempt_artifacts(spec: dict[str, Any]) -> dict[str, Any]:
    log_path = LOG_ROOT / spec["log"]
    time_path = LOG_ROOT / spec["time"]
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    time_text = time_path.read_text(encoding="utf-8", errors="replace")
    start_match = re.search(r"Script started on ([^\[]+?) \[", log_text)
    end_match = re.search(r'Script done on ([^\[]+?) \[COMMAND_EXIT_CODE="([0-9]+)"\]', log_text)
    elapsed_match = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([0-9:.]+)", time_text)
    rss_match = re.search(r"Maximum resident set size \(kbytes\): ([0-9]+)", time_text)
    exit_match = re.search(r"Exit status: ([0-9]+)", time_text)
    require(all((start_match, end_match, elapsed_match, rss_match, exit_match)), f"attempt log parse failed: {spec['attempt_id']}")
    assert start_match and end_match and elapsed_match and rss_match and exit_match
    returncode = int(end_match.group(2))
    require(returncode == int(exit_match.group(1)), f"return-code evidence drift: {spec['attempt_id']}")
    require(returncode == spec["expected_returncode"], f"unexpected attempt return code: {spec['attempt_id']}")
    for marker in spec.get("required_markers", []):
        require(marker in log_text, f"missing attempt marker {marker}: {spec['attempt_id']}")
    start = datetime.fromisoformat(start_match.group(1).strip()).astimezone(timezone.utc)
    end = datetime.fromisoformat(end_match.group(1).strip()).astimezone(timezone.utc)
    return {
        "attempt_id": spec["attempt_id"],
        "upstream_id": spec["upstream_id"],
        "command": spec["command"],
        "working_directory": spec.get("working_directory", "minimap2"),
        "timeout_seconds": spec.get("timeout_seconds", 1800),
        "started_utc": start.isoformat(),
        "ended_utc": end.isoformat(),
        "wall_seconds": parse_elapsed(elapsed_match.group(1)),
        "max_rss_kib": int(rss_match.group(1)),
        "returncode": returncode,
        "classification": spec["classification"],
        "repair": spec.get("repair", "none"),
        "log_path": str(log_path.relative_to(ROOT)),
        "log_sha256": sha256_file(log_path),
        "time_path": str(time_path.relative_to(ROOT)),
        "time_sha256": sha256_file(time_path),
    }


def g3sa_patch() -> dict[str, Any]:
    repo = SOURCE_ROOT / "G3SA"
    completed = run(
        ("git", "diff", "--binary", "--", "minimap2/include/gasal.h", "minimap2/include/host_mem.h"),
        cwd=repo,
    )
    require(completed.stdout, "missing G3SA portability patch")
    changed = git(repo, "diff", "--name-only").splitlines()
    require(
        changed == ["minimap2/include/gasal.h", "minimap2/include/host_mem.h"],
        "unexpected tracked G3SA sandbox changes",
    )
    return {
        "scope": "ignored_build_sandbox_only",
        "changed_paths": changed,
        "diff_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "semantic_change": False,
        "description": "Replace two absolute CUDA 12.1 includes with standard cuda_runtime.h includes.",
    }


def binary_metadata(relative: str) -> dict[str, Any]:
    path = SOURCE_ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"missing build output: {path}")
    return {
        "path": str(path.relative_to(ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def toolchain_metadata() -> dict[str, Any]:
    cxx = Path(shutil.which("g++") or "")
    require(cxx.is_file() and NVCC.is_file(), "required Phase 4 compiler unavailable")
    gpu_query = run(
        (
            "nvidia-smi",
            "--query-gpu=index,name,uuid,compute_cap,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        )
    ).stdout.splitlines()
    devices = []
    for line in gpu_query:
        fields = [field.strip() for field in line.split(",")]
        require(len(fields) == 6, "unexpected GPU metadata")
        devices.append(
            {
                "index": int(fields[0]),
                "name": fields[1],
                "uuid": fields[2],
                "compute_capability": fields[3],
                "memory_total_mib": int(fields[4]),
                "driver_version": fields[5],
            }
        )
    return {
        "cxx_path": str(cxx.resolve()),
        "cxx_sha256": sha256_file(cxx.resolve()),
        "cxx_version": run((str(cxx), "--version")).stdout.splitlines()[0],
        "nvcc_path": str(NVCC.resolve()),
        "nvcc_sha256": sha256_file(NVCC.resolve()),
        "nvcc_version": run((str(NVCC), "--version")).stdout.strip(),
        "make_version": run(("make", "--version")).stdout.splitlines()[0],
        "gpu_devices": devices,
    }


def build_receipt(
    snapshot_payload: bytes,
    *,
    frozen_parent_head: str,
    frozen_utc: str,
) -> dict[str, Any]:
    build_attempts = [parse_attempt_artifacts(spec) for spec in BUILD_ATTEMPTS]
    for attempt, spec in zip(build_attempts, BUILD_ATTEMPTS):
        if spec["binary"]:
            attempt["output_binary"] = binary_metadata(spec["binary"])
        else:
            attempt["output_binary"] = None
    run_attempts = [parse_attempt_artifacts(spec) for spec in RUN_ATTEMPTS]
    build_counts = {
        upstream_id: sum(attempt["upstream_id"] == upstream_id for attempt in build_attempts)
        for upstream_id in UPSTREAMS
    }
    require(build_counts == {"accelign": 1, "g3sa": 3}, "build-attempt budget drift")
    gpu_runtime_upper_bound = sum(attempt["wall_seconds"] for attempt in run_attempts)
    require(gpu_runtime_upper_bound < 8 * 3600, "Phase 4 GPU-time budget exceeded")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": 4,
        "status": "pass_with_bounded_upstream_runtime_limitations",
        "frozen_parent_head": frozen_parent_head,
        "frozen_utc": frozen_utc,
        "upstream_snapshot": {
            "path": str(SNAPSHOT.relative_to(ROOT)),
            "sha256": sha256_bytes(snapshot_payload),
            "row_count": 2,
        },
        "toolchain": toolchain_metadata(),
        "build_budget": {
            "maximum_attempts_per_upstream": 3,
            "attempt_counts": build_counts,
            "architecture_candidate_count": 3,
            "maximum_architecture_candidates": 3,
            "gpu_time_limit_seconds": 8 * 3600,
            "observed_runtime_wall_seconds_upper_bound": gpu_runtime_upper_bound,
        },
        "g3sa_portability_patch": g3sa_patch(),
        "build_attempts": build_attempts,
        "runtime_attempts": run_attempts,
        "results": {
            "accelign_build": "pass_first_attempt",
            "accelign_single_tile_self_check": "pass",
            "accelign_multi_tile_2812_self_check": "pass",
            "accelign_ssw_equivalence_claimed": False,
            "g3sa_build": "pass_third_and_final_attempt",
            "g3sa_runtime_correctness_claimed": False,
            "g3sa_no_argument_smoke": "sigsegv_exit_139",
            "selected_architecture": "C_mixed_in_tree_checkpoint_recompute",
            "third_party_code_linked_or_copied": False,
        },
        "bindings": {
            "generator_path": str(Path(__file__).resolve().relative_to(ROOT)),
            "generator_sha256": sha256_file(Path(__file__).resolve()),
            "semantic_diff_path": str(SEMANTIC_DIFF.relative_to(ROOT)),
            "semantic_diff_sha256": sha256_file(SEMANTIC_DIFF),
            "architecture_decision_path": str(DECISION.relative_to(ROOT)),
            "architecture_decision_sha256": sha256_file(DECISION),
        },
        "claim_boundary": {
            "cpu_oracle_replaced": False,
            "l1_l5_implementation_owner": "in_tree",
            "g3sa_license_status": "reference_only_pending_component_level_legal_review",
            "bioinformatics_b3_track": "closed_amdahl",
            "engineering_track": "active",
        },
    }


def build_outputs(frozen_parent_head: str, frozen_utc: str) -> dict[Path, bytes]:
    require(frozen_parent_head == PHASE3_HEAD, "Phase 4 parent must be the final Phase 3 commit")
    require(frozen_utc.endswith("Z") or "+00:00" in frozen_utc, "frozen UTC must include UTC offset")
    rows = snapshot_rows()
    snapshot_payload = tsv_bytes(SNAPSHOT_FIELDS, rows)
    receipt = build_receipt(
        snapshot_payload,
        frozen_parent_head=frozen_parent_head,
        frozen_utc=frozen_utc,
    )
    return {SNAPSHOT: snapshot_payload, RECEIPT: json_bytes(receipt)}


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, payload in outputs.items():
        require(not path.is_symlink(), f"unsafe output path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def validate_committed() -> dict[str, Any]:
    for path in (SNAPSHOT, RECEIPT, SEMANTIC_DIFF, DECISION):
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 4 evidence: {path}")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    require(receipt["schema_version"] == 1 and receipt["phase"] == 4, "Phase 4 receipt schema drift")
    require(receipt["frozen_parent_head"] == PHASE3_HEAD, "Phase 4 parent drift")
    require(receipt["upstream_snapshot"]["sha256"] == sha256_file(SNAPSHOT), "snapshot binding drift")
    require(receipt["upstream_snapshot"]["row_count"] == 2, "snapshot row-count drift")
    require(
        receipt["bindings"]["generator_sha256"] == sha256_file(Path(__file__).resolve()),
        "Phase 4 generator binding drift",
    )
    require(receipt["bindings"]["semantic_diff_sha256"] == sha256_file(SEMANTIC_DIFF), "semantic diff binding drift")
    require(receipt["bindings"]["architecture_decision_sha256"] == sha256_file(DECISION), "decision binding drift")
    require(receipt["build_budget"]["attempt_counts"] == {"accelign": 1, "g3sa": 3}, "attempt budget drift")
    require(receipt["build_budget"]["architecture_candidate_count"] <= 3, "architecture budget drift")
    require(receipt["build_budget"]["observed_runtime_wall_seconds_upper_bound"] < 8 * 3600, "GPU budget drift")
    require(receipt["results"]["selected_architecture"] == "C_mixed_in_tree_checkpoint_recompute", "decision drift")
    require(not receipt["results"]["third_party_code_linked_or_copied"], "third-party reuse boundary drift")
    require(not receipt["claim_boundary"]["cpu_oracle_replaced"], "CPU oracle boundary drift")
    require(receipt["claim_boundary"]["bioinformatics_b3_track"] == "closed_amdahl", "B3 boundary drift")
    with SNAPSHOT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require({row["upstream_id"] for row in rows} == set(UPSTREAMS), "upstream inventory drift")
    for row in rows:
        metadata = UPSTREAMS[row["upstream_id"]]
        require(row["commit"] == metadata["commit"], f"{row['upstream_id']} pin drift")
        require(row["license_spdx"] == metadata["license_spdx"], f"{row['upstream_id']} license drift")
    return receipt


def check_artifacts() -> None:
    receipt = validate_committed()
    outputs = build_outputs(receipt["frozen_parent_head"], receipt["frozen_utc"])
    for path, payload in outputs.items():
        require(path.read_bytes() == payload, f"Phase 4 evidence is not reproducible: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-artifacts", action="store_true")
    parser.add_argument("--frozen-parent-head")
    parser.add_argument("--frozen-utc")
    arguments = parser.parse_args()
    if arguments.write:
        require(arguments.frozen_parent_head is not None, "--write requires --frozen-parent-head")
        require(arguments.frozen_utc is not None, "--write requires --frozen-utc")
        write_outputs(build_outputs(arguments.frozen_parent_head, arguments.frozen_utc))
    elif arguments.check_artifacts:
        check_artifacts()
    else:
        validate_committed()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FreezeError as error:
        print(f"Phase 4 freeze error: {error}", file=sys.stderr)
        raise SystemExit(1)
