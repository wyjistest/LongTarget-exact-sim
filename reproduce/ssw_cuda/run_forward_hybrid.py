#!/usr/bin/env python3
"""Freeze, execute, and audit the Phase 7 exact forward-hybrid checkpoint."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import platform
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "paper/ssw_cuda/forward_hybrid_attempt_plan_v2.tsv"
PROTOCOL = ROOT / "paper/ssw_cuda/forward_hybrid_protocol.md"
REPAIR_PROTOCOL = ROOT / "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.md"
REPAIR_RECEIPT = ROOT / "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.json"
SOURCE_DATA = ROOT / "paper/ssw_cuda/forward_hybrid_source_data.tsv"
PROJECTION = ROOT / "paper/ssw_cuda/forward_hybrid_projection.json"
DECISION = ROOT / "paper/ssw_cuda/forward_hybrid_decision.json"
STATE = ROOT / "paper/ssw_cuda/PROGRAM_STATE.json"
HOLDOUT = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
PHASE1_PLAN = ROOT / "paper/ssw_cuda/cpu_profile_recovery_attempt_plan.tsv"
PHASE1_SOURCE = ROOT / "paper/ssw_cuda/cpu_profile_v2_source_data.tsv"
PHASE1_STATS = ROOT / "paper/ssw_cuda/cpu_profile_v2_statistics.json"
H2_RECEIPT = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json"
COMPARATOR = ROOT / "scripts/compare_fasim_lite_offline_cluster_topk.py"
COMPARATOR_SHA256 = "2765d76b6c8e742596b1072a413309a88ef415f3576c9de62be67213ee76dc80"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/forward-hybrid"
FORMAL_ROOT = ARTIFACT_ROOT / "formal-v2"
COMPARISON_ROOT = ARTIFACT_ROOT / "offline-comparison-v2"
EXECUTION_RECEIPT = ARTIFACT_ROOT / "execution-receipt-v2.json"
DEFAULT_BINARY = ARTIFACT_ROOT / "build/fasim_forward_hybrid"
SNAPSHOT_ROOT = ARTIFACT_ROOT / "execution-snapshot-v2"
SNAPSHOT_BINARY = SNAPSHOT_ROOT / "fasim_forward_hybrid"
V1_EXECUTION_RECEIPT = ARTIFACT_ROOT / "execution-receipt-v1.json"
PHASE2_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
SCHEMA_VERSION = "1"
MAX_TASKS = 16
GPU_BUDGET_SECONDS = 12 * 3600
CORRECTNESS_TIMEOUT_SECONDS = 600
PERFORMANCE_TIMEOUT_SECONDS = 7200

PERFORMANCE_WORKLOADS = (
    "overhead_aq001_at0001",
    "medium_h19_chr22_2mb",
    "large_h19_chr21",
    "large_h19_chr22",
    "application_aq005_at0199",
)

PLAN_FIELDS = (
    "attempt_id",
    "execution_stage",
    "arm",
    "backend",
    "workload_id",
    "workload_class",
    "observation_id",
    "cache_state",
    "execution_order",
    "device",
    "gpu_assignment",
    "query_path",
    "target_path",
    "query_file_sha256",
    "target_file_sha256",
    "query_sequence_sha256",
    "target_sequence_sha256",
    "pair_digest",
    "reference_arm",
    "reference_attempt_id",
    "reference_artifact_root",
    "reference_output_digest",
    "source_manifest",
    "source_manifest_sha256",
    "command_template",
    "environment_json",
    "maximum_tasks",
    "timeout_seconds",
    "total_gpu_budget_seconds",
    "retry_policy",
    "claim_role",
    "formal_source_data",
    "artifact_root",
    "status",
)

TELEMETRY_FIELDS = (
    "schema_version",
    "backend",
    "status",
    "device",
    "flushes",
    "tasks",
    "scoreinfos",
    "attempts",
    "selected",
    "cpu_prealign_calls",
    "cpu_forward_calls",
    "cpu_reverse_calls",
    "cpu_banded_sw_calls",
    "cpu_continuation_calls",
    "cpu_failures",
    "fallback_calls",
    "gpu_preselect_seconds",
    "gpu_forward_seconds",
    "attempt_planning_seconds",
    "attempt_selection_seconds",
    "gpu_packing_seconds",
    "gpu_h2d_seconds",
    "gpu_prealign_kernel_seconds",
    "gpu_selection_kernel_seconds",
    "gpu_forward_kernel_seconds",
    "gpu_endpoint_reduce_seconds",
    "gpu_d2h_seconds",
    "gpu_unattributed_overhead_seconds",
    "host_input_bytes",
    "device_input_bytes",
    "device_workspace_peak_bytes",
    "device_output_bytes",
    "backend_total_seconds",
    "cpu_substring_seconds",
    "cpu_continuation_seconds",
    "cpu_reverse_start_seconds",
    "cpu_banded_traceback_seconds",
    "cpu_cigar_seconds",
    "downstream_conversion_seconds",
    "cluster_sort_seconds",
    "filter_seconds",
    "error",
)

COMPARATOR_BINARY_FIELDS = (
    "raw_score_top5_equal",
    "raw_stability_top5_equal",
    "raw_nt_top5_equal",
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "all_three_top5_equal",
    "boundary_ties_equal",
)
COMPARATOR_COUNT_FIELDS = (
    "baseline_rows",
    "candidate_rows",
    "full_missing_rows",
    "full_extra_rows",
    "baseline_boundary_tie_groups",
    "candidate_boundary_tie_groups",
    "baseline_representative_conflict_clusters",
    "candidate_representative_conflict_clusters",
)

SOURCE_FIELDS = (
    "attempt_id",
    "execution_stage",
    "workload_id",
    "workload_class",
    "observation_id",
    "cache_state",
    "device",
    "status",
    "returncode",
    "timed_out",
    "wall_seconds",
    "authority_reference_wall_seconds",
    "checkpoint_reference_ratio",
    "max_rss_kib",
    "gpu_sample_count",
    "gpu_memory_peak_mib",
    "gpu_temperature_peak_c",
    "gpu_power_peak_w",
    "query_file_sha256",
    "target_file_sha256",
    "pair_digest",
    "binary_sha256",
    "environment_sha256",
    "hardware_identity_sha256",
    "source_commit",
    "output_digest",
    "reference_output_digest",
    "full_output_equal_diagnostic",
    *COMPARATOR_BINARY_FIELDS,
    *COMPARATOR_COUNT_FIELDS,
    "declared_contract_clean",
    *TELEMETRY_FIELDS[4:-1],
    "telemetry_error",
    "attempt_receipt_sha256",
    "comparison_receipt_sha256",
)


class Phase7Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase7Error(message)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(reader.fieldnames is not None, f"missing TSV header: {path}")
        rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
            f"malformed TSV: {path}")
    return rows


def atomic_write(path: Path, payload: bytes) -> None:
    require(not path.exists(), f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    require(not temporary.exists(), f"temporary path collision: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read_fasta(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA: {path}")
    sequence = b"".join(
        line.strip().upper()
        for line in path.read_bytes().splitlines()
        if line and not line.startswith(b">")
    )
    require(sequence, f"empty FASTA: {path}")
    require(not (set(sequence) - set(b"ACGTN")), f"invalid FASTA sequence: {path}")
    return sequence


def output_inventory(output_dir: Path) -> list[dict[str, Any]]:
    require(output_dir.is_dir() and not output_dir.is_symlink(), f"missing output directory: {output_dir}")
    rows: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        require(not path.is_symlink(), f"output symlink is forbidden: {path}")
        if path.is_file():
            rows.append(
                {
                    "path": str(path.relative_to(output_dir)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def output_digest(output_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    rows = output_inventory(output_dir)
    require(rows, f"no output files: {output_dir}")
    return sha256_bytes(tsv_bytes(("path", "size_bytes", "sha256"), rows)), rows


def single_output(output_dir: Path) -> Path:
    paths = [path for path in output_dir.iterdir() if path.is_file() and not path.is_symlink()]
    require(len(paths) == 1, f"expected one output in {output_dir}, found {len(paths)}")
    return paths[0]


def pair_digest(query_sequence_sha256: str, target_sequence_sha256: str) -> str:
    return sha256_bytes(
        b"ssw-cuda-phase7-pair-v1\0"
        + query_sequence_sha256.encode("ascii")
        + b"\0"
        + target_sequence_sha256.encode("ascii")
    )


def environment_template() -> str:
    values = {
        "CUDA_VISIBLE_DEVICES": "0,1",
        "FASIM_EXTEND_THREADS": "1",
        "FASIM_OUTPUT_MODE": "tfosorted",
        "FASIM_SSW_AVX2": "0",
        "FASIM_SSW_BACKEND": "cuda-forward-hybrid",
        "FASIM_SSW_CUDA_DEVICE": "{device}",
        "FASIM_SSW_FORWARD_HYBRID_MAX_TASKS": str(MAX_TASKS),
        "FASIM_SSW_FORWARD_HYBRID_TELEMETRY_PATH": "{telemetry}",
        "FASIM_SSW_ORACLE_TRACE": "0",
        "FASIM_SSW_PROFILE_CACHE": "0",
        "FASIM_SSW_PROFILE_CONTEXT": "0",
        "FASIM_TRANSFERSTRING_TABLE": "0",
        "FASIM_VERBOSE": "0",
    }
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def make_plan_row(
    *,
    attempt_id: str,
    stage: str,
    workload_id: str,
    workload_class: str,
    observation_id: int,
    cache_state: str,
    execution_order: int,
    device: int,
    query_path: str,
    target_path: str,
    query_file_sha256: str,
    target_file_sha256: str,
    query_sequence_sha256: str,
    target_sequence_sha256: str,
    reference_attempt_id: str,
    reference_artifact_root: str,
    reference_output_digest: str,
    source_manifest: str,
    timeout_seconds: int,
    claim_role: str,
) -> dict[str, str]:
    artifact_root = f".paper-artifacts/ssw-cuda-v1/forward-hybrid/formal-v2/{attempt_id}"
    return {
        "attempt_id": attempt_id,
        "execution_stage": stage,
        "arm": "F",
        "backend": "ssw_cuda_forward_hybrid_v1",
        "workload_id": workload_id,
        "workload_class": workload_class,
        "observation_id": str(observation_id),
        "cache_state": cache_state,
        "execution_order": str(execution_order),
        "device": str(device),
        "gpu_assignment": f"single_process_to_physical_{device}",
        "query_path": query_path,
        "target_path": target_path,
        "query_file_sha256": query_file_sha256,
        "target_file_sha256": target_file_sha256,
        "query_sequence_sha256": query_sequence_sha256,
        "target_sequence_sha256": target_sequence_sha256,
        "pair_digest": pair_digest(query_sequence_sha256, target_sequence_sha256),
        "reference_arm": "A",
        "reference_attempt_id": reference_attempt_id,
        "reference_artifact_root": reference_artifact_root,
        "reference_output_digest": reference_output_digest,
        "source_manifest": source_manifest,
        "source_manifest_sha256": sha256_file(ROOT / source_manifest),
        "command_template": "{binary} -f1 {target} -f2 {query} -r 0 -cn 1 -O {output}",
        "environment_json": environment_template(),
        "maximum_tasks": str(MAX_TASKS),
        "timeout_seconds": str(timeout_seconds),
        "total_gpu_budget_seconds": str(GPU_BUDGET_SECONDS),
        "retry_policy": "none",
        "claim_role": claim_role,
        "formal_source_data": "1",
        "artifact_root": artifact_root,
        "status": "preregistered_not_run",
    }


def expected_plan_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    order = 1
    for source in read_tsv(HOLDOUT):
        workload_id = source["workload_id"]
        reference_attempt = f"{workload_id}__repeat00"
        reference_root = (
            PHASE2_ARTIFACT_ROOT / "formal" / reference_attempt / "authority/output"
        )
        reference_digest, _ = output_digest(reference_root)
        rows.append(
            make_plan_row(
                attempt_id=f"p7v2c_{workload_id}",
                stage="correctness_regression",
                workload_id=workload_id,
                workload_class=f"consumed_{source['length_stratum']}",
                observation_id=0,
                cache_state="not_requested",
                execution_order=order,
                device=(order - 1) % 2,
                query_path=source["query_path"],
                target_path=source["target_path"],
                query_file_sha256=source["query_file_sha256"],
                target_file_sha256=source["target_file_sha256"],
                query_sequence_sha256=source["query_sequence_sha256"],
                target_sequence_sha256=source["target_sequence_sha256"],
                reference_attempt_id=reference_attempt,
                reference_artifact_root=str(reference_root.relative_to(ROOT)),
                reference_output_digest=reference_digest,
                source_manifest=str(HOLDOUT.relative_to(ROOT)),
                timeout_seconds=CORRECTNESS_TIMEOUT_SECONDS,
                claim_role="consumed_regression_only",
            )
        )
        order += 1

    phase1_plan = read_tsv(PHASE1_PLAN)
    phase1_source = {row["attempt_id"]: row for row in read_tsv(PHASE1_SOURCE)}
    by_key = {
        (row["workload_id"], int(row["observation_id"])): row
        for row in phase1_plan
        if row["profile_mode"] == "profile_off"
    }
    schedules = (
        PERFORMANCE_WORKLOADS,
        tuple(reversed(PERFORMANCE_WORKLOADS)),
        PERFORMANCE_WORKLOADS[2:] + PERFORMANCE_WORKLOADS[:2],
        tuple(reversed(PERFORMANCE_WORKLOADS[1:] + PERFORMANCE_WORKLOADS[:1])),
        PERFORMANCE_WORKLOADS,
    )
    for observation_id, schedule in enumerate(schedules, start=1):
        for workload_id in schedule:
            source = by_key[(workload_id, observation_id)]
            authority = phase1_source[source["attempt_id"]]
            authority_root = Path(str(authority["artifact_receipt"])).parent / "output"
            require((ROOT / authority_root).is_dir(), f"missing Phase 1 authority output: {authority_root}")
            rows.append(
                make_plan_row(
                    attempt_id=f"p7v2p_{workload_id}_o{observation_id:02d}",
                    stage="fixed_development_pilot",
                    workload_id=workload_id,
                    workload_class=source["workload_class"],
                    observation_id=observation_id,
                    cache_state=source["cache_state"],
                    execution_order=order,
                    device=(order - 1) % 2,
                    query_path=source["query_path"],
                    target_path=source["target_path"],
                    query_file_sha256=source["query_file_sha256"],
                    target_file_sha256=source["target_file_sha256"],
                    query_sequence_sha256=source["query_sequence_sha256"],
                    target_sequence_sha256=source["target_sequence_sha256"],
                    reference_attempt_id=source["attempt_id"],
                    reference_artifact_root=str(authority_root),
                    reference_output_digest=str(authority["output_digest"]),
                    source_manifest=str(PHASE1_PLAN.relative_to(ROOT)),
                    timeout_seconds=PERFORMANCE_TIMEOUT_SECONDS,
                    claim_role="development_checkpoint_only",
                )
            )
            order += 1
    require(len(rows) == 49, f"unexpected Phase 7 plan cardinality: {len(rows)}")
    return rows


def check_plan() -> list[dict[str, str]]:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    require(state["active_phase"] == 7, "Phase 7 runner requires active_phase=7")
    require(state["phase_status"]["6"] == "pass" and
            state["phase_status"]["7"] == "in_progress",
            "Phase 7 state transition drift")
    require(state["bioinformatics_b3_track"] == "closed_amdahl",
            "Phase 7 cannot reopen the closed Amdahl decision")
    require(sha256_file(COMPARATOR) == COMPARATOR_SHA256,
            "Phase 7 offline comparator digest drift")
    h2 = json.loads(H2_RECEIPT.read_text(encoding="utf-8"))
    require(h2["rescue_track_status"] == "closed_performance_no_go",
            "historical H2 track is not closed")
    require(abs(float(h2["primary_aggregate_speedup"]) - 0.25759196676394047) < 1e-15,
            "historical H2 performance anchor drift")
    repair = json.loads(REPAIR_RECEIPT.read_text(encoding="utf-8"))
    require(repair["repair_number"] == 1 and repair["v1_status"] == "incomplete",
            "Phase 7 repair receipt drift")
    require(repair["v1_execution_receipt_sha256"] ==
            "7380d57c286db1540c05e9803a26d329ab6497f2ec9e7e6cd64b244e1b0ba1f1",
            "Phase 7 v1 receipt anchor drift")
    repaired_input = ROOT / repair["input_path"]
    require(sha256_file(repaired_input) == repair["input_file_sha256"],
            "Phase 7 repaired input file drift")
    require(sha256_bytes(read_fasta(repaired_input)) ==
            repair["required_uppercase_sequence_sha256"],
            "Phase 7 repaired input normalization drift")
    observed = read_tsv(PLAN)
    require(tuple(observed[0].keys()) == PLAN_FIELDS, "Phase 7 plan schema mismatch")
    expected = expected_plan_rows()
    require(observed == expected, "Phase 7 attempt plan is not the deterministic frozen plan")
    require([int(row["execution_order"]) for row in observed] == list(range(1, 50)),
            "Phase 7 execution order is not contiguous")
    require(sum(row["execution_stage"] == "correctness_regression" for row in observed) == 24,
            "Phase 7 correctness cardinality drift")
    require(sum(row["execution_stage"] == "fixed_development_pilot" for row in observed) == 25,
            "Phase 7 performance cardinality drift")
    for workload_id in PERFORMANCE_WORKLOADS:
        workload_rows = [row for row in observed if row["workload_id"] == workload_id and
                         row["execution_stage"] == "fixed_development_pilot"]
        require(len(workload_rows) == 5, f"{workload_id}: expected five F observations")
    return observed


def git_output(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def require_clean_committed_execution() -> str:
    require(not git_output("status", "--porcelain=v1"),
            "formal Phase 7 execution requires a clean worktree")
    head = git_output("rev-parse", "HEAD")
    for relative in (
        "paper/ssw_cuda/forward_hybrid_protocol.md",
        "paper/ssw_cuda/forward_hybrid_attempt_plan_v2.tsv",
        "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.md",
        "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.json",
        "reproduce/ssw_cuda/run_forward_hybrid.py",
        "scripts/check_ssw_cuda_phase7.sh",
        "tests/ssw_cuda/test_forward_hybrid_runner.py",
    ):
        result = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{relative}"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        require(result.returncode == 0, f"formal Phase 7 dependency is not committed: {relative}")
    return head


def validate_input(row: dict[str, str]) -> tuple[Path, Path]:
    query = ROOT / row["query_path"]
    target = ROOT / row["target_path"]
    require(sha256_file(query) == row["query_file_sha256"],
            f"{row['attempt_id']}: query file digest drift")
    require(sha256_file(target) == row["target_file_sha256"],
            f"{row['attempt_id']}: target file digest drift")
    require(sha256_bytes(read_fasta(query)) == row["query_sequence_sha256"],
            f"{row['attempt_id']}: query sequence digest drift")
    require(sha256_bytes(read_fasta(target)) == row["target_sequence_sha256"],
            f"{row['attempt_id']}: target sequence digest drift")
    return query, target


def validate_v1_repair_evidence() -> None:
    repair = json.loads(REPAIR_RECEIPT.read_text(encoding="utf-8"))
    require(V1_EXECUTION_RECEIPT.is_file() and not V1_EXECUTION_RECEIPT.is_symlink(),
            "missing Phase 7 v1 failure receipt")
    require(sha256_file(V1_EXECUTION_RECEIPT) == repair["v1_execution_receipt_sha256"],
            "Phase 7 v1 failure receipt drift")
    receipt = json.loads(V1_EXECUTION_RECEIPT.read_text(encoding="utf-8"))
    require(receipt["status"] == "incomplete" and receipt["completed_attempt_receipts"] == 25,
            "Phase 7 v1 failure cardinality drift")
    require(receipt["replacement_retries"] == 0,
            "Phase 7 v1 unexpectedly records a replacement retry")
    require(receipt["stop_reason"] ==
            "runner_failure:p7p_medium_h19_chr22_2mb_o01",
            "Phase 7 v1 stop reason drift")


def cache_drop_hint(paths: Sequence[Path]) -> str:
    if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED"):
        return "unsupported"
    statuses: list[str] = []
    for path in paths:
        try:
            with path.open("rb") as handle:
                os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            statuses.append("advised")
        except OSError as exc:
            statuses.append(f"error_{exc.errno}")
    return ";".join(statuses)


def kill_process_group(process: subprocess.Popen[Any]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def sample_gpu(device: int) -> tuple[str, str, str] | None:
    result = subprocess.run(
        [
            "nvidia-smi",
            f"--id={device}",
            "--query-gpu=memory.used,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    fields = [field.strip() for field in result.stdout.strip().split(",")]
    return tuple(fields) if len(fields) == 3 else None  # type: ignore[return-value]


def hardware_identity(device: int) -> dict[str, Any]:
    cpu: dict[str, Any] = {
        "logical_cpu_count": os.cpu_count(),
        "machine": platform.machine(),
        "platform": platform.platform(),
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            if key in {"model name", "microcode"} and key not in cpu:
                cpu[key.replace(" ", "_")] = value
    gpu_result = subprocess.run(
        [
            "nvidia-smi",
            f"--id={device}",
            "--query-gpu=index,uuid,name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    require(gpu_result.returncode == 0, f"cannot identify GPU {device}: {gpu_result.stderr.strip()}")
    fields = [field.strip() for field in gpu_result.stdout.strip().split(",")]
    require(len(fields) == 6, f"unexpected GPU identity schema for device {device}")
    return {
        "hostname": platform.node(),
        "cpu": cpu,
        "gpu": {
            "index": fields[0],
            "uuid": fields[1],
            "name": fields[2],
            "driver_version": fields[3],
            "memory_total_mib": fields[4],
            "compute_capability": fields[5],
        },
    }


def parse_max_rss(path: Path) -> int | None:
    if not path.is_file():
        return None
    values: list[int] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("Maximum resident set size (kbytes):"):
            values.append(int(line.split(":", 1)[1].strip()))
    require(len(values) <= 1, f"duplicate maximum RSS in {path}")
    return values[0] if values else None


def parse_telemetry(path: Path) -> dict[str, str]:
    require(path.is_file() and not path.is_symlink(), f"missing telemetry: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == TELEMETRY_FIELDS,
                f"forward-hybrid telemetry schema mismatch: {path}")
        rows = list(reader)
    require(len(rows) == 1 and None not in rows[0] and
            all(value is not None for value in rows[0].values()),
            f"invalid forward-hybrid telemetry cardinality: {path}")
    row = rows[0]
    require(row["schema_version"] == SCHEMA_VERSION, "telemetry schema version drift")
    require(row["backend"] == "cuda-forward-hybrid", "telemetry backend drift")
    return row


def telemetry_contract_clean(row: dict[str, str]) -> bool:
    integer_fields = (
        "flushes",
        "tasks",
        "scoreinfos",
        "attempts",
        "selected",
        "cpu_prealign_calls",
        "cpu_forward_calls",
        "cpu_reverse_calls",
        "cpu_banded_sw_calls",
        "cpu_continuation_calls",
        "cpu_failures",
        "fallback_calls",
        "host_input_bytes",
        "device_input_bytes",
        "device_workspace_peak_bytes",
        "device_output_bytes",
    )
    try:
        values = {field: int(row[field]) for field in integer_fields}
        for field in TELEMETRY_FIELDS:
            if field.endswith("_seconds"):
                value = float(row[field])
                if not math.isfinite(value) or value < 0.0:
                    return False
    except (KeyError, ValueError):
        return False
    return (
        row["status"] == "complete"
        and row["error"] == "none"
        and values["flushes"] > 0
        and values["tasks"] > 0
        and values["selected"] == values["cpu_continuation_calls"]
        and values["cpu_prealign_calls"] == 0
        and values["cpu_forward_calls"] == 0
        and values["cpu_reverse_calls"] == values["cpu_continuation_calls"]
        and values["cpu_banded_sw_calls"] == values["cpu_continuation_calls"]
        and values["cpu_failures"] == 0
        and values["fallback_calls"] == 0
    )


def artifact_manifest(attempt_dir: Path) -> tuple[list[dict[str, Any]], str]:
    excluded = {"attempt.json", "artifact_manifest.tsv", "artifact_manifest.sha256"}
    rows: list[dict[str, Any]] = []
    for path in sorted(attempt_dir.rglob("*")):
        require(not path.is_symlink(), f"attempt artifact symlink is forbidden: {path}")
        if path.is_file() and str(path.relative_to(attempt_dir)) not in excluded:
            rows.append(
                {
                    "path": str(path.relative_to(attempt_dir)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    payload = tsv_bytes(("path", "size_bytes", "sha256"), rows)
    return rows, sha256_bytes(payload)


def run_attempt(
    row: dict[str, str], binary: Path, binary_sha256: str, source_commit: str
) -> dict[str, Any]:
    query, target = validate_input(row)
    attempt_dir = ROOT / row["artifact_root"]
    require(not attempt_dir.exists(), f"refusing to replace attempt: {attempt_dir}")
    attempt_dir.mkdir(parents=True)
    output_dir = attempt_dir / "output"
    output_dir.mkdir()
    telemetry_path = attempt_dir / "telemetry.tsv"
    stdout_path = attempt_dir / "stdout.log"
    stderr_path = attempt_dir / "stderr.log"
    resource_path = attempt_dir / "resource.log"
    gpu_path = attempt_dir / "gpu_samples.tsv"

    command = [
        str(binary.resolve()),
        "-f1",
        str(target.resolve()),
        "-f2",
        str(query.resolve()),
        "-r",
        "0",
        "-cn",
        "1",
        "-O",
        str(output_dir.resolve()),
    ]
    environment_values = json.loads(row["environment_json"])
    environment_values = {
        key: value.format(device=row["device"], telemetry=str(telemetry_path.resolve()))
        for key, value in environment_values.items()
    }
    environment = {**os.environ, **environment_values}
    environment_sha256 = sha256_bytes(json_bytes(environment_values))
    attempt_hardware = hardware_identity(int(row["device"]))
    hardware_identity_sha256 = sha256_bytes(json_bytes(attempt_hardware))
    measured_command = ["/usr/bin/time", "-v", "-o", str(resource_path), *command]
    cache_hint = (
        cache_drop_hint((query, target))
        if row["cache_state"] == "cold_advisory"
        else "not_requested"
    )
    started_utc = utc_now()
    started = time.monotonic()
    timed_out = False
    gpu_rows: list[dict[str, str]] = []
    with stdout_path.open("x", encoding="utf-8") as stdout_handle, \
            stderr_path.open("x", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            measured_command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        deadline = started + int(row["timeout_seconds"])
        while process.poll() is None:
            sampled = sample_gpu(int(row["device"]))
            if sampled is not None:
                gpu_rows.append(
                    {
                        "elapsed_seconds": format(time.monotonic() - started, ".9f"),
                        "memory_used_mib": sampled[0],
                        "temperature_c": sampled[1],
                        "power_w": sampled[2],
                    }
                )
            if time.monotonic() >= deadline:
                timed_out = True
                kill_process_group(process)
                break
            time.sleep(0.2)
        returncode = 124 if timed_out else int(process.wait())
    wall_seconds = time.monotonic() - started
    atomic_write(
        gpu_path,
        tsv_bytes(("elapsed_seconds", "memory_used_mib", "temperature_c", "power_w"), gpu_rows),
    )

    digest = ""
    output_rows = output_inventory(output_dir)
    output_error = "none"
    if returncode == 0 and not timed_out:
        try:
            digest, output_rows = output_digest(output_dir)
        except Phase7Error as exc:
            output_error = str(exc)
    telemetry: dict[str, str] = {}
    telemetry_error = "none"
    if telemetry_path.exists():
        try:
            telemetry = parse_telemetry(telemetry_path)
        except Phase7Error as exc:
            telemetry_error = str(exc)
    else:
        telemetry_error = "missing telemetry"
    telemetry_clean = bool(telemetry) and telemetry_contract_clean(telemetry)
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    oom_detected = "out of memory" in stderr_text.lower() or "std::bad_alloc" in stderr_text
    fallback_count = int(telemetry.get("fallback_calls", "0")) if telemetry else 0
    failure_reasons = []
    if timed_out:
        failure_reasons.append("timeout")
    if returncode != 0:
        failure_reasons.append(f"returncode_{returncode}")
    if oom_detected:
        failure_reasons.append("oom")
    if output_error != "none":
        failure_reasons.append("invalid_output")
    if telemetry_error != "none" or not telemetry_clean:
        failure_reasons.append("invalid_telemetry")
    if fallback_count:
        failure_reasons.append("fallback")
    status = (
        "complete"
        if returncode == 0 and not timed_out and output_error == "none" and
        telemetry_error == "none" and telemetry_clean
        else "technical_failure"
    )
    manifest_rows, manifest_sha256 = artifact_manifest(attempt_dir)
    atomic_write(
        attempt_dir / "artifact_manifest.tsv",
        tsv_bytes(("path", "size_bytes", "sha256"), manifest_rows),
    )
    atomic_write(
        attempt_dir / "artifact_manifest.sha256",
        f"{manifest_sha256}  artifact_manifest.tsv\n".encode("ascii"),
    )
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "status": status,
        "start_utc": started_utc,
        "end_utc": utc_now(),
        "source_commit": source_commit,
        "binary_path": str(binary.resolve()),
        "binary_sha256": binary_sha256,
        "command": command,
        "measured_command": measured_command,
        "environment": environment_values,
        "environment_sha256": environment_sha256,
        "hardware_identity": attempt_hardware,
        "hardware_identity_sha256": hardware_identity_sha256,
        "plan_row": row,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": wall_seconds,
        "cache_drop_hint": cache_hint,
        "max_rss_kib": parse_max_rss(resource_path),
        "gpu_samples": len(gpu_rows),
        "gpu_memory_peak_mib": max((float(item["memory_used_mib"]) for item in gpu_rows), default=None),
        "gpu_temperature_peak_c": max((float(item["temperature_c"]) for item in gpu_rows), default=None),
        "gpu_power_peak_w": max((float(item["power_w"]) for item in gpu_rows), default=None),
        "output_digest": digest,
        "output_manifest": output_rows,
        "partial_output_file_count": len(output_rows) if status != "complete" else 0,
        "output_error": output_error,
        "telemetry": telemetry,
        "telemetry_error": telemetry_error,
        "telemetry_contract_clean": telemetry_clean,
        "fallback_count": fallback_count,
        "fallback_reason": "none" if fallback_count == 0 else "telemetry_reported_fallback",
        "oom_detected": oom_detected,
        "failure_reason": "none" if not failure_reasons else ";".join(failure_reasons),
        "artifact_manifest_sha256": manifest_sha256,
    }
    atomic_write(attempt_dir / "attempt.json", json_bytes(receipt))
    return receipt


def execute(binary: Path) -> None:
    rows = check_plan()
    source_commit = require_clean_committed_execution()
    validate_v1_repair_evidence()
    require(binary.is_file() and not binary.is_symlink(), f"missing Phase 7 binary: {binary}")
    binary_sha256 = sha256_file(binary)
    require(not SNAPSHOT_ROOT.exists(), f"Phase 7 snapshot already exists: {SNAPSHOT_ROOT}")
    require(not FORMAL_ROOT.exists(), f"formal Phase 7 root already exists: {FORMAL_ROOT}")
    require(not EXECUTION_RECEIPT.exists(), "Phase 7 execution receipt already exists")
    atomic_write(SNAPSHOT_BINARY, binary.read_bytes())
    SNAPSHOT_BINARY.chmod(0o755)
    atomic_write(
        SNAPSHOT_ROOT / "snapshot.json",
        json_bytes(
            {
                "schema_version": 1,
                "source_commit": source_commit,
                "source_binary_path": str(binary.resolve()),
                "binary_path": str(SNAPSHOT_BINARY.resolve()),
                "binary_sha256": binary_sha256,
                "plan_sha256": sha256_file(PLAN),
                "created_utc": utc_now(),
            }
        ),
    )
    FORMAL_ROOT.mkdir(parents=True)
    started_utc = utc_now()
    started = time.monotonic()
    receipts: list[dict[str, Any]] = []
    stop_reason = "none"
    runner_error = "none"
    for row in rows:
        remaining_budget = GPU_BUDGET_SECONDS - (time.monotonic() - started)
        if remaining_budget < int(row["timeout_seconds"]):
            stop_reason = "fixed_gpu_budget_insufficient_for_next_frozen_timeout"
            break
        try:
            receipt = run_attempt(row, SNAPSHOT_BINARY, binary_sha256, source_commit)
        except (OSError, ValueError, Phase7Error, subprocess.SubprocessError) as exc:
            runner_error = str(exc)
            stop_reason = f"runner_failure:{row['attempt_id']}"
            break
        receipts.append(receipt)
        if receipt["status"] != "complete":
            stop_reason = f"technical_failure:{row['attempt_id']}"
            break
    elapsed = time.monotonic() - started
    status = "complete" if len(receipts) == len(rows) else "incomplete"
    execution_receipt = {
        "schema_version": 1,
        "status": status,
        "stop_reason": stop_reason,
        "runner_error": runner_error,
        "start_utc": started_utc,
        "end_utc": utc_now(),
        "source_commit": source_commit,
        "binary_path": str(SNAPSHOT_BINARY.resolve()),
        "binary_sha256": binary_sha256,
        "plan_path": str(PLAN.relative_to(ROOT)),
        "plan_sha256": sha256_file(PLAN),
        "planned_attempts": len(rows),
        "completed_attempt_receipts": len(receipts),
        "technical_failures": sum(item["status"] != "complete" for item in receipts),
        "replacement_retries": 0,
        "elapsed_seconds": elapsed,
        "gpu_budget_seconds": GPU_BUDGET_SECONDS,
        "artifact_root": str(FORMAL_ROOT.relative_to(ROOT)),
    }
    atomic_write(EXECUTION_RECEIPT, json_bytes(execution_receipt))
    print(f"Phase 7 execution status={status} attempts={len(receipts)}/{len(rows)}")
    if status != "complete":
        raise Phase7Error(f"formal execution stopped: {stop_reason}: {runner_error}")


def parse_comparator_stdout(stdout: str) -> dict[str, int]:
    raw: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            raw[key] = value
    required = (*COMPARATOR_BINARY_FIELDS, *COMPARATOR_COUNT_FIELDS)
    require(all(field in raw for field in required),
            "offline comparator omitted required metrics")
    metrics: dict[str, int] = {}
    for field in required:
        try:
            metrics[field] = int(raw[field])
        except ValueError as exc:
            raise Phase7Error(f"invalid comparator metric {field}={raw[field]}") from exc
    require(all(metrics[field] in {0, 1} for field in COMPARATOR_BINARY_FIELDS),
            "offline comparator emitted non-binary equality metric")
    require(all(metrics[field] >= 0 for field in COMPARATOR_COUNT_FIELDS),
            "offline comparator emitted negative count")
    require(metrics["all_three_top5_equal"] == int(all(
        metrics[field] == 1 for field in (
            "clustered_score_top5_equal",
            "clustered_stability_top5_equal",
            "clustered_nt_top5_equal",
        )
    )), "offline comparator aggregate metric is inconsistent")
    return metrics


def comparison_clean(metrics: dict[str, int]) -> bool:
    return all(metrics[field] == 1 for field in (
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "boundary_ties_equal",
    ))


def run_comparison(row: dict[str, str], receipt: dict[str, Any]) -> dict[str, Any]:
    comparison_dir = COMPARISON_ROOT / row["attempt_id"]
    require(not comparison_dir.exists(), f"refusing to replace comparison: {comparison_dir}")
    comparison_dir.mkdir(parents=True)
    baseline = single_output(ROOT / row["reference_artifact_root"])
    candidate = single_output(ROOT / row["artifact_root"] / "output")
    details = comparison_dir / "details.tsv"
    command = [
        sys.executable,
        str(COMPARATOR),
        "--baseline",
        str(baseline),
        "--candidate",
        str(candidate),
        "--k",
        "5",
        "--details",
        str(details),
    ]
    started = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=CORRECTNESS_TIMEOUT_SECONDS,
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    atomic_write(comparison_dir / "stdout.log", stdout.encode("utf-8"))
    atomic_write(comparison_dir / "stderr.log", stderr.encode("utf-8"))
    if not details.exists():
        atomic_write(details, b"")
    metrics: dict[str, int] = {}
    status = "technical_failure"
    error = "none"
    try:
        require(not timed_out, "offline comparator timed out")
        require(returncode in {0, 1}, f"unsupported comparator return code: {returncode}")
        require(details.stat().st_size > 0, "offline comparator details are empty")
        metrics = parse_comparator_stdout(stdout)
        full_clean = (
            metrics["full_missing_rows"] == 0
            and metrics["full_extra_rows"] == 0
            and all(metrics[field] == 1 for field in COMPARATOR_BINARY_FIELDS)
        )
        require((returncode == 0) == full_clean,
                "offline comparator return code disagrees with full-output truth")
        status = "clean" if comparison_clean(metrics) else "mismatch"
    except Phase7Error as exc:
        error = str(exc)
    comparison_receipt = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "status": status,
        "error": error,
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": time.monotonic() - started,
        "baseline_path": str(baseline),
        "baseline_sha256": sha256_file(baseline),
        "candidate_path": str(candidate),
        "candidate_sha256": sha256_file(candidate),
        "candidate_attempt_receipt_sha256": sha256_file(
            ROOT / row["artifact_root"] / "attempt.json"
        ),
        "metrics": metrics,
        "declared_contract_clean": bool(metrics) and comparison_clean(metrics),
        "full_output_equal_diagnostic": receipt["output_digest"] == row["reference_output_digest"],
        "details_sha256": sha256_file(details),
        "stdout_sha256": sha256_file(comparison_dir / "stdout.log"),
        "stderr_sha256": sha256_file(comparison_dir / "stderr.log"),
    }
    atomic_write(comparison_dir / "comparison.json", json_bytes(comparison_receipt))
    return comparison_receipt


def validate_attempt_receipt(row: dict[str, str], source_commit: str) -> dict[str, Any] | None:
    attempt_path = ROOT / row["artifact_root"] / "attempt.json"
    if not attempt_path.exists():
        return None
    require(attempt_path.is_file() and not attempt_path.is_symlink(),
            f"unsafe attempt receipt: {attempt_path}")
    receipt = json.loads(attempt_path.read_text(encoding="utf-8"))
    require(receipt["attempt_id"] == row["attempt_id"], "attempt receipt ID drift")
    require(receipt["plan_row"] == row, f"{row['attempt_id']}: embedded plan row drift")
    require(receipt["source_commit"] == source_commit,
            f"{row['attempt_id']}: source commit drift")
    require(receipt["binary_sha256"] == sha256_file(Path(receipt["binary_path"])),
            f"{row['attempt_id']}: binary digest drift")
    require(receipt["environment_sha256"] == sha256_bytes(json_bytes(receipt["environment"])),
            f"{row['attempt_id']}: environment digest drift")
    require(receipt["hardware_identity_sha256"] ==
            sha256_bytes(json_bytes(receipt["hardware_identity"])),
            f"{row['attempt_id']}: hardware identity digest drift")
    if receipt["status"] != "complete":
        return receipt
    digest, output_rows = output_digest(ROOT / row["artifact_root"] / "output")
    require(receipt["output_digest"] == digest and receipt["output_manifest"] == output_rows,
            f"{row['attempt_id']}: output inventory drift")
    telemetry = parse_telemetry(ROOT / row["artifact_root"] / "telemetry.tsv")
    require(receipt["telemetry"] == telemetry,
            f"{row['attempt_id']}: telemetry receipt drift")
    require(receipt["telemetry_contract_clean"] == telemetry_contract_clean(telemetry),
            f"{row['attempt_id']}: telemetry contract drift")
    manifest_rows, manifest_sha256 = artifact_manifest(ROOT / row["artifact_root"])
    observed_manifest = read_tsv(ROOT / row["artifact_root"] / "artifact_manifest.tsv")
    expected_manifest = [
        {key: str(value) for key, value in item.items()} for item in manifest_rows
    ]
    require(observed_manifest == expected_manifest,
            f"{row['attempt_id']}: artifact manifest drift")
    require(receipt["artifact_manifest_sha256"] == manifest_sha256,
            f"{row['attempt_id']}: artifact manifest digest drift")
    return receipt


def validate_comparison_receipt(
    row: dict[str, str], attempt_receipt: dict[str, Any]
) -> dict[str, Any] | None:
    path = COMPARISON_ROOT / row["attempt_id"] / "comparison.json"
    if not path.exists():
        return None
    require(path.is_file() and not path.is_symlink(), f"unsafe comparison receipt: {path}")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt["attempt_id"] == row["attempt_id"], "comparison receipt ID drift")
    require(receipt["candidate_attempt_receipt_sha256"] == sha256_file(
        ROOT / row["artifact_root"] / "attempt.json"
    ), f"{row['attempt_id']}: comparison attempt binding drift")
    require(receipt["baseline_sha256"] == sha256_file(Path(receipt["baseline_path"])),
            f"{row['attempt_id']}: comparison baseline drift")
    require(receipt["candidate_sha256"] == sha256_file(Path(receipt["candidate_path"])),
            f"{row['attempt_id']}: comparison candidate drift")
    for name in ("details", "stdout", "stderr"):
        artifact = path.parent / f"{name}.tsv" if name == "details" else path.parent / f"{name}.log"
        require(receipt[f"{name}_sha256"] == sha256_file(artifact),
                f"{row['attempt_id']}: comparison {name} drift")
    metrics = parse_comparator_stdout((path.parent / "stdout.log").read_text(encoding="utf-8"))
    require(receipt["metrics"] == metrics, f"{row['attempt_id']}: comparison metrics drift")
    require(receipt["declared_contract_clean"] == comparison_clean(metrics),
            f"{row['attempt_id']}: comparison gate drift")
    require(receipt["full_output_equal_diagnostic"] ==
            (attempt_receipt["output_digest"] == row["reference_output_digest"]),
            f"{row['attempt_id']}: L8 diagnostic drift")
    return receipt


def optional(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".12g") if math.isfinite(value) else ""
    return str(value)


def source_rows(
    rows: list[dict[str, str]],
    attempts: dict[str, dict[str, Any] | None],
    comparisons: dict[str, dict[str, Any] | None],
) -> list[dict[str, str]]:
    phase1 = {row["attempt_id"]: row for row in read_tsv(PHASE1_SOURCE)}
    result: list[dict[str, str]] = []
    for plan_row in rows:
        attempt = attempts[plan_row["attempt_id"]]
        comparison = comparisons[plan_row["attempt_id"]]
        authority_wall = ""
        if plan_row["execution_stage"] == "fixed_development_pilot":
            authority_wall = phase1[plan_row["reference_attempt_id"]]["outer_wall_seconds"]
        item = {field: "" for field in SOURCE_FIELDS}
        item.update(
            attempt_id=plan_row["attempt_id"],
            execution_stage=plan_row["execution_stage"],
            workload_id=plan_row["workload_id"],
            workload_class=plan_row["workload_class"],
            observation_id=plan_row["observation_id"],
            cache_state=plan_row["cache_state"],
            device=plan_row["device"],
            status="not_started" if attempt is None else str(attempt["status"]),
            query_file_sha256=plan_row["query_file_sha256"],
            target_file_sha256=plan_row["target_file_sha256"],
            pair_digest=plan_row["pair_digest"],
            reference_output_digest=plan_row["reference_output_digest"],
            authority_reference_wall_seconds=authority_wall,
        )
        if attempt is not None:
            item.update(
                returncode=str(attempt["returncode"]),
                timed_out=str(int(bool(attempt["timed_out"]))),
                wall_seconds=optional(attempt["wall_seconds"]),
                max_rss_kib=optional(attempt["max_rss_kib"]),
                gpu_sample_count=str(attempt["gpu_samples"]),
                gpu_memory_peak_mib=optional(attempt["gpu_memory_peak_mib"]),
                gpu_temperature_peak_c=optional(attempt["gpu_temperature_peak_c"]),
                gpu_power_peak_w=optional(attempt["gpu_power_peak_w"]),
                binary_sha256=str(attempt["binary_sha256"]),
                environment_sha256=str(attempt["environment_sha256"]),
                hardware_identity_sha256=str(attempt["hardware_identity_sha256"]),
                source_commit=str(attempt["source_commit"]),
                output_digest=str(attempt["output_digest"]),
                attempt_receipt_sha256=sha256_file(
                    ROOT / plan_row["artifact_root"] / "attempt.json"
                ),
            )
            if authority_wall and float(attempt["wall_seconds"]) > 0.0:
                item["checkpoint_reference_ratio"] = optional(
                    float(authority_wall) / float(attempt["wall_seconds"])
                )
            telemetry = attempt.get("telemetry", {})
            if telemetry:
                for field in TELEMETRY_FIELDS[4:-1]:
                    item[field] = str(telemetry[field])
                item["telemetry_error"] = str(telemetry["error"])
        if comparison is not None:
            metrics = comparison["metrics"]
            for field in (*COMPARATOR_BINARY_FIELDS, *COMPARATOR_COUNT_FIELDS):
                item[field] = str(metrics[field])
            item["declared_contract_clean"] = str(
                int(bool(comparison["declared_contract_clean"]))
            )
            item["full_output_equal_diagnostic"] = str(
                int(bool(comparison["full_output_equal_diagnostic"]))
            )
            item["comparison_receipt_sha256"] = sha256_file(
                COMPARISON_ROOT / plan_row["attempt_id"] / "comparison.json"
            )
        result.append(item)
    return result


def median_float(rows: Sequence[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows if row[field] != ""]
    require(values, f"no numeric values for {field}")
    return float(statistics.median(values))


def build_projection(source: list[dict[str, str]]) -> dict[str, Any]:
    h2 = json.loads(H2_RECEIPT.read_text(encoding="utf-8"))
    phase1_stats = json.loads(PHASE1_STATS.read_text(encoding="utf-8"))
    workloads: dict[str, Any] = {}
    for workload_id in PERFORMANCE_WORKLOADS:
        selected = [
            row for row in source
            if row["execution_stage"] == "fixed_development_pilot"
            and row["workload_id"] == workload_id
            and row["status"] == "complete"
        ]
        if len(selected) != 5:
            workloads[workload_id] = {
                "status": "incomplete",
                "completed_observations": len(selected),
            }
            continue
        authority_wall = median_float(selected, "authority_reference_wall_seconds")
        f_wall = median_float(selected, "wall_seconds")
        continuation = median_float(selected, "cpu_continuation_seconds")
        optimistic_g_wall = max(0.0, f_wall - continuation)
        attempts = median_float(selected, "attempts")
        selected_attempts = median_float(selected, "selected")
        workloads[workload_id] = {
            "status": "complete",
            "observations": 5,
            "authority_reference_median_wall_seconds": authority_wall,
            "forward_hybrid_median_wall_seconds": f_wall,
            "checkpoint_reference_ratio": authority_wall / f_wall,
            "gpu_packing_median_seconds": median_float(selected, "gpu_packing_seconds"),
            "gpu_h2d_median_seconds": median_float(selected, "gpu_h2d_seconds"),
            "gpu_prealign_median_seconds": median_float(selected, "gpu_prealign_kernel_seconds"),
            "gpu_selection_median_seconds": median_float(selected, "gpu_selection_kernel_seconds"),
            "gpu_forward_median_seconds": median_float(selected, "gpu_forward_kernel_seconds"),
            "gpu_endpoint_reduce_median_seconds": median_float(
                selected, "gpu_endpoint_reduce_seconds"
            ),
            "gpu_d2h_median_seconds": median_float(selected, "gpu_d2h_seconds"),
            "cpu_reverse_start_median_seconds": median_float(
                selected, "cpu_reverse_start_seconds"
            ),
            "cpu_banded_traceback_median_seconds": median_float(
                selected, "cpu_banded_traceback_seconds"
            ),
            "cpu_continuation_median_seconds": continuation,
            "selected_attempt_ratio": selected_attempts / attempts if attempts else 0.0,
            "projected_full_gpu_wall_lower_bound_seconds": optimistic_g_wall,
            "projected_full_gpu_wall_upper_bound_seconds": f_wall,
            "projected_full_gpu_reference_speedup_lower": authority_wall / f_wall,
            "projected_full_gpu_reference_speedup_upper": (
                authority_wall / optimistic_g_wall if optimistic_g_wall > 0.0 else None
            ),
            "declared_contract_clean_observations": sum(
                row["declared_contract_clean"] == "1" for row in selected
            ),
            "full_output_equal_diagnostic_observations": sum(
                row["full_output_equal_diagnostic"] == "1" for row in selected
            ),
            "phase1_addressable_fraction_median": phase1_stats["workloads"][workload_id][
                "steady_state"
            ]["p_backend_addressable"]["median"],
        }
    return {
        "schema_version": 1,
        "status": (
            "complete"
            if all(value["status"] == "complete" for value in workloads.values())
            else "incomplete"
        ),
        "role": "development_checkpoint_projection_only",
        "formal_speedup_claim": False,
        "authority_reference": {
            "source": str(PHASE1_SOURCE.relative_to(ROOT)),
            "source_sha256": sha256_file(PHASE1_SOURCE),
            "execution_epoch": 2,
            "new_authority_attempts_executed": 0,
        },
        "historical_h2_reference": {
            "source": str(H2_RECEIPT.relative_to(ROOT)),
            "source_sha256": sha256_file(H2_RECEIPT),
            "primary_aggregate_speedup": h2["primary_aggregate_speedup"],
            "hybrid_slowdown_vs_authority": h2["hybrid_slowdown_vs_authority"],
            "track_status": h2["rescue_track_status"],
            "new_h2_attempts_executed": 0,
        },
        "workloads": workloads,
        "projection_definition": {
            "lower_wall_bound": "F median wall minus measured selected CPU continuation median",
            "upper_wall_bound": "observed F median wall with no assumed L4/L5 improvement",
            "warning": "bounds are an early engineering model, not observed G performance",
        },
        "b3_speedup_threshold": 10.0,
        "b3_threshold_changed": False,
        "bioinformatics_b3_track": "closed_amdahl",
    }


def build_decision(
    rows: list[dict[str, str]],
    source: list[dict[str, str]],
    projection: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    completed = [row for row in source if row["status"] == "complete"]
    technical_complete = len(completed) == len(rows) and execution["status"] == "complete"
    comparison_complete = all(row["declared_contract_clean"] != "" for row in completed)
    declared_clean = comparison_complete and all(
        row["declared_contract_clean"] == "1" for row in completed
    )
    call_contract_clean = all(
        row["cpu_prealign_calls"] == "0"
        and row["cpu_forward_calls"] == "0"
        and row["cpu_reverse_calls"] == row["cpu_continuation_calls"]
        and row["cpu_banded_sw_calls"] == row["cpu_continuation_calls"]
        and row["cpu_failures"] == "0"
        and row["fallback_calls"] == "0"
        for row in completed
    )
    correctness_pass = technical_complete and declared_clean and call_contract_clean
    if not technical_complete:
        result = "blocked_by_environment"
        phase7_status = "blocked"
        phase8_authorized = False
    elif not correctness_pass:
        result = "forward_hybrid_performance_futility_stop"
        phase7_status = "no_go"
        phase8_authorized = False
    else:
        result = "forward_hybrid_correct_but_b3_track_closed"
        phase7_status = "pass"
        phase8_authorized = True
    return {
        "schema_version": 1,
        "decision": result,
        "phase7_status": phase7_status,
        "phase8_engineering_authorized": phase8_authorized,
        "execution_status": execution["status"],
        "execution_stop_reason": execution["stop_reason"],
        "planned_attempts": len(rows),
        "completed_attempts": len(completed),
        "correctness_regression_attempts": sum(
            row["execution_stage"] == "correctness_regression" for row in completed
        ),
        "performance_observations": sum(
            row["execution_stage"] == "fixed_development_pilot" for row in completed
        ),
        "technical_failures": len([row for row in source if row["status"] == "technical_failure"]),
        "declared_contract_mismatches": sum(
            row["declared_contract_clean"] == "0" for row in completed
        ),
        "score_clustered_top5_clean": sum(
            row["clustered_score_top5_equal"] == "1" for row in completed
        ),
        "stability_clustered_top5_clean": sum(
            row["clustered_stability_top5_equal"] == "1" for row in completed
        ),
        "nt_clustered_top5_clean": sum(
            row["clustered_nt_top5_equal"] == "1" for row in completed
        ),
        "full_output_equal_diagnostic": sum(
            row["full_output_equal_diagnostic"] == "1" for row in completed
        ),
        "cpu_call_contract_clean": call_contract_clean,
        "cpu_prealign_calls": sum(int(row["cpu_prealign_calls"]) for row in completed),
        "cpu_forward_calls": sum(int(row["cpu_forward_calls"]) for row in completed),
        "cpu_reverse_calls": sum(int(row["cpu_reverse_calls"]) for row in completed),
        "cpu_banded_traceback_calls": sum(
            int(row["cpu_banded_sw_calls"]) for row in completed
        ),
        "fallbacks": sum(int(row["fallback_calls"]) for row in completed),
        "replacement_retries": 0,
        "fresh_holdout_consumed": False,
        "application_50x668_panel_run": False,
        "historical_h2_rerun": False,
        "new_cpu_authority_performance_attempts": 0,
        "authority_reference_role": "historical_same_input_checkpoint_reference_only",
        "performance_claim_role": "development_checkpoint_projection_only",
        "formal_speedup_claim": False,
        "l8_contract_status": "diagnostic_only",
        "bioinformatics_b3_track": "closed_amdahl",
        "b3_speedup_threshold": 10.0,
        "b3_threshold_changed": False,
        "projection_status": projection["status"],
        "plan_sha256": sha256_file(PLAN),
        "execution_receipt_sha256": sha256_file(EXECUTION_RECEIPT),
        "source_data_sha256": sha256_bytes(tsv_bytes(SOURCE_FIELDS, source)),
        "projection_sha256": sha256_bytes(json_bytes(projection)),
        "source_commit": execution["source_commit"],
        "binary_sha256": execution["binary_sha256"],
        "allowed_decisions": [
            "forward_hybrid_checkpoint_pass_continue_full_gpu",
            "forward_hybrid_correct_but_b3_track_closed",
            "forward_hybrid_performance_futility_stop",
            "blocked_by_environment",
        ],
    }


def load_execution_receipt(rows: list[dict[str, str]]) -> dict[str, Any]:
    require(EXECUTION_RECEIPT.is_file() and not EXECUTION_RECEIPT.is_symlink(),
            "missing Phase 7 execution receipt")
    receipt = json.loads(EXECUTION_RECEIPT.read_text(encoding="utf-8"))
    require(receipt["plan_sha256"] == sha256_file(PLAN), "execution plan digest drift")
    require(receipt["planned_attempts"] == len(rows), "execution plan cardinality drift")
    require(receipt["replacement_retries"] == 0, "replacement retry recorded")
    require(receipt["binary_sha256"] == sha256_file(Path(receipt["binary_path"])),
            "execution snapshot binary drift")
    require(receipt["source_commit"] == json.loads(
        (SNAPSHOT_ROOT / "snapshot.json").read_text(encoding="utf-8")
    )["source_commit"], "execution snapshot commit drift")
    return receipt


def reconstruct_outputs(create_comparisons: bool) -> tuple[bytes, bytes, bytes]:
    rows = check_plan()
    execution = load_execution_receipt(rows)
    attempts: dict[str, dict[str, Any] | None] = {}
    comparisons: dict[str, dict[str, Any] | None] = {}
    for row in rows:
        attempt = validate_attempt_receipt(row, execution["source_commit"])
        attempts[row["attempt_id"]] = attempt
    if create_comparisons:
        require(not COMPARISON_ROOT.exists(),
                f"offline comparison root already exists: {COMPARISON_ROOT}")
        for row in rows:
            attempt = attempts[row["attempt_id"]]
            comparisons[row["attempt_id"]] = (
                run_comparison(row, attempt)
                if attempt is not None and attempt["status"] == "complete"
                else None
            )
    else:
        for row in rows:
            attempt = attempts[row["attempt_id"]]
            comparisons[row["attempt_id"]] = (
                validate_comparison_receipt(row, attempt)
                if attempt is not None and attempt["status"] == "complete"
                else None
            )
    source = source_rows(rows, attempts, comparisons)
    projection = build_projection(source)
    decision = build_decision(rows, source, projection, execution)
    return (
        tsv_bytes(SOURCE_FIELDS, source),
        json_bytes(projection),
        json_bytes(decision),
    )


def analyze() -> None:
    source_payload, projection_payload, decision_payload = reconstruct_outputs(True)
    atomic_write(SOURCE_DATA, source_payload)
    atomic_write(PROJECTION, projection_payload)
    atomic_write(DECISION, decision_payload)
    decision = json.loads(decision_payload)
    print(
        "Phase 7 analysis "
        f"decision={decision['decision']} completed={decision['completed_attempts']}/"
        f"{decision['planned_attempts']}"
    )


def check_results() -> None:
    for path in (SOURCE_DATA, PROJECTION, DECISION):
        require(path.is_file() and not path.is_symlink(), f"missing Phase 7 result: {path}")
    expected = reconstruct_outputs(False)
    observed = (SOURCE_DATA.read_bytes(), PROJECTION.read_bytes(), DECISION.read_bytes())
    require(observed == expected, "Phase 7 committed result reconstruction drift")
    decision = json.loads(observed[2])
    require(decision["decision"] in decision["allowed_decisions"],
            "Phase 7 decision is outside the frozen state machine")
    print(
        "Phase 7 results OK "
        f"decision={decision['decision']} attempts={decision['completed_attempts']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--check-plan", action="store_true")
    actions.add_argument("--execute", action="store_true")
    actions.add_argument("--analyze", action="store_true")
    actions.add_argument("--check-results", action="store_true")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    arguments = parser.parse_args()
    try:
        if arguments.print_plan:
            sys.stdout.buffer.write(tsv_bytes(PLAN_FIELDS, expected_plan_rows()))
        elif arguments.check_plan:
            rows = check_plan()
            print(
                "Phase 7 plan OK "
                f"rows={len(rows)} correctness=24 new_f_performance=25 new_a=0 new_h2=0"
            )
        elif arguments.execute:
            execute(arguments.binary.resolve())
        elif arguments.analyze:
            analyze()
        else:
            check_results()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, Phase7Error) as exc:
        print(f"Phase 7 error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
