#!/usr/bin/env python3
"""Freeze canonical-hybrid-v2 runtime identity and Phase 2 regression plan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_canonical_hybrid_v2.py"
RUNTIME_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_runtime.json"
REGRESSION_PLAN_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_plan.tsv"
REGRESSION_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_plan_receipt.json"
HOLDOUT_MANIFEST_PATH = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
HOLDOUT_RESULTS_PATH = ROOT / "paper/bioinformatics/holdout_attempt_results.tsv"
OLD_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
IMPLEMENTATION_SOURCES = (
    ROOT / "fasim/Fasim-LongTarget.cpp",
    ROOT / "fasim/gasal2_align_bridge.cpp",
    ROOT / "fasim/gasal2_align_bridge.h",
    ROOT / "fasim/gasal2_align_bridge_stub.cpp",
    RUNNER_PATH,
    ROOT / "scripts/canonical_hybrid_v2_telemetry.py",
    ROOT / "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json",
    ROOT / "paper/bioinformatics/canonical_hybrid_v2_protocol.md",
)
PREALIGN_CUDA_FLAGS = (
    "-O3 -std=c++11 "
    "--generate-code=arch=compute_89,code=sm_89 "
    "--generate-code=arch=compute_80,code=compute_80"
)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_bytes(path: Path, payload: bytes) -> None:
    require(not path.exists(), f"refusing to replace frozen artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: list[dict[str, str]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="raise"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def command_output(command: Sequence[str], timeout: int = 30) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    require(completed.returncode == 0, completed.stderr.strip() or f"command failed: {' '.join(command)}")
    return completed.stdout.strip()


def git_output(*arguments: str) -> str:
    return command_output(("git", "-C", str(ROOT), *arguments))


def require_clean_checkout() -> str:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all", "--ignored=no")
    require(not status, f"freeze requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def load_runner():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_freeze_runner", RUNNER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical hybrid runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def safe_version(command: Sequence[str]) -> str:
    try:
        return command_output(command)
    except (FreezeError, OSError, subprocess.TimeoutExpired):
        return "unavailable"


def gpu_inventory() -> list[dict[str, str]]:
    output = safe_version(
        (
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,compute_cap,driver_version",
            "--format=csv,noheader,nounits",
        )
    )
    if output == "unavailable":
        return []
    fields = ("index", "name", "uuid", "memory_total_mib", "compute_capability", "driver_version")
    return [dict(zip(fields, (part.strip() for part in line.split(",")))) for line in output.splitlines()]


def freeze_runtime(args: argparse.Namespace) -> dict[str, object]:
    commit = require_clean_checkout()
    hybrid = args.hybrid_binary.resolve()
    authority = args.authority_binary.resolve()
    for label, binary in (("hybrid", hybrid), ("authority", authority)):
        require(binary.is_file() and not binary.is_symlink(), f"missing or unsafe {label} binary")
        require(os.access(binary, os.X_OK), f"{label} binary is not executable")
        require(ROOT in binary.parents, f"{label} binary must be inside the repository")
    code_objects = safe_version(
        ("/usr/local/cuda/bin/cuobjdump", "--list-elf", str(ROOT / "cuda/prealign_cuda.o"))
    ).splitlines()
    require(any("sm_89" in line for line in code_objects), "prealign object lacks frozen sm_89 code")
    devices = gpu_inventory()
    require({device["index"] for device in devices} >= {"0", "1"}, "runtime freeze requires GPUs 0 and 1")
    source_files = {
        path.relative_to(ROOT).as_posix(): sha256_file(path) for path in IMPLEMENTATION_SOURCES
    }
    receipt = {
        "schema_version": 1,
        "runtime_epoch": 1,
        "contract": "canonical-hybrid-v2",
        "runtime_commit": commit,
        "runner_commit": commit,
        "complete_cpu_authority_inside_hybrid": False,
        "hybrid_binary_path": hybrid.relative_to(ROOT).as_posix(),
        "hybrid_binary_sha256": sha256_file(hybrid),
        "authority_binary_path": authority.relative_to(ROOT).as_posix(),
        "authority_binary_sha256": sha256_file(authority),
        "hybrid_build_commands": [
            [
                "make",
                "-B",
                "cuda/prealign_cuda.o",
                f"CUDA_CXXFLAGS={PREALIGN_CUDA_FLAGS}",
            ],
            [
                "make",
                "build-fasim-gasal2",
                f"FASIM_GASAL2_TARGET={hybrid.relative_to(ROOT).as_posix()}",
                "GASAL2_GPU_SM_ARCH=sm_89",
                "GASAL2_MAX_QUERY_LEN=2812",
                "GASAL2_N_CODE=0x4E",
            ],
        ],
        "authority_build_commands": [
            [
                "make",
                "build-fasim",
                f"FASIM_TARGET={authority.relative_to(ROOT).as_posix()}",
            ],
        ],
        "runner_sha256": sha256_file(RUNNER_PATH),
        "telemetry_validator_sha256": sha256_file(ROOT / "scripts/canonical_hybrid_v2_telemetry.py"),
        "telemetry_schema_sha256": sha256_file(
            ROOT / "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json"
        ),
        "comparator_sha256": sha256_file(ROOT / "scripts/compare_fasim_segmented_contract.py"),
        "implementation_source_sha256": source_files,
        "implementation_commit_patch_sha256": hashlib.sha256(
            subprocess.run(
                ["git", "-C", str(ROOT), "show", "--format=", "--binary", commit],
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
        ).hexdigest(),
        "compiler": safe_version(("g++", "--version")).splitlines()[0],
        "cuda_compiler": safe_version(("/usr/local/cuda/bin/nvcc", "--version")).splitlines()[-1],
        "gasal2_revision": safe_version(("git", "-C", str(ROOT / ".tmp/GASAL2"), "rev-parse", "HEAD")),
        "linked_dependency_sha256": {
            "cuda/prealign_cuda.o": sha256_file(ROOT / "cuda/prealign_cuda.o"),
            ".tmp/GASAL2/lib/libgasal.a": sha256_file(ROOT / ".tmp/GASAL2/lib/libgasal.a"),
        },
        "prealign_cuda_code_objects": code_objects,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "gpu_inventory": devices,
        "runtime_environment": {
            "FASIM_OUTPUT_MODE": "tfosorted",
            "FASIM_VERBOSE": "0",
            "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
            "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
            "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
            "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
            "FASIM_ALIGN_GASAL2_STREAMS": "3",
            "FASIM_ALIGN_GASAL2_BATCH": "20000",
            "FASIM_ALIGN_GASAL2_CPU_TRACEBACK": "1",
            "FASIM_CANONICAL_HYBRID_V2": "1",
        },
        "historical_decision_sha256": {
            "phase2_decision.md": sha256_file(ROOT / "paper/bioinformatics/phase2_decision.md"),
            "phase3_postpilot_decision.json": sha256_file(
                ROOT / "paper/bioinformatics/phase3_postpilot_decision.json"
            ),
        },
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_bytes(RUNTIME_PATH, json_bytes(receipt))
    return receipt


def authority_output(attempt_id: str) -> Path:
    output_root = OLD_ARTIFACT_ROOT / "formal" / attempt_id / "authority/output"
    outputs = sorted(path for path in output_root.glob("*TFOsorted") if path.is_file())
    require(len(outputs) == 1, f"expected one frozen authority output for {attempt_id}")
    require(not outputs[0].is_symlink(), f"unsafe frozen authority output for {attempt_id}")
    return outputs[0]


def freeze_regression_plan(_: argparse.Namespace) -> dict[str, object]:
    freeze_commit = require_clean_checkout()
    runner = load_runner()
    runtime = runner.read_runtime_receipt()
    results = read_tsv(HOLDOUT_RESULTS_PATH)
    manifest = {row["workload_id"]: row for row in read_tsv(HOLDOUT_MANIFEST_PATH)}
    require(len(results) == 36, "Phase 2 primary attempt count drift")
    require(len({row["attempt_id"] for row in results}) == 36, "duplicate Phase 2 attempt ID")
    require(all(row["outcome"] in ("complete", "scientific_mismatch") for row in results), "incomplete Phase 2 attempt")
    runtime_sha256 = sha256_file(RUNTIME_PATH)
    rows: list[dict[str, str]] = []
    for order, result in enumerate(results, 1):
        workload = manifest[result["workload_id"]]
        old_receipt = OLD_ARTIFACT_ROOT / result["receipt_path"]
        require(old_receipt.is_file() and not old_receipt.is_symlink(), "missing Phase 2 attempt receipt")
        require(sha256_file(old_receipt) == result["receipt_sha256"], "Phase 2 attempt receipt digest drift")
        authority = authority_output(result["attempt_id"])
        attempt_id = f"v2reg_{result['attempt_id']}"
        rows.append(
            {
                "attempt_id": attempt_id,
                "stage": "regression",
                "validation_id": result["attempt_id"],
                "arm": "H",
                "order": str(order),
                "repeat_id": result["repeat_index"],
                "query_id": result["query_id"],
                "target_id": result["target_id"],
                "query_path": workload["query_path"],
                "target_path": workload["target_path"],
                "query_sha256": sha256_file(ROOT / workload["query_path"]),
                "target_sha256": sha256_file(ROOT / workload["target_path"]),
                "authority_reference_kind": "frozen_file",
                "authority_reference": authority.relative_to(ROOT).as_posix(),
                "authority_reference_sha256": sha256_file(authority),
                "runtime_commit": str(runtime["runtime_commit"]),
                "hybrid_binary_sha256": str(runtime["hybrid_binary_sha256"]),
                "authority_binary_sha256": str(runtime["authority_binary_sha256"]),
                "runner_commit": str(runtime["runner_commit"]),
                "runner_sha256": str(runtime["runner_sha256"]),
                "runtime_receipt_sha256": runtime_sha256,
                "backend_timeout_seconds": "3600",
                "gpu_physical_index": str((order - 1) % 2),
                "contract": "all-ranked-top5-canonical-row-v2",
                "claim_role": "regression_only",
                "promotion_eligible": "0",
                "formal_source_data": "0",
                "retry_policy": "none",
                "expected_artifact_root": f"regression/{attempt_id}",
                "status": "preregistered_not_run",
            }
        )
    payload = tsv_bytes(runner.PLAN_FIELDS, rows)
    atomic_bytes(REGRESSION_PLAN_PATH, payload)
    plan_sha256 = sha256_file(REGRESSION_PLAN_PATH)
    atomic_bytes(
        REGRESSION_PLAN_PATH.with_suffix(".sha256"),
        f"{plan_sha256}  {REGRESSION_PLAN_PATH.name}\n".encode("ascii"),
    )
    receipt = {
        "schema_version": 1,
        "stage": "regression",
        "freeze_commit": freeze_commit,
        "runtime_commit": runtime["runtime_commit"],
        "runtime_receipt_sha256": runtime_sha256,
        "plan_sha256": plan_sha256,
        "attempt_count": len(rows),
        "arm_counts": {"A": 0, "H": len(rows)},
        "gpu_assignment": "zero_based_order_modulo_2",
        "phase2_holdout_manifest_sha256": sha256_file(HOLDOUT_MANIFEST_PATH),
        "phase2_attempt_results_sha256": sha256_file(HOLDOUT_RESULTS_PATH),
        "promotion_eligible": False,
        "claim_role": "regression_only",
        "retry_policy": "none",
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_bytes(REGRESSION_RECEIPT_PATH, json_bytes(receipt))
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    runtime = subparsers.add_parser("runtime")
    runtime.add_argument("--hybrid-binary", type=Path, required=True)
    runtime.add_argument("--authority-binary", type=Path, required=True)
    subparsers.add_parser("regression-plan")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        result = freeze_runtime(args) if args.command == "runtime" else freeze_regression_plan(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (FreezeError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"canonical-hybrid-v2 freeze failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
