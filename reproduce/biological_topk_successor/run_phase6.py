#!/usr/bin/env python3
"""Preflight or execute the frozen successor Phase 6 A/G/X attempts."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import freeze_phase5 as frozen
except ImportError:  # pragma: no cover
    import freeze_phase5 as frozen  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
STATE = PAPER / "PROGRAM_STATE.json"
ATTEMPT_PLAN = PAPER / "experimental_attempt_plan.tsv"
BENCHMARK_PLAN = PAPER / "experimental_benchmark_plan.json"
MANIFEST = PAPER / "experimental_benchmark_manifest.tsv"
RUNTIME_RECEIPT = PAPER / "experimental_runtime_input_receipt.json"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase6"
PHASE5_COMMIT_MESSAGE = "repro: preregister independent biological utility benchmark"
FIXED_TOTAL_ARTIFACT_STORAGE_BYTES = 64 * 1024**3
TRACKED_EVIDENCE_RESERVATION_BYTES = 256 * 1024**2
MAX_GPU_SECONDS = 96 * 3600
MAX_CPU_WALL_SECONDS = 96 * 3600
FASIM_ENVIRONMENT_A = {"FASIM_OUTPUT_MODE": "tfosorted", "FASIM_VERBOSE": "0"}
FASIM_ENVIRONMENT_G = {
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
}


class RunnerError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    ).hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
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


def atomic_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json_bytes(value))


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def directory_file_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    require(path.is_dir() and not path.is_symlink(), f"unsafe artifact root: {path}")
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def formal_artifact_bytes() -> int:
    return sum(
        directory_file_bytes(path)
        for path in (
            ROOT / ".paper-artifacts/biological-topk",
            ROOT / ".paper-artifacts/biological-topk-successor",
        )
    )


def read_attempts() -> list[dict[str, str]]:
    require(ATTEMPT_PLAN.is_file() and not ATTEMPT_PLAN.is_symlink(), "attempt plan missing")
    with ATTEMPT_PLAN.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == frozen.ATTEMPT_FIELDS, "attempt plan schema drift")
        rows = list(reader)
    require(len(rows) == 15 and all(None not in row for row in rows), "attempt plan row count/malformed drift")
    return rows


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(ROOT), *arguments),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or f"git command failed: {arguments}")
    return completed.stdout.strip()


def bubblewrap_prefix(work_root: Path) -> list[str]:
    return [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--new-session",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/sbin",
        "/sbin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--ro-bind",
        "/etc",
        "/etc",
        "--dev-bind",
        "/dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(work_root),
        "/work",
        "--chdir",
        "/work",
    ]


def isolation_preflight() -> None:
    require(shutil.which("bwrap") == "/usr/bin/bwrap", "frozen bubblewrap executable unavailable")
    with tempfile.TemporaryDirectory(prefix="bt6-isolation-") as name:
        command = bubblewrap_prefix(Path(name)) + [
            "/usr/bin/test",
            "!",
            "-e",
            "/data/wenyujianData/LongTarget-exact-sim/paper/biological_topk_successor/experimental_benchmark_manifest.tsv",
        ]
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace") or "bubblewrap label isolation failed")


def validate_frozen_plan() -> tuple[list[dict[str, str]], dict[str, Any]]:
    attempts = read_attempts()
    plan = read_json(BENCHMARK_PLAN)
    receipt = read_json(RUNTIME_RECEIPT)
    require(plan["bindings"]["experimental_benchmark_manifest_sha256"] == sha256_file(MANIFEST), "manifest digest drift")
    require(plan["bindings"]["experimental_attempt_plan_sha256"] == sha256_file(ATTEMPT_PLAN), "attempt plan digest drift")
    require(plan["evaluation_prediction_started"] is False and plan["phase_6_authorized"] is True, "Phase 6 not authorized by frozen plan")
    require(
        plan["execution"]["max_gpu_hours"] == 96
        and plan["execution"]["max_cpu_wall_hours"] == 96
        and plan["execution"]["max_total_artifact_storage_bytes"] == FIXED_TOTAL_ARTIFACT_STORAGE_BYTES
        and plan["execution"]["tracked_evidence_reservation_bytes"] == TRACKED_EVIDENCE_RESERVATION_BYTES,
        "Phase 6 fixed execution limits drift",
    )
    require(receipt["target_region_count"] == 5000 and receipt["fasta_headers_label_blind"] is True, "runtime input receipt drift")
    registered = {row["path"]: row for row in receipt["files"]}
    for row in attempts:
        require(row["labels_visible_to_backend"] == "0", f"backend label visibility drift: {row['attempt_id']}")
        require(row["retry_policy"] == "none" and row["comparison_policy"] == "offline_after_all_15_attempts_terminal", "attempt policy drift")
        require(sha256_file(ROOT / row["query_fasta_path"]) == row["query_fasta_sha256"], "attempt query FASTA drift")
        require(sha256_file(ROOT / row["target_fasta_path"]) == row["target_fasta_sha256"], "attempt target FASTA drift")
        require(sha256_file(ROOT / row["binary_path"]) == row["binary_sha256"], "attempt binary drift")
        require(sha256_file(ROOT / row["runner_path"]) == row["runner_sha256"], "attempt runner drift")
        require(sha256_file(ROOT / row["analyzer_path"]) == row["analyzer_sha256"], "attempt analyzer drift")
        for field in ("query_fasta_path", "target_fasta_path"):
            identity = registered[row[field]]
            require(identity["contains_labels"] is False and identity["sha256"] == sha256_file(ROOT / row[field]), "runtime input identity drift")
    require(len({row["attempt_id"] for row in attempts}) == 15 and sorted(int(row["execution_index"]) for row in attempts) == list(range(1, 16)), "attempt identity/order drift")
    require(
        formal_artifact_bytes() + TRACKED_EVIDENCE_RESERVATION_BYTES <= FIXED_TOTAL_ARTIFACT_STORAGE_BYTES,
        "fixed artifact budget is exhausted before Phase 6",
    )
    isolation_preflight()
    return attempts, plan


def execution_source_commit() -> str:
    head = git("rev-parse", "HEAD")
    require(git("log", "-1", "--format=%s", head) == PHASE5_COMMIT_MESSAGE, "formal Phase 6 execution requires Phase 5 freeze commit at HEAD")
    committed = json.loads(git("show", f"{head}:paper/biological_topk_successor/PROGRAM_STATE.json"))
    require(committed["phase_status"]["5"] == "pass" and committed["active_phase"] == 6, "committed Phase 5 state did not authorize Phase 6")
    live = read_json(STATE)
    require(live["phase_status"]["6"] == "active", "formal Phase 6 execution requires live Phase 6 active state")
    changed_lines = git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    changed_paths = {line[3:] for line in changed_lines if len(line) >= 4}
    allowlist_path = PAPER / "phase_6_change_allowlist.txt"
    require(allowlist_path.is_file(), "missing Phase 6 execution allowlist")
    allowed = {line.strip() for line in allowlist_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    require(changed_paths <= allowed, f"Phase 6 checkout has out-of-scope changes: {sorted(changed_paths - allowed)}")
    for path in (Path(__file__).resolve(), ATTEMPT_PLAN, BENCHMARK_PLAN, MANIFEST):
        relative = path.relative_to(ROOT).as_posix()
        require(not git("diff", "--name-only", head, "--", relative), f"frozen Phase 6 input changed after Phase 5: {relative}")
    return head


def visible_gpu_inventory() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ("nvidia-smi", "--query-gpu=index,name,uuid,memory.total,compute_cap", "--format=csv,noheader,nounits"),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or "GPU inventory unavailable")
    rows = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        require(len(fields) == 5, "GPU inventory schema drift")
        rows.append({"index": int(fields[0]), "name": fields[1], "uuid": fields[2], "memory_total_mib": int(fields[3]), "compute_capability": fields[4]})
    require(len(rows) >= 2 and all(row["name"] == "NVIDIA GeForce RTX 4090" for row in rows[:2]), "frozen Phase 6 GPU envelope unavailable")
    return rows[:2]


def _limit_address_space() -> None:
    limit = 96 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run_process(command: Sequence[str], environment: Mapping[str, str], root: Path, timeout_seconds: int) -> dict[str, Any]:
    time_path = root / "time.txt"
    measured = ["/usr/bin/time", "-v", "-o", str(time_path), *command]
    started_utc = utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        measured,
        cwd=ROOT,
        env=dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        preexec_fn=_limit_address_space,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    wall = time.perf_counter() - started
    atomic_write(root / "stdout.txt", stdout)
    atomic_write(root / "stderr.txt", stderr)
    return {
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "wall_seconds": format(wall, ".9f"),
        "timeout_seconds_applied": timeout_seconds,
        "returncode": process.returncode,
        "timed_out": timed_out,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "time_sha256": sha256_file(time_path),
    }


def gzip_deterministic(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    destination = path.with_suffix(path.suffix + ".gz")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=output, mtime=0) as handle:
                handle.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    path.unlink()
    return {
        "path": destination.name,
        "compression": "gzip_level_9_mtime_0_no_filename",
        "uncompressed_size_bytes": len(payload),
        "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
        "compressed_size_bytes": destination.stat().st_size,
        "compressed_sha256": sha256_file(destination),
        "lossless": gzip.decompress(destination.read_bytes()) == payload,
        "validated_before_compression": True,
    }


def artifact_manifest(root: Path) -> bytes:
    fields = ("path", "size_bytes", "sha256")
    rows = []
    excluded = {"artifact-manifest.tsv", "artifact-manifest.sha256", "attempt-complete.json"}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.relative_to(root).as_posix() not in excluded:
            rows.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def fasim_output(output_root: Path) -> Path:
    files = sorted(path for path in output_root.iterdir() if path.is_file() and path.name.endswith("TFOsorted"))
    require(len(files) == 1, f"expected one Fasim TFOsorted output, observed {len(files)}")
    with files[0].open(encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
    require({"StartInSeq", "EndInSeq", "Score", "Nt(bp)"} <= set(header), "Fasim output schema drift")
    return files[0]


def command_for(row: Mapping[str, str]) -> tuple[list[str], dict[str, str]]:
    base_environment = {
        "HOME": "/tmp",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "OMP_NUM_THREADS": "10",
    }
    prefix = bubblewrap_prefix(Path(row["_partial_root"]))
    if row["arm"] in {"A", "G"}:
        inner = [
            "/usr/bin/taskset",
            "-c",
            row["cpu_affinity"],
            "/work/backend",
            "-f1",
            "/work/inputs/target.fa",
            "-f2",
            "/work/inputs/query.fa",
            "-r",
            "0",
            "-O",
            "/work/output",
        ]
        explicit = dict(FASIM_ENVIRONMENT_A if row["arm"] == "A" else FASIM_ENVIRONMENT_G)
        explicit["CUDA_VISIBLE_DEVICES"] = "" if row["arm"] == "A" else row["gpu_physical_index"]
        if row["arm"] == "G":
            explicit["FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH"] = "/work/telemetry.json"
    else:
        inner = [
            "/usr/bin/taskset",
            "-c",
            row["cpu_affinity"],
            "/work/backend",
            "-ss",
            "/work/inputs/query.fa",
            "-ds",
            "/work/inputs/target.fa",
            "-l",
            "16",
            "-L",
            "30",
            "-e",
            "5",
            "-of",
            "2",
            "-rm",
            "0",
            "-o",
            "/work/output/triplexator-summary.tsv",
        ]
        explicit = {"CUDA_VISIBLE_DEVICES": ""}
    base_environment.update(explicit)
    return prefix + inner, base_environment


def validate_terminal_receipt(destination: Path, row: Mapping[str, str], source_commit: str) -> dict[str, Any]:
    receipt = read_json(destination / "attempt-complete.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 6, "existing attempt schema/phase drift")
    require(receipt["attempt_id"] == row["attempt_id"], "existing attempt identity drift")
    require(receipt["status"] in {"success", "technical_failure"}, "existing attempt is not terminal")
    require(receipt["source_commit"] == source_commit, "existing attempt source commit drift")
    require(receipt["attempt_config_sha256"] == canonical_digest(dict(row)), "existing attempt config drift")
    require(receipt["query_fasta_sha256"] == row["query_fasta_sha256"], "existing attempt query binding drift")
    require(receipt["target_fasta_sha256"] == row["target_fasta_sha256"], "existing attempt target binding drift")
    require(receipt["binary_sha256"] == row["binary_sha256"], "existing attempt binary binding drift")
    require(receipt["labels_visible_to_backend"] is False and receipt["label_manifest_mounted_in_sandbox"] is False, "existing attempt label isolation drift")
    require(receipt["comparison_started"] is False, "existing attempt performed a comparison")
    if receipt["status"] == "success":
        relative = Path(str(receipt["output_path"]))
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe existing attempt output path")
        output = destination / relative
        require(output.is_file() and not output.is_symlink(), "existing successful attempt output missing")
        require(sha256_file(output) == receipt["output_sha256"], "existing successful attempt output drift")
    return receipt


def completed_wall_seconds(attempts: Sequence[Mapping[str, str]], *, gpu: bool) -> float:
    total = 0.0
    for attempt in attempts:
        if (attempt["arm"] == "G") is not gpu:
            continue
        path = ROOT / attempt["artifact_root"] / "attempt-complete.json"
        if not path.is_file():
            continue
        receipt = read_json(path)
        value = float(receipt["execution"]["wall_seconds"])
        require(math.isfinite(value) and value >= 0, "attempt wall-time receipt drift")
        total += value
    return total


def bounded_timeout(
    row: Mapping[str, str],
    attempts: Sequence[Mapping[str, str]],
) -> tuple[int, str, bool]:
    gpu = row["arm"] == "G"
    budget_name = "gpu_hours" if gpu else "cpu_wall"
    limit = MAX_GPU_SECONDS if gpu else MAX_CPU_WALL_SECONDS
    remaining = limit - completed_wall_seconds(attempts, gpu=gpu)
    require(remaining >= 1, f"fixed {budget_name} budget exhausted before {row['attempt_id']}")
    planned = int(row["timeout_seconds"])
    applied = min(planned, int(math.floor(remaining)))
    return applied, budget_name, applied < planned


def execute_attempt(
    row: Mapping[str, str],
    source_commit: str,
    timeout_seconds: int,
    budget_name: str,
    budget_limited: bool,
) -> dict[str, Any]:
    destination = ROOT / row["artifact_root"]
    if destination.is_dir():
        return validate_terminal_receipt(destination, row, source_commit)
    stale = sorted(ARTIFACT_ROOT.glob(f".{row['attempt_id']}.partial.*"))
    require(not stale, f"stale partial attempt cannot be retried: {row['attempt_id']}")
    partial = ARTIFACT_ROOT / f".{row['attempt_id']}.partial.{os.getpid()}"
    partial.mkdir()
    (partial / "inputs").mkdir()
    (partial / "output").mkdir()
    shutil.copy2(ROOT / row["query_fasta_path"], partial / "inputs/query.fa")
    shutil.copy2(ROOT / row["target_fasta_path"], partial / "inputs/target.fa")
    shutil.copy2(ROOT / row["binary_path"], partial / "backend")
    (partial / "backend").chmod(0o755)
    augmented = dict(row)
    augmented["_partial_root"] = str(partial)
    command, environment = command_for(augmented)
    config = {
        "attempt": dict(row),
        "attempt_config_sha256": canonical_digest(dict(row)),
        "source_commit": source_commit,
        "sandbox": {
            "engine": "/usr/bin/bwrap",
            "unshare_all": True,
            "network_unshared": True,
            "repository_and_label_manifest_mounted": False,
            "writable_mount": "/work",
        },
        "command": command,
        "explicit_environment": {key: value for key, value in environment.items() if key not in {"HOME", "LANG", "LC_ALL", "PATH", "OMP_NUM_THREADS"}},
    }
    atomic_json(partial / "attempt-config.json", config)
    execution = run_process(command, environment, partial, timeout_seconds)
    execution["budget_class"] = budget_name
    execution["budget_limited_timeout"] = budget_limited
    technical_success = execution["returncode"] == 0 and not execution["timed_out"]
    failure_reason: str | None = None
    output: Path | None = None
    telemetry: dict[str, Any] | None = None
    if technical_success:
        try:
            if row["arm"] in {"A", "G"}:
                output = fasim_output(partial / "output")
                if row["arm"] == "G":
                    raw_telemetry = partial / "telemetry.json"
                    require(raw_telemetry.is_file(), "G attempt telemetry missing")
                    sys.path.insert(0, str(ROOT / "scripts"))
                    from canonical_hybrid_v2_telemetry import validate_attempt

                    summary = validate_attempt(raw_telemetry, output, (partial / "stderr.txt").read_text(encoding="utf-8", errors="replace"))
                    require(int(summary.get("fallbacks", -1)) == 0, "G attempt used unexpected fallback")
                    atomic_json(partial / "telemetry-summary.json", summary)
                    telemetry = gzip_deterministic(raw_telemetry)
            else:
                output = partial / "output/triplexator-summary.tsv"
                require(output.is_file(), "Triplexator summary output missing")
        except (OSError, ValueError, KeyError, RunnerError) as error:
            technical_success = False
            failure_reason = f"output_validation:{type(error).__name__}:{error}"
    if not technical_success and failure_reason is None:
        if execution["timed_out"] and budget_limited:
            failure_reason = f"fixed_{budget_name}_budget_timeout"
        else:
            failure_reason = "timeout" if execution["timed_out"] else f"nonzero_exit_{execution['returncode']}"

    receipt = {
        "schema_version": 1,
        "phase": 6,
        "attempt_id": row["attempt_id"],
        "dataset_id": row["dataset_id"],
        "outer_lncRNA_id": row["outer_lncRNA_id"],
        "arm": row["arm"],
        "backend": row["backend"],
        "status": "success" if technical_success else "technical_failure",
        "failure_reason": failure_reason,
        "source_commit": source_commit,
        "attempt_config_sha256": canonical_digest(dict(row)),
        "query_fasta_sha256": sha256_file(partial / "inputs/query.fa"),
        "target_fasta_sha256": sha256_file(partial / "inputs/target.fa"),
        "binary_sha256": sha256_file(partial / "backend"),
        "output_path": None if output is None else output.relative_to(partial).as_posix(),
        "output_sha256": None if output is None or not output.is_file() else sha256_file(output),
        "labels_visible_to_backend": False,
        "label_manifest_mounted_in_sandbox": False,
        "comparison_started": False,
        "retry_policy": "none",
        "replacement_retry_allowed": False,
        "telemetry_storage": telemetry,
        "execution": execution,
    }
    manifest_payload = artifact_manifest(partial)
    atomic_write(partial / "artifact-manifest.tsv", manifest_payload)
    manifest_sha = sha256_file(partial / "artifact-manifest.tsv")
    atomic_write(partial / "artifact-manifest.sha256", f"{manifest_sha}  artifact-manifest.tsv\n".encode("ascii"))
    receipt["artifact_manifest_sha256"] = manifest_sha
    atomic_json(partial / "attempt-complete.json", receipt)
    os.replace(partial, destination)
    return read_json(destination / "attempt-complete.json")


def rebuild_summary(attempts: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    receipts = []
    missing = []
    for row in attempts:
        path = ROOT / row["artifact_root"] / "attempt-complete.json"
        if path.is_file():
            receipts.append(read_json(path))
        else:
            missing.append(row["attempt_id"])
    gpu_seconds = completed_wall_seconds(attempts, gpu=True)
    cpu_seconds = completed_wall_seconds(attempts, gpu=False)
    artifact_bytes = formal_artifact_bytes()
    summary = {
        "schema_version": 1,
        "phase": 6,
        "status": "complete" if len(receipts) == len(attempts) else "in_progress_or_interrupted",
        "planned_attempt_count": len(attempts),
        "terminal_attempt_count": len(receipts),
        "successful_attempt_count": sum(receipt["status"] == "success" for receipt in receipts),
        "technical_failure_count": sum(receipt["status"] != "success" for receipt in receipts),
        "missing_attempt_ids": missing,
        "comparison_started": False,
        "gpu_wall_seconds": format(gpu_seconds, ".9f"),
        "cpu_wall_seconds": format(cpu_seconds, ".9f"),
        "max_gpu_seconds": MAX_GPU_SECONDS,
        "max_cpu_wall_seconds": MAX_CPU_WALL_SECONDS,
        "formal_artifact_bytes": artifact_bytes,
        "tracked_evidence_reservation_bytes": TRACKED_EVIDENCE_RESERVATION_BYTES,
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_ARTIFACT_STORAGE_BYTES,
        "fixed_runtime_budget_gate_pass": gpu_seconds <= MAX_GPU_SECONDS and cpu_seconds <= MAX_CPU_WALL_SECONDS,
        "fixed_artifact_budget_gate_pass": artifact_bytes + TRACKED_EVIDENCE_RESERVATION_BYTES <= FIXED_TOTAL_ARTIFACT_STORAGE_BYTES,
        "updated_utc": utc_now(),
    }
    atomic_json(ARTIFACT_ROOT / "run-summary.json", summary)
    return summary


def execute(attempts: Sequence[dict[str, str]]) -> dict[str, Any]:
    source_commit = execution_source_commit()
    if not ARTIFACT_ROOT.exists():
        ARTIFACT_ROOT.mkdir(parents=True)
        atomic_json(
            ARTIFACT_ROOT / "execution-snapshot.json",
            {
                "schema_version": 1,
                "source_commit": source_commit,
                "attempt_plan_sha256": sha256_file(ATTEMPT_PLAN),
                "benchmark_plan_sha256": sha256_file(BENCHMARK_PLAN),
                "manifest_sha256": sha256_file(MANIFEST),
                "runner_sha256": sha256_file(Path(__file__).resolve()),
                "gpu_inventory": visible_gpu_inventory(),
                "comparison_started": False,
                "labels_copied_or_mounted": False,
                "created_utc": utc_now(),
            },
        )
    for row in sorted(attempts, key=lambda value: int(value["execution_index"])):
        destination = ROOT / row["artifact_root"]
        if destination.is_dir():
            timeout_seconds = int(row["timeout_seconds"])
            budget_name = "gpu_hours" if row["arm"] == "G" else "cpu_wall"
            budget_limited = False
        else:
            require(
                formal_artifact_bytes() + TRACKED_EVIDENCE_RESERVATION_BYTES <= FIXED_TOTAL_ARTIFACT_STORAGE_BYTES,
                f"fixed artifact budget exhausted before {row['attempt_id']}",
            )
            timeout_seconds, budget_name, budget_limited = bounded_timeout(row, attempts)
        execute_attempt(row, source_commit, timeout_seconds, budget_name, budget_limited)
        summary = rebuild_summary(attempts)
        require(summary["fixed_runtime_budget_gate_pass"], "fixed Phase 6 runtime budget exceeded")
        require(summary["fixed_artifact_budget_gate_pass"], "fixed Phase 6 artifact budget exceeded")
    return rebuild_summary(attempts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    try:
        attempts, plan = validate_frozen_plan()
        if args.preflight:
            require(not ARTIFACT_ROOT.exists(), "Phase 6 artifact root exists before formal execution")
            print(json.dumps({"status": "preflight_pass", "attempt_count": len(attempts), "dataset_count": plan["dataset_count"], "labels_visible_to_backend": False}, sort_keys=True))
            return 0
        if args.summary:
            require(ARTIFACT_ROOT.is_dir(), "Phase 6 artifact root missing")
            print(json.dumps(rebuild_summary(attempts), sort_keys=True))
            return 0
        print(json.dumps(execute(attempts), sort_keys=True))
        return 0
    except (RunnerError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"successor Phase 6 runner failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
