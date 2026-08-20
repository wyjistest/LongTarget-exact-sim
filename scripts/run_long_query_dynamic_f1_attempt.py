#!/usr/bin/env python3
"""Run one exact F1 whole-query attempt inside a fenced pool directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLAIM_SCHEMA = "long_query_dynamic_gpu_pool_claim_v1"
RECEIPT_SCHEMA = "long_query_dynamic_gpu_attempt_receipt_v1"
EXECUTION_MODE = "consumer_driven_f1_exact_pipeline"

FASIM_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "FASIM_OUTPUT_MODE": "tfosorted",
    "FASIM_VERBOSE": "0",
    "FASIM_ALIGN_GASAL2": "1",
    "FASIM_ENABLE_PREALIGN_CUDA": "1",
    "FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE": "1",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "2812",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE": "0",
    "FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE": "1",
    "FASIM_LONG_QUERY_GPU_CONSUMER_F1_LEGACY_CPU_REPLAY": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "0",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO": "1",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "0",
}

REQUIRED_STDOUT_LINES = {"finished normally"}
REQUIRED_STDERR_LINES = {
    "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_active=1",
    "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_failures=0",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches=0",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_fallbacks=0",
}


class AttemptError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AttemptError(message)


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


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AttemptError(f"cannot read JSON {path}: {error}") from error
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def required_environment(name: str) -> str:
    value = os.environ.get(name, "")
    require(bool(value), f"missing environment variable: {name}")
    return value


def fasta_sequence(path: Path) -> str:
    pieces: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                continue
            pieces.append("".join(line.split()).upper())
    sequence = "".join(pieces)
    require(bool(sequence), "query sequence is empty")
    try:
        sequence.encode("ascii")
    except UnicodeEncodeError as error:
        raise AttemptError("query sequence is not ASCII") from error
    return sequence


def archive_interrupted_work(attempt_dir: Path, work: Path) -> None:
    if not work.exists():
        return
    diagnostics = attempt_dir / "diagnostics"
    diagnostics.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    os.replace(work, diagnostics / f"interrupted-{stamp}")


def validate_claim(claim_path: Path, attempt_dir: Path) -> dict[str, Any]:
    require(attempt_dir.is_dir() and not attempt_dir.is_symlink(), "unsafe attempt directory")
    require(claim_path.resolve() == (attempt_dir / "claim.json").resolve(), "claim is outside attempt directory")
    require(claim_path.is_file() and not claim_path.is_symlink(), "unsafe claim file")
    claim = read_json(claim_path)
    require(claim.get("schema_version") == CLAIM_SCHEMA, "claim schema drift")
    for key in ("pool_id", "job_id", "gene_id", "worker_id", "gpu_id", "lease_epoch"):
        require(str(claim.get(key) if claim.get(key) is not None else "") != "", f"claim missing {key}")
    require(isinstance(claim.get("row"), dict), "claim row is missing")
    require(isinstance(claim.get("receipt_contract"), dict), "receipt contract is missing")
    require(os.environ.get("LONGTARGET_POOL_ID") == claim["pool_id"], "pool environment mismatch")
    require(os.environ.get("LONGTARGET_POOL_JOB_ID") == claim["job_id"], "job environment mismatch")
    require(os.environ.get("LONGTARGET_POOL_WORKER_ID") == claim["worker_id"], "worker environment mismatch")
    require(os.environ.get("LONGTARGET_POOL_LEASE_EPOCH") == str(claim["lease_epoch"]), "epoch environment mismatch")
    return claim


def validate_inputs(claim: dict[str, Any]) -> dict[str, Any]:
    binary = Path(required_environment("LONGTARGET_F1_BINARY"))
    binary_sha256 = required_environment("LONGTARGET_F1_BINARY_SHA256")
    source_commit = required_environment("LONGTARGET_F1_SOURCE_COMMIT")
    target = Path(required_environment("LONGTARGET_F1_TARGET"))
    target_sha256 = required_environment("LONGTARGET_F1_TARGET_SHA256")
    target_length = int(required_environment("LONGTARGET_F1_TARGET_LENGTH"))
    minimum_length = int(os.environ.get("LONGTARGET_F1_MIN_QUERY_LENGTH", "2813"))
    maximum_length = int(os.environ.get("LONGTARGET_F1_MAX_QUERY_LENGTH", "12397"))
    row = claim["row"]
    query = Path(str(row.get("query_path") or ""))

    require(binary.is_absolute() and binary.is_file() and os.access(binary, os.X_OK), f"missing binary: {binary}")
    require(not binary.is_symlink(), f"binary must not be a symlink: {binary}")
    require(target.is_absolute() and target.is_file(), f"missing target: {target}")
    require(not target.is_symlink(), f"target must not be a symlink: {target}")
    require(query.is_absolute() and query.is_file(), f"missing query: {query}")
    require(not query.is_symlink(), f"query must not be a symlink: {query}")
    require(sha256_file(binary) == binary_sha256, "binary digest drift")
    require(sha256_file(target) == target_sha256, "target digest drift")
    require(sha256_file(query) == row["query_file_sha256"], "query file digest drift")

    sequence = fasta_sequence(query)
    observed_sequence_sha256 = hashlib.sha256(sequence.encode("ascii")).hexdigest()
    require(observed_sequence_sha256 == row["query_sequence_sha256"], "query sequence digest drift")
    require(len(sequence) == int(row["query_length_nt"]), "query length drift")
    require(minimum_length <= len(sequence) <= maximum_length, "query outside frozen validated length range")

    contract = claim["receipt_contract"]
    expected_contract = {
        "source_commit": source_commit,
        "binary_sha256": binary_sha256,
        "target_sha256": target_sha256,
        "execution_mode": EXECUTION_MODE,
    }
    for key, value in expected_contract.items():
        require(contract.get(key) == value, f"claim/environment contract mismatch: {key}")
    return {
        "binary": binary,
        "binary_sha256": binary_sha256,
        "source_commit": source_commit,
        "target": target,
        "target_sha256": target_sha256,
        "target_length": target_length,
        "query": query,
        "sequence": sequence,
    }


def verify_gpu_uuid(claim: dict[str, Any]) -> None:
    if os.environ.get("LONGTARGET_F1_VERIFY_GPU_UUID", "1") != "1":
        return
    expected = str(claim.get("gpu_uuid") or "")
    require(expected not in {"", "unknown"}, "claim does not freeze a GPU UUID")
    command = [
        "nvidia-smi",
        f"--id={claim['gpu_id']}",
        "--query-gpu=uuid",
        "--format=csv,noheader",
    ]
    try:
        observed = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise AttemptError(f"cannot verify GPU UUID: {error}") from error
    require(observed == expected, f"GPU UUID mismatch: expected {expected}, observed {observed}")


def write_runtime_query(path: Path, gene_id: str, sequence: str) -> None:
    with path.open("w", encoding="ascii") as handle:
        handle.write(f">{gene_id}\n")
        for start in range(0, len(sequence), 80):
            handle.write(sequence[start : start + 80] + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def require_lines(path: Path, required: set[str], label: str) -> None:
    observed = set(path.read_text(encoding="utf-8", errors="replace").splitlines())
    missing = sorted(required - observed)
    require(not missing, f"{label} missing required markers: {missing}")


def publish_attempt(
    claim: dict[str, Any],
    inputs: dict[str, Any],
    attempt_dir: Path,
    work: Path,
    started_utc: str,
    completed_utc: str,
    wall_seconds: float,
    max_rss_kb: int,
) -> None:
    require_lines(work / "stdout.log", REQUIRED_STDOUT_LINES, "stdout")
    require_lines(work / "stderr.log", REQUIRED_STDERR_LINES, "stderr")
    require((work / "f1.tsv").is_file() and (work / "f1.tsv").stat().st_size > 0, "F1 report is missing or empty")
    runtime_output = work / "runtime_output"
    artifacts = [
        path
        for path in runtime_output.glob("*-TFOsorted")
        if path.is_file() and not path.is_symlink() and path.stat().st_size > 0
    ]
    require(len(artifacts) == 1, "expected one nonempty TFOsorted artifact")
    artifact = artifacts[0]
    artifact_relative = str(artifact.relative_to(work))
    artifact_sha256 = sha256_file(artifact)
    artifact_size = artifact.stat().st_size
    artifact_rows = sum(1 for _ in artifact.open("rb"))

    run_plan = {
        "schema_version": "long_query_dynamic_f1_attempt_plan_v1",
        "pool_id": claim["pool_id"],
        "job_id": claim["job_id"],
        "gene_id": claim["gene_id"],
        "worker_id": claim["worker_id"],
        "gpu_id": claim["gpu_id"],
        "gpu_uuid": claim.get("gpu_uuid"),
        "cpu_affinity": claim.get("cpu_affinity"),
        "lease_epoch": claim["lease_epoch"],
        "source_commit": inputs["source_commit"],
        "binary": str(inputs["binary"]),
        "binary_sha256": inputs["binary_sha256"],
        "target": str(inputs["target"]),
        "target_length_bp": inputs["target_length"],
        "target_sha256": inputs["target_sha256"],
        "query": str(inputs["query"]),
        "query_length_nt": len(inputs["sequence"]),
        "query_file_sha256": claim["row"]["query_file_sha256"],
        "query_sequence_sha256": claim["row"]["query_sequence_sha256"],
        "environment": FASIM_ENVIRONMENT,
        "execution_mode": EXECUTION_MODE,
        "output_mode": "full_tfosorted",
    }
    summary = {
        "schema_version": "long_query_dynamic_f1_attempt_summary_v1",
        "status": "complete",
        "pool_id": claim["pool_id"],
        "job_id": claim["job_id"],
        "gene_id": claim["gene_id"],
        "worker_id": claim["worker_id"],
        "lease_epoch": claim["lease_epoch"],
        "wall_seconds": wall_seconds,
        "max_rss_kb": max_rss_kb,
        "artifact_path": artifact_relative,
        "artifact_rows": artifact_rows,
        "artifact_size_bytes": artifact_size,
        "artifact_sha256": artifact_sha256,
        "started_utc": started_utc,
        "completed_utc": completed_utc,
    }
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "complete",
        "pool_id": claim["pool_id"],
        "job_id": claim["job_id"],
        "gene_id": claim["gene_id"],
        "worker_id": claim["worker_id"],
        "lease_epoch": claim["lease_epoch"],
        "query_file_sha256": claim["row"]["query_file_sha256"],
        "query_sequence_sha256": claim["row"]["query_sequence_sha256"],
        "artifact_path": artifact_relative,
        "artifact_size_bytes": artifact_size,
        "artifact_sha256": artifact_sha256,
        "wall_seconds": wall_seconds,
        "started_utc": started_utc,
        "completed_utc": completed_utc,
    }
    receipt.update(claim["receipt_contract"])
    atomic_json(work / "run-plan.json", run_plan)
    atomic_json(work / "summary.json", summary)
    atomic_json(work / "attempt-receipt.json", receipt)
    fsync_directory(work)
    os.replace(work, attempt_dir / "publish")
    fsync_directory(attempt_dir)


def run_attempt(claim_path: Path, attempt_dir: Path) -> int:
    claim = validate_claim(claim_path, attempt_dir)
    require(not (attempt_dir / "publish").exists(), "attempt publication already exists")
    inputs = validate_inputs(claim)
    verify_gpu_uuid(claim)
    work = attempt_dir / "work"
    archive_interrupted_work(attempt_dir, work)
    work.mkdir()
    runtime_output = work / "runtime_output"
    runtime_output.mkdir()
    runtime_query = work / "query.fa"
    write_runtime_query(runtime_query, claim["gene_id"], inputs["sequence"])

    f1_report = work / "f1.tsv"
    command = [
        "taskset",
        "-c",
        str(claim.get("cpu_affinity") or ""),
        str(inputs["binary"]),
        "-f1",
        str(inputs["target"]),
        "-f2",
        str(runtime_query),
        "-r",
        "0",
        "-na",
        os.environ.get("LONGTARGET_F1_NA", "512"),
        "-O",
        str(runtime_output),
    ]
    require(bool(claim.get("cpu_affinity")), "claim is missing CPU affinity")
    environment = os.environ.copy()
    environment.update(FASIM_ENVIRONMENT)
    environment["CUDA_VISIBLE_DEVICES"] = str(claim["gpu_id"])
    environment["FASIM_LONG_QUERY_GPU_CONSUMER_F1_REPORT"] = str(f1_report)
    started_utc = utc_now()
    started = time.monotonic()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    with (work / "stdout.log").open("wb") as stdout, (work / "stderr.log").open("wb") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, env=environment, check=False)
    wall_seconds = time.monotonic() - started
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    completed_utc = utc_now()
    atomic_json(
        work / "process.json",
        {
            "schema_version": "long_query_dynamic_f1_process_v1",
            "command": command,
            "exit_code": completed.returncode,
            "started_utc": started_utc,
            "completed_utc": completed_utc,
            "wall_seconds": wall_seconds,
            "max_rss_kb": max(usage_before, usage_after),
        },
    )
    require(completed.returncode == 0, f"F1 binary exited with status {completed.returncode}")
    publish_attempt(
        claim,
        inputs,
        attempt_dir,
        work,
        started_utc,
        completed_utc,
        wall_seconds,
        max(usage_before, usage_after),
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run_attempt(args.claim, args.attempt_dir)
    except (AttemptError, OSError, ValueError, KeyError) as error:
        failure = {
            "schema_version": "long_query_dynamic_f1_attempt_failure_v1",
            "status": "failed",
            "error": str(error),
            "failed_utc": utc_now(),
        }
        try:
            atomic_json(args.attempt_dir / "failure.json", failure)
        except OSError:
            pass
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
