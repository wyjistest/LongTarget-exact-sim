#!/usr/bin/env python3
"""Replay the two Phase 2 traceback mismatches from immutable snapshots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "paper/bioinformatics/phase2_traceback_replay_plan.json"
PLAN_SHA256 = "8dffd1437daad40a6e6551eb110b71ee9cb64d3b4a9b9508f0412924fe5a590d"
EVIDENCE_PATH = ROOT / "paper/bioinformatics/phase2_traceback_replay.tsv"
RECEIPT_PATH = ROOT / "paper/bioinformatics/phase2_traceback_replay_receipt.json"
RUNNER_PATH = Path(__file__).resolve()
METRIC_PREFIX = "benchmark.fasim_gasal2_"
METRICS = (
    "fallbacks",
    "score_selected_attempts",
    "cpu_traceback_replay_attempts",
    "cpu_traceback_selected_attempts",
    "cpu_traceback_align_calls",
    "cpu_traceback_emit_threshold",
    "cpu_traceback_emit_best_fallback",
    "cpu_traceback_emit_last",
)
TABLE_FIELDS = (
    "attempt_id",
    "replay_mode",
    "expected_output_side",
    "output_sha256",
    "expected_output_sha256",
    "byte_equal_to_expected",
    "returncode",
    "timed_out",
    "oom_detected",
    *METRICS,
    "wall_seconds",
    "artifact_path",
)


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    import io

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


def read_plan() -> dict[str, object]:
    require(PLAN_PATH.is_file() and not PLAN_PATH.is_symlink(), "unsafe replay plan")
    require(sha256_file(PLAN_PATH) == PLAN_SHA256, "replay plan SHA-256 drift")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    require(plan.get("schema_version") == 1, "unsupported replay plan schema")
    require(plan.get("promotion_eligible") is False, "diagnostic became promotion evidence")
    require(plan.get("purpose") == "post_hoc_root_cause_diagnostic_only", "purpose drift")
    require(plan["execution"]["retry_policy"] == "none", "retry policy drift")
    require(len(plan.get("cases", [])) == 2, "replay case count drift")
    require(len(plan.get("modes", [])) == 3, "replay mode count drift")
    return plan


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_clean_checkout() -> str:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all", "--ignored=no")
    require(not status, f"replay execution requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def relative_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    require(path == ROOT or ROOT in path.parents, f"path escapes repository: {value}")
    return path


def validate_source_case(
    plan: dict[str, object], case: dict[str, object]
) -> dict[str, Path]:
    source_root = relative_path(plan["execution"]["source_artifact_root"])
    attempt_root = source_root / "formal" / str(case["attempt_id"])
    require(attempt_root.is_dir() and not attempt_root.is_symlink(), "missing source attempt")
    snapshot = attempt_root / "execution-snapshot"
    paths = {
        "attempt_root": attempt_root,
        "binary": snapshot / "binaries/fasim_longtarget_gasal2",
        "query": snapshot / "inputs/query.fa",
        "target": snapshot / "inputs/target.fa",
        "config": attempt_root / "attempt-config.json",
        "snapshot_manifest": snapshot / "snapshot-manifest.json",
        "authority": attempt_root / "authority/output" / str(case["expected_tfosorted_name"]),
        "candidate": attempt_root / "candidate/output" / str(case["expected_tfosorted_name"]),
    }
    for label, path in paths.items():
        require(path.exists() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    config = json.loads(paths["config"].read_text(encoding="utf-8"))
    source_freeze = plan["source_freeze"]
    require(config["git_head"] == source_freeze["snapshot_commit"], "snapshot commit drift")
    require(config["freeze_id"] == source_freeze["holdout_freeze_id"], "freeze ID drift")
    require(config["manifest_sha256"] == source_freeze["holdout_manifest_sha256"], "manifest drift")
    require(config["execution_identity_sha256"] == case["execution_identity_sha256"], "identity drift")
    expected_digests = {
        "binary": source_freeze["candidate_binary_sha256"],
        "query": case["query_sha256"],
        "target": case["target_sha256"],
        "authority": case["authority_output_sha256"],
        "candidate": case["candidate_output_sha256"],
    }
    for label, expected in expected_digests.items():
        require(sha256_file(paths[label]) == expected, f"{label} digest drift for {case['attempt_id']}")
    require(os.access(paths["binary"], os.X_OK), "snapshot candidate binary is not executable")
    return paths


def query_devices() -> list[dict[str, object]]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,uuid,pci.bus_id,driver_version,compute_cap,memory.total",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(command, check=False, text=True, capture_output=True, timeout=30)
    require(completed.returncode == 0, f"nvidia-smi failed: {completed.stderr.strip()}")
    devices = []
    for raw in completed.stdout.splitlines():
        parts = [part.strip() for part in raw.split(",")]
        require(len(parts) == 7, f"unexpected nvidia-smi row: {raw}")
        devices.append(
            {
                "physical_index": int(parts[0]),
                "name": parts[1],
                "uuid": parts[2],
                "pci_bus_id": parts[3],
                "driver_version": parts[4],
                "compute_capability": parts[5],
                "memory_total_mib": int(parts[6]),
            }
        )
    return devices


def validate_replay_device(plan: dict[str, object], devices: list[dict[str, object]]) -> dict[str, object]:
    expected = plan["replay_device"]
    matching = [row for row in devices if row["physical_index"] == expected["physical_index"]]
    require(len(matching) == 1, "fixed replay GPU index is unavailable")
    observed = matching[0]
    for field in ("name", "uuid", "driver_version", "compute_capability", "memory_total_mib"):
        require(observed[field] == expected[field], f"replay GPU {field} drift")
    return observed


def replay_environment(
    plan: dict[str, object], mode: dict[str, object]
) -> tuple[dict[str, str], dict[str, str]]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FASIM_")}
    explicit = {str(key): str(value) for key, value in plan["candidate_environment"].items()}
    for key in mode["unset_environment"]:
        explicit.pop(str(key), None)
    explicit.update({str(key): str(value) for key, value in mode["set_environment"].items()})
    explicit["CUDA_VISIBLE_DEVICES"] = str(plan["replay_device"]["physical_index"])
    environment.update(explicit)
    return environment, explicit


def parse_metrics(stderr: str) -> dict[str, int]:
    parsed: dict[str, int] = {}
    pattern = re.compile(r"^" + re.escape(METRIC_PREFIX) + r"([a-z0-9_]+)=(-?[0-9]+)$")
    for line in stderr.splitlines():
        match = pattern.match(line)
        if match and match.group(1) in METRICS:
            name = match.group(1)
            require(name not in parsed, f"duplicate telemetry metric: {name}")
            parsed[name] = int(match.group(2))
    missing = sorted(set(METRICS) - set(parsed))
    require(not missing, f"missing telemetry metrics: {', '.join(missing)}")
    return parsed


def oom_detected(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(token in lowered for token in ("out of memory", "std::bad_alloc", "cuda_error_memory_allocation"))


def execute_run(
    plan: dict[str, object],
    case: dict[str, object],
    mode: dict[str, object],
    paths: dict[str, Path],
    staging_root: Path,
) -> dict[str, object]:
    relative_run = Path(str(case["attempt_id"])) / str(mode["mode_id"])
    run_root = staging_root / relative_run
    output_root = run_root / "output"
    output_root.mkdir(parents=True, exist_ok=False)
    command = [
        str(paths["binary"]),
        "-f1",
        str(paths["target"]),
        "-f2",
        str(paths["query"]),
        "-r",
        "0",
        "-O",
        str(output_root),
    ]
    environment, explicit_environment = replay_environment(plan, mode)
    started_utc = utc_now()
    started = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(plan["execution"]["backend_timeout_seconds"]),
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    wall_seconds = time.perf_counter() - started
    atomic_write(run_root / "stdout.log", stdout.encode("utf-8"))
    atomic_write(run_root / "stderr.log", stderr.encode("utf-8"))
    require(not timed_out, f"replay timed out: {case['attempt_id']} {mode['mode_id']}")
    require(returncode == 0, f"replay failed: {case['attempt_id']} {mode['mode_id']}")
    require(not oom_detected(stderr), f"OOM detected: {case['attempt_id']} {mode['mode_id']}")
    metrics = parse_metrics(stderr)
    expected_metrics = case["expected_metrics"][mode["mode_id"]]
    require(metrics == expected_metrics, f"telemetry drift: {case['attempt_id']} {mode['mode_id']}")
    output = output_root / str(case["expected_tfosorted_name"])
    files = [path for path in output_root.iterdir() if path.is_file()]
    require(files == [output], f"unexpected replay outputs: {case['attempt_id']} {mode['mode_id']}")
    expected_side = str(mode["expected_output"])
    expected_path = paths[expected_side]
    observed_sha256 = sha256_file(output)
    expected_sha256 = str(case[f"{expected_side}_output_sha256"])
    require(observed_sha256 == expected_sha256, f"output digest mismatch: {case['attempt_id']} {mode['mode_id']}")
    require(output.read_bytes() == expected_path.read_bytes(), "output is not byte-equal to frozen source")
    result = {
        "attempt_id": case["attempt_id"],
        "replay_mode": mode["mode_id"],
        "expected_output_side": expected_side,
        "output_sha256": observed_sha256,
        "expected_output_sha256": expected_sha256,
        "byte_equal_to_expected": True,
        "returncode": returncode,
        "timed_out": timed_out,
        "oom_detected": False,
        **metrics,
        "wall_seconds": round(wall_seconds, 9),
        "artifact_path": str(relative_run / "output" / output.name),
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "command": command,
        "explicit_environment": explicit_environment,
        "stdout_sha256": sha256_file(run_root / "stdout.log"),
        "stderr_sha256": sha256_file(run_root / "stderr.log"),
    }
    atomic_write(run_root / "run.json", canonical_json_bytes(result))
    return result


def artifact_manifest(root: Path) -> tuple[bytes, int]:
    rows = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "artifact-manifest.tsv":
            continue
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return tsv_bytes(("path", "size_bytes", "sha256"), rows), len(rows)


def execute(plan: dict[str, object]) -> dict[str, object]:
    head = require_clean_checkout()
    canonical_root = relative_path(plan["execution"]["artifact_root"])
    require(not canonical_root.exists(), f"replay artifact root already exists: {canonical_root}")
    partials = list(canonical_root.parent.glob(f".{canonical_root.name}.partial.*"))
    require(not partials, "stale replay partial requires manual adjudication")
    canonical_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = canonical_root.parent / f".{canonical_root.name}.partial.{os.getpid()}"
    staging_root.mkdir(mode=0o755)
    devices = query_devices()
    replay_device = validate_replay_device(plan, devices)
    started_utc = utc_now()
    results = []
    source = {}
    for case in plan["cases"]:
        paths = validate_source_case(plan, case)
        source[str(case["attempt_id"])] = {
            "candidate_binary_sha256": sha256_file(paths["binary"]),
            "query_sha256": sha256_file(paths["query"]),
            "target_sha256": sha256_file(paths["target"]),
            "authority_output_sha256": sha256_file(paths["authority"]),
            "candidate_output_sha256": sha256_file(paths["candidate"]),
        }
        for mode in plan["modes"]:
            results.append(execute_run(plan, case, mode, paths, staging_root))
    summary = {
        "schema_version": 1,
        "freeze_id": plan["freeze_id"],
        "plan_sha256": PLAN_SHA256,
        "runner_sha256": sha256_file(RUNNER_PATH),
        "runner_commit": head,
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "visible_devices_before_binding": devices,
        "replay_device": replay_device,
        "formal_candidate_device_binding": plan["formal_candidate_device_binding"],
        "source": source,
        "runs": results,
        "run_count": len(results),
        "technical_failures": 0,
        "fallbacks": sum(int(row["fallbacks"]) for row in results),
        "timeouts": sum(bool(row["timed_out"]) for row in results),
        "ooms": sum(bool(row["oom_detected"]) for row in results),
        "all_outputs_byte_equal": all(bool(row["byte_equal_to_expected"]) for row in results),
        "promotion_eligible": False,
    }
    atomic_write(staging_root / "replay-summary.json", canonical_json_bytes(summary))
    manifest_payload, artifact_count = artifact_manifest(staging_root)
    atomic_write(staging_root / "artifact-manifest.tsv", manifest_payload)
    manifest_sha256 = sha256_file(staging_root / "artifact-manifest.tsv")
    os.replace(staging_root, canonical_root)
    receipt = {
        **summary,
        "artifact_root": plan["execution"]["artifact_root"],
        "artifact_manifest_path": str(Path(plan["execution"]["artifact_root"]) / "artifact-manifest.tsv"),
        "artifact_manifest_sha256": manifest_sha256,
        "artifact_count": artifact_count,
        "root_cause_classification": (
            "reproducible_GASAL2_GPU_endpoint_CIGAR_traceback_divergence_"
            "consistent_with_alternative_reported_equal_score_alignment_path"
        ),
        "dp_tie_cell_localized": False,
        "cross_gpu_architecture_generalized": False,
        "mismatch_rate_estimate_supported": False,
        "historical_phase2_decision": "verified_only_contract",
        "historical_phase3_v1_decision": "no_go",
    }
    table_rows = [{field: row[field] for field in TABLE_FIELDS} for row in results]
    atomic_write(EVIDENCE_PATH, tsv_bytes(TABLE_FIELDS, table_rows))
    atomic_write(RECEIPT_PATH, canonical_json_bytes(receipt))
    return receipt


def plan_summary(plan: dict[str, object]) -> dict[str, object]:
    return {
        "freeze_id": plan["freeze_id"],
        "plan_sha256": PLAN_SHA256,
        "case_count": len(plan["cases"]),
        "mode_count": len(plan["modes"]),
        "run_count": len(plan["cases"]) * len(plan["modes"]),
        "promotion_eligible": plan["promotion_eligible"],
        "retry_policy": plan["execution"]["retry_policy"],
        "artifact_root": plan["execution"]["artifact_root"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        plan = read_plan()
        result = execute(plan) if args.execute else plan_summary(plan)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ReplayError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"phase2 traceback replay failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
