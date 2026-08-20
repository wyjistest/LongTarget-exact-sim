#!/usr/bin/env python3
"""Run whole-query GPU jobs through a resumable, fenced dynamic pool."""

from __future__ import annotations

import argparse
import csv
import ctypes
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


PLAN_SCHEMA = "long_query_dynamic_gpu_pool_plan_v1"
STATE_SCHEMA = "long_query_dynamic_gpu_pool_state_v1"
CLAIM_SCHEMA = "long_query_dynamic_gpu_pool_claim_v1"
RECEIPT_SCHEMA = "long_query_dynamic_gpu_attempt_receipt_v1"
STATUS_SCHEMA = "long_query_dynamic_gpu_pool_status_v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_MANIFEST_FIELDS = (
    "gene_id",
    "query_length_nt",
    "estimated_seconds",
    "query_path",
    "query_file_sha256",
    "query_sequence_sha256",
)


class PoolError(RuntimeError):
    """A fail-closed pool contract violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PoolError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def epoch_now() -> float:
    return time.time()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sequence_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                continue
            digest.update("".join(line.split()).upper().encode("ascii"))
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".tmp.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    atomic_bytes(path, payload)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PoolError(f"cannot read JSON {path}: {error}") from error
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def clean_field(value: object) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def validate_identifier(value: object, label: str) -> str:
    identifier = str(value or "")
    require(bool(SAFE_ID.fullmatch(identifier)), f"unsafe {label}: {identifier!r}")
    require(identifier not in {".", ".."}, f"unsafe {label}: {identifier!r}")
    return identifier


@contextmanager
def pool_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "pool.lock").open("a+", encoding="ascii") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(root: Path, event: str, **fields: object) -> None:
    path = root / "events.tsv"
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        if new_file:
            handle.write("utc\tevent\tjob_id\tworker_id\tlease_epoch\tdetail\n")
        detail = " ".join(
            f"{key}={clean_field(value)}"
            for key, value in sorted(fields.items())
            if key not in {"job_id", "worker_id", "lease_epoch"}
        )
        handle.write(
            "\t".join(
                clean_field(value)
                for value in (
                    utc_now(),
                    event,
                    fields.get("job_id", ""),
                    fields.get("worker_id", ""),
                    fields.get("lease_epoch", ""),
                    detail,
                )
            )
            + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())


def validate_plan(path: Path) -> dict[str, Any]:
    plan = read_json(path)
    require(plan.get("schema_version") == PLAN_SCHEMA, "unexpected plan schema")
    validate_identifier(plan.get("pool_id"), "pool_id")

    manifest = plan.get("manifest")
    require(isinstance(manifest, dict), "missing manifest contract")
    raw_manifest_path = str(manifest.get("path") or "")
    require(bool(raw_manifest_path), "missing manifest path")
    manifest_path = Path(raw_manifest_path)
    require(manifest_path.is_absolute(), "manifest path must be absolute")
    require(manifest_path.is_file(), f"missing manifest: {manifest_path}")
    require(not manifest_path.is_symlink(), f"manifest must not be a symlink: {manifest_path}")
    require(
        sha256_file(manifest_path) == manifest.get("sha256"),
        "manifest digest mismatch",
    )

    raw_results_root = str(plan.get("results_root") or "")
    require(bool(raw_results_root), "missing results_root")
    results_root = Path(raw_results_root)
    require(results_root.is_absolute(), "results_root must be absolute")
    require(not results_root.is_symlink(), "results_root must not be a symlink")

    workers = plan.get("workers")
    require(isinstance(workers, list) and workers, "missing workers")
    worker_ids: set[str] = set()
    gpu_ids: set[str] = set()
    for worker in workers:
        require(isinstance(worker, dict), "invalid worker entry")
        worker_id = validate_identifier(worker.get("worker_id"), "worker_id")
        gpu_id = str(worker.get("gpu_id") if worker.get("gpu_id") is not None else "")
        require(gpu_id and gpu_id not in gpu_ids, "duplicate or missing gpu_id")
        require(worker_id not in worker_ids, "duplicate worker_id")
        worker_ids.add(worker_id)
        gpu_ids.add(gpu_id)
        model = worker.get("runtime_model")
        require(isinstance(model, dict), f"missing runtime model: {worker_id}")
        coefficients = model.get("coefficients")
        require(isinstance(coefficients, dict) and coefficients, f"missing runtime coefficients: {worker_id}")
        for feature, coefficient in coefficients.items():
            require(isinstance(feature, str) and feature, "invalid runtime feature")
            float(coefficient)
        float(model.get("intercept_seconds", 0.0))

    runner = plan.get("runner")
    require(isinstance(runner, dict), "missing runner contract")
    command = runner.get("command")
    require(
        isinstance(command, list)
        and command
        and all(isinstance(token, str) and token for token in command),
        "runner command must be a nonempty string list",
    )
    environment = runner.get("environment", {})
    require(isinstance(environment, dict), "runner environment must be an object")
    require(
        all(isinstance(key, str) and isinstance(value, str) for key, value in environment.items()),
        "runner environment entries must be strings",
    )

    lease_seconds = float(plan.get("lease_seconds", 0))
    heartbeat_seconds = float(plan.get("heartbeat_seconds", 0))
    require(lease_seconds > 0, "invalid lease_seconds")
    require(heartbeat_seconds > 0, "invalid heartbeat_seconds")
    require(heartbeat_seconds < lease_seconds, "heartbeat must be shorter than lease")
    require(int(plan.get("max_attempts", 0)) > 0, "invalid max_attempts")
    require(float(plan.get("poll_seconds", 5.0)) > 0, "invalid poll_seconds")
    require(float(plan.get("worker_stale_seconds", lease_seconds)) > heartbeat_seconds, "invalid worker_stale_seconds")
    receipt_contract = plan.get("receipt_contract")
    require(isinstance(receipt_contract, dict) and receipt_contract, "missing receipt contract")
    return plan


def load_manifest(plan: dict[str, Any]) -> list[dict[str, str]]:
    path = Path(plan["manifest"]["path"])
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = tuple(reader.fieldnames or ())
        for required in REQUIRED_MANIFEST_FIELDS:
            require(required in fields, f"manifest missing field: {required}")
        rows = list(reader)
    require(rows, "manifest is empty")
    seen: set[str] = set()
    for row in rows:
        job_id = validate_identifier(row.get("job_id") or row["gene_id"], "job_id")
        validate_identifier(row["gene_id"], "gene_id")
        require(job_id not in seen, f"duplicate job_id: {job_id}")
        seen.add(job_id)
        row["job_id"] = job_id
        require(int(row["query_length_nt"]) > 0, f"invalid query length: {job_id}")
        require(float(row["estimated_seconds"]) > 0, f"invalid estimate: {job_id}")
        query = Path(row["query_path"])
        require(query.is_absolute(), f"query path must be absolute: {query}")
        require(query.is_file() and not query.is_symlink(), f"unsafe query: {query}")
        require(sha256_file(query) == row["query_file_sha256"], f"query file digest mismatch: {job_id}")
        require(sequence_sha256(query) == row["query_sequence_sha256"], f"query sequence digest mismatch: {job_id}")
    return rows


def predict_base_seconds(row: dict[str, str], worker: dict[str, Any]) -> float:
    model = worker["runtime_model"]
    value = float(model.get("intercept_seconds", 0.0))
    for feature, coefficient in model["coefficients"].items():
        require(feature in row, f"manifest lacks model feature: {feature}")
        value += float(coefficient) * float(row[feature])
    require(value > 0.0, f"nonpositive prediction for {row['job_id']}")
    return value


def initialize_pool(root: Path, plan_path: Path) -> dict[str, Any]:
    plan_path = plan_path.resolve()
    plan = validate_plan(plan_path)
    rows = load_manifest(plan)
    plan_payload = plan_path.read_bytes()
    plan_digest = hashlib.sha256(plan_payload).hexdigest()
    manifest_path = Path(plan["manifest"]["path"])
    manifest_payload = manifest_path.read_bytes()
    with pool_lock(root):
        state_path = root / "state.json"
        frozen_plan_path = root / "plan.json"
        if state_path.exists():
            state = read_json(state_path)
            require(state.get("plan_sha256") == plan_digest, "pool plan drift")
            require(state.get("pool_id") == plan["pool_id"], "pool identity drift")
            require(frozen_plan_path.is_file(), "frozen plan is missing")
            require(sha256_file(frozen_plan_path) == plan_digest, "frozen plan digest drift")
            return state

        atomic_bytes(frozen_plan_path, plan_payload)
        atomic_bytes(root / "manifest.tsv", manifest_payload)
        worker_entries: dict[str, dict[str, Any]] = {}
        worker_by_id = {worker["worker_id"]: worker for worker in plan["workers"]}
        for worker_id, worker in worker_by_id.items():
            worker_entries[worker_id] = {
                "worker_id": worker_id,
                "gpu_id": str(worker["gpu_id"]),
                "gpu_uuid": str(worker.get("gpu_uuid") or "unknown"),
                "cpu_affinity": str(worker.get("cpu_affinity") or ""),
                "status": "offline",
                "current_job_id": None,
                "current_lease_epoch": None,
                "heartbeat_epoch_seconds": None,
                "heartbeat_utc": None,
                "observed_base_seconds": 0.0,
                "observed_wall_seconds": 0.0,
                "completed_jobs": 0,
            }

        jobs: dict[str, dict[str, Any]] = {}
        for manifest_order, row in enumerate(rows, 1):
            predictions = {
                worker_id: predict_base_seconds(row, worker)
                for worker_id, worker in worker_by_id.items()
            }
            jobs[row["job_id"]] = {
                "job_id": row["job_id"],
                "gene_id": row["gene_id"],
                "manifest_order": manifest_order,
                "row": row,
                "base_predictions": predictions,
                "status": "pending",
                "attempt_count": 0,
                "lease_epoch": 0,
                "lease_owner": None,
                "lease_started_epoch_seconds": None,
                "lease_started_utc": None,
                "lease_expires_epoch_seconds": None,
                "attempt_dir": None,
                "completed_worker_id": None,
                "completed_lease_epoch": None,
                "completed_utc": None,
                "actual_wall_seconds": None,
                "receipt_sha256": None,
                "failure": None,
            }
        state = {
            "schema_version": STATE_SCHEMA,
            "pool_id": plan["pool_id"],
            "plan_sha256": plan_digest,
            "manifest_sha256": plan["manifest"]["sha256"],
            "created_utc": utc_now(),
            "updated_utc": utc_now(),
            "jobs": jobs,
            "workers": worker_entries,
        }
        atomic_json(state_path, state)
        append_event(root, "pool_initialized", jobs=len(jobs), workers=len(worker_entries))
        return state


def load_frozen(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    plan_path = root / "plan.json"
    plan = read_json(plan_path)
    state = read_json(root / "state.json")
    require(plan.get("schema_version") == PLAN_SCHEMA, "frozen plan schema drift")
    require(state.get("schema_version") == STATE_SCHEMA, "state schema drift")
    require(state.get("pool_id") == plan.get("pool_id"), "state/plan pool mismatch")
    require(state.get("plan_sha256") == sha256_file(plan_path), "frozen plan digest drift")
    return plan, state


def save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_utc"] = utc_now()
    atomic_json(root / "state.json", state)


def worker_factor(worker: dict[str, Any]) -> float:
    base = float(worker.get("observed_base_seconds") or 0.0)
    wall = float(worker.get("observed_wall_seconds") or 0.0)
    if base <= 0.0 or wall <= 0.0:
        return 1.0
    return wall / base


def predicted_seconds(job: dict[str, Any], worker_id: str, workers: dict[str, dict[str, Any]]) -> float:
    return float(job["base_predictions"][worker_id]) * worker_factor(workers[worker_id])


def results_completed_dir(plan: dict[str, Any], job_id: str) -> Path:
    return Path(plan["results_root"]) / job_id / "completed"


def safe_relative_artifact(publish_dir: Path, relative: str) -> Path:
    require(relative and not os.path.isabs(relative), "artifact path must be relative")
    artifact = (publish_dir / relative).resolve()
    publish_resolved = publish_dir.resolve()
    require(artifact != publish_resolved, "artifact must name a file")
    require(publish_resolved in artifact.parents, "artifact escapes publish directory")
    return artifact


def validate_attempt_receipt(
    plan: dict[str, Any],
    job: dict[str, Any],
    worker_id: str,
    lease_epoch: int,
    publish_dir: Path,
) -> dict[str, Any]:
    require(publish_dir.is_dir() and not publish_dir.is_symlink(), "missing or unsafe publish directory")
    receipt_path = publish_dir / "attempt-receipt.json"
    require(receipt_path.is_file() and not receipt_path.is_symlink(), "missing or unsafe receipt")
    receipt = read_json(receipt_path)
    require(receipt.get("schema_version") == RECEIPT_SCHEMA, "receipt schema drift")
    require(receipt.get("status") == "complete", "attempt is not complete")
    require(receipt.get("pool_id") == plan["pool_id"], "receipt pool mismatch")
    require(receipt.get("job_id") == job["job_id"], "receipt job mismatch")
    require(receipt.get("gene_id") == job["gene_id"], "receipt gene mismatch")
    require(receipt.get("worker_id") == worker_id, "receipt worker mismatch")
    require(int(receipt.get("lease_epoch") or -1) == lease_epoch, "receipt epoch mismatch")
    for key, expected in plan["receipt_contract"].items():
        require(receipt.get(key) == expected, f"receipt contract mismatch: {key}")
    row = job["row"]
    for key in ("query_file_sha256", "query_sequence_sha256"):
        require(receipt.get(key) == row[key], f"receipt query mismatch: {key}")
    artifact = safe_relative_artifact(publish_dir, str(receipt.get("artifact_path") or ""))
    require(artifact.is_file() and not artifact.is_symlink(), "artifact missing or unsafe")
    require(artifact.stat().st_size == int(receipt.get("artifact_size_bytes") or -1), "artifact size mismatch")
    require(sha256_file(artifact) == receipt.get("artifact_sha256"), "artifact digest mismatch")
    require(float(receipt.get("wall_seconds") or 0.0) > 0.0, "invalid wall_seconds")
    return receipt


def finalize_job_state(
    root: Path,
    state: dict[str, Any],
    job: dict[str, Any],
    worker_id: str,
    lease_epoch: int,
    receipt: dict[str, Any],
    completed_dir: Path,
    recovered: bool,
) -> None:
    require(job["status"] != "complete", f"job already complete: {job['job_id']}")
    worker = state["workers"][worker_id]
    actual_wall = float(receipt["wall_seconds"])
    worker["observed_base_seconds"] = float(worker["observed_base_seconds"]) + float(job["base_predictions"][worker_id])
    worker["observed_wall_seconds"] = float(worker["observed_wall_seconds"]) + actual_wall
    worker["completed_jobs"] = int(worker["completed_jobs"]) + 1
    worker["status"] = "idle"
    worker["current_job_id"] = None
    worker["current_lease_epoch"] = None
    worker["heartbeat_epoch_seconds"] = epoch_now()
    worker["heartbeat_utc"] = utc_now()
    job["status"] = "complete"
    job["completed_worker_id"] = worker_id
    job["completed_lease_epoch"] = lease_epoch
    job["completed_utc"] = utc_now()
    job["actual_wall_seconds"] = actual_wall
    job["receipt_sha256"] = sha256_file(completed_dir / "attempt-receipt.json")
    job["lease_owner"] = None
    job["lease_expires_epoch_seconds"] = None
    job["failure"] = None
    append_event(
        root,
        "job_publication_recovered" if recovered else "job_completed",
        job_id=job["job_id"],
        worker_id=worker_id,
        lease_epoch=lease_epoch,
        wall_seconds=actual_wall,
        artifact_sha256=receipt["artifact_sha256"],
    )


def recover_publications(root: Path, plan: dict[str, Any], state: dict[str, Any]) -> bool:
    changed = False
    for job in state["jobs"].values():
        if job["status"] != "leased":
            continue
        completed_dir = results_completed_dir(plan, job["job_id"])
        if not completed_dir.exists():
            continue
        worker_id = str(job.get("lease_owner") or "")
        lease_epoch = int(job.get("lease_epoch") or 0)
        require(worker_id in state["workers"], "published job has no valid lease owner")
        receipt = validate_attempt_receipt(plan, job, worker_id, lease_epoch, completed_dir)
        finalize_job_state(root, state, job, worker_id, lease_epoch, receipt, completed_dir, True)
        changed = True
    return changed


def expire_leases(root: Path, plan: dict[str, Any], state: dict[str, Any], now: float) -> bool:
    changed = False
    for job in state["jobs"].values():
        if job["status"] != "leased":
            continue
        expires = float(job.get("lease_expires_epoch_seconds") or 0.0)
        if expires > now:
            continue
        owner = str(job.get("lease_owner") or "")
        epoch = int(job.get("lease_epoch") or 0)
        terminal = int(job["attempt_count"]) >= int(plan["max_attempts"])
        job["status"] = "failed" if terminal else "pending"
        job["lease_owner"] = None
        job["lease_started_epoch_seconds"] = None
        job["lease_started_utc"] = None
        job["lease_expires_epoch_seconds"] = None
        job["attempt_dir"] = None
        job["failure"] = "lease_expired"
        worker = state["workers"].get(owner)
        if worker and worker.get("current_job_id") == job["job_id"]:
            worker["status"] = "failed" if terminal else "stale"
            worker["current_job_id"] = None
            worker["current_lease_epoch"] = None
        append_event(
            root,
            "lease_expired_terminal" if terminal else "lease_expired",
            job_id=job["job_id"],
            worker_id=owner,
            lease_epoch=epoch,
        )
        changed = True
    return changed


def active_worker_ids(
    plan: dict[str, Any], state: dict[str, Any], now: float, claimant: str
) -> list[str]:
    stale_after = float(plan.get("worker_stale_seconds", plan["lease_seconds"]))
    active: list[str] = []
    for worker_id in sorted(state["workers"]):
        worker = state["workers"][worker_id]
        heartbeat_time = float(worker.get("heartbeat_epoch_seconds") or 0.0)
        current = worker.get("current_job_id")
        has_live_lease = False
        if current and current in state["jobs"]:
            job = state["jobs"][current]
            has_live_lease = job.get("status") == "leased" and job.get("lease_owner") == worker_id
        recently_online = (
            worker.get("status") in {"idle", "running"}
            and heartbeat_time > 0
            and now - heartbeat_time <= stale_after
        )
        if worker_id == claimant or has_live_lease or recently_online:
            active.append(worker_id)
    require(claimant in active, "claiming worker is not active")
    return active


def schedule_pending(
    state: dict[str, Any], now: float, eligible_workers: list[str]
) -> dict[str, list[str]]:
    workers = state["workers"]
    available: dict[str, float] = {}
    for worker_id in eligible_workers:
        worker = workers[worker_id]
        job_id = worker.get("current_job_id")
        if job_id and job_id in state["jobs"]:
            job = state["jobs"][job_id]
            if job.get("status") == "leased" and job.get("lease_owner") == worker_id:
                elapsed = max(0.0, now - float(job.get("lease_started_epoch_seconds") or now))
                available[worker_id] = max(0.0, predicted_seconds(job, worker_id, workers) - elapsed)
                continue
        available[worker_id] = 0.0

    pending = [job for job in state["jobs"].values() if job["status"] == "pending"]

    def rank(job: dict[str, Any]) -> tuple[float, float, str]:
        predictions = sorted(predicted_seconds(job, worker_id, workers) for worker_id in eligible_workers)
        mean = sum(predictions) / len(predictions)
        regret = predictions[1] - predictions[0] if len(predictions) > 1 else 0.0
        return (-mean, -regret, str(job["job_id"]))

    pending.sort(key=rank)
    assignment = {worker_id: [] for worker_id in eligible_workers}
    worker_order = {worker_id: index for index, worker_id in enumerate(eligible_workers)}
    for job in pending:
        worker_id = min(
            eligible_workers,
            key=lambda candidate: (
                available[candidate] + predicted_seconds(job, candidate, workers),
                worker_order[candidate],
            ),
        )
        assignment[worker_id].append(job["job_id"])
        available[worker_id] += predicted_seconds(job, worker_id, workers)
    return assignment


def claim_job(root: Path, worker_id: str) -> dict[str, Any] | None:
    validate_identifier(worker_id, "worker_id")
    now = epoch_now()
    with pool_lock(root):
        plan, state = load_frozen(root)
        require(worker_id in state["workers"], f"unknown worker: {worker_id}")
        changed = recover_publications(root, plan, state)
        changed = expire_leases(root, plan, state, now) or changed
        worker = state["workers"][worker_id]
        current_job_id = worker.get("current_job_id")
        if current_job_id:
            current = state["jobs"].get(current_job_id)
            require(
                current is not None
                and current.get("status") == "leased"
                and current.get("lease_owner") == worker_id,
                f"worker has inconsistent current job: {worker_id}",
            )
            current["lease_expires_epoch_seconds"] = now + float(plan["lease_seconds"])
            worker["status"] = "running"
            worker["heartbeat_epoch_seconds"] = now
            worker["heartbeat_utc"] = utc_now()
            save_state(root, state)
            return read_json(Path(current["attempt_dir"]) / "claim.json")

        worker["status"] = "idle"
        worker["heartbeat_epoch_seconds"] = now
        worker["heartbeat_utc"] = utc_now()
        eligible = active_worker_ids(plan, state, now, worker_id)
        assignment = schedule_pending(state, now, eligible)
        candidates = assignment.get(worker_id, [])
        if not candidates:
            save_state(root, state)
            return None

        job = state["jobs"][candidates[0]]
        require(job["status"] == "pending", "scheduler selected nonpending job")
        require(int(job["attempt_count"]) < int(plan["max_attempts"]), f"attempt limit reached: {job['job_id']}")
        epoch = int(job["lease_epoch"]) + 1
        attempt_dir = root / "attempts" / job["job_id"] / f"epoch-{epoch:06d}-{worker_id}"
        require(not attempt_dir.exists(), f"attempt directory already exists: {attempt_dir}")
        attempt_dir.mkdir(parents=True)
        claim = {
            "schema_version": CLAIM_SCHEMA,
            "pool_id": state["pool_id"],
            "job_id": job["job_id"],
            "gene_id": job["gene_id"],
            "worker_id": worker_id,
            "gpu_id": worker["gpu_id"],
            "gpu_uuid": worker["gpu_uuid"],
            "cpu_affinity": worker["cpu_affinity"],
            "lease_epoch": epoch,
            "lease_started_utc": utc_now(),
            "row": job["row"],
            "receipt_contract": plan["receipt_contract"],
            "base_predicted_seconds": job["base_predictions"][worker_id],
            "calibrated_predicted_seconds": predicted_seconds(job, worker_id, state["workers"]),
        }
        atomic_json(attempt_dir / "claim.json", claim)
        job["status"] = "leased"
        job["attempt_count"] = int(job["attempt_count"]) + 1
        job["lease_epoch"] = epoch
        job["lease_owner"] = worker_id
        job["lease_started_epoch_seconds"] = now
        job["lease_started_utc"] = claim["lease_started_utc"]
        job["lease_expires_epoch_seconds"] = now + float(plan["lease_seconds"])
        job["attempt_dir"] = str(attempt_dir)
        job["failure"] = None
        worker["status"] = "running"
        worker["current_job_id"] = job["job_id"]
        worker["current_lease_epoch"] = epoch
        save_state(root, state)
        append_event(
            root,
            "lease_claimed",
            job_id=job["job_id"],
            worker_id=worker_id,
            lease_epoch=epoch,
            predicted_seconds=claim["calibrated_predicted_seconds"],
        )
        return claim


def heartbeat(root: Path, worker_id: str, job_id: str, lease_epoch: int) -> bool:
    now = epoch_now()
    with pool_lock(root):
        plan, state = load_frozen(root)
        changed = recover_publications(root, plan, state)
        changed = expire_leases(root, plan, state, now) or changed
        job = state["jobs"].get(job_id)
        if not (
            job
            and job.get("status") == "leased"
            and job.get("lease_owner") == worker_id
            and int(job.get("lease_epoch") or 0) == lease_epoch
        ):
            if changed:
                save_state(root, state)
            return False
        job["lease_expires_epoch_seconds"] = now + float(plan["lease_seconds"])
        worker = state["workers"][worker_id]
        worker["heartbeat_epoch_seconds"] = now
        worker["heartbeat_utc"] = utc_now()
        save_state(root, state)
        return True


def complete_job(root: Path, worker_id: str, job_id: str, lease_epoch: int) -> Path:
    with pool_lock(root):
        plan, state = load_frozen(root)
        job = state["jobs"].get(job_id)
        require(job is not None, f"unknown job: {job_id}")
        completed_dir = results_completed_dir(plan, job_id)
        if job.get("status") == "complete":
            require(job.get("completed_worker_id") == worker_id, "idempotent completion worker mismatch")
            require(int(job.get("completed_lease_epoch") or 0) == lease_epoch, "idempotent completion epoch mismatch")
            validate_attempt_receipt(plan, job, worker_id, lease_epoch, completed_dir)
            return completed_dir
        require(job.get("status") == "leased", "job is not leased")
        require(job.get("lease_owner") == worker_id, "completion worker is fenced")
        require(int(job.get("lease_epoch") or 0) == lease_epoch, "completion epoch is fenced")

        if completed_dir.exists():
            attempt_publish = Path(str(job.get("attempt_dir") or "")) / "publish"
            require(not attempt_publish.exists(), "both attempt and completed publications exist")
            receipt = validate_attempt_receipt(plan, job, worker_id, lease_epoch, completed_dir)
            finalize_job_state(root, state, job, worker_id, lease_epoch, receipt, completed_dir, True)
            save_state(root, state)
            return completed_dir

        attempt_dir = Path(str(job.get("attempt_dir") or ""))
        publish_dir = attempt_dir / "publish"
        receipt = validate_attempt_receipt(plan, job, worker_id, lease_epoch, publish_dir)
        completed_dir.parent.mkdir(parents=True, exist_ok=True)
        require(publish_dir.stat().st_dev == completed_dir.parent.stat().st_dev, "attempt and results roots must share a filesystem")
        os.replace(publish_dir, completed_dir)
        _fsync_directory(completed_dir.parent)
        finalize_job_state(root, state, job, worker_id, lease_epoch, receipt, completed_dir, False)
        save_state(root, state)
        return completed_dir


def fail_job(root: Path, worker_id: str, job_id: str, lease_epoch: int, reason: str) -> str:
    with pool_lock(root):
        plan, state = load_frozen(root)
        if recover_publications(root, plan, state):
            save_state(root, state)
        job = state["jobs"].get(job_id)
        require(job is not None, f"unknown job: {job_id}")
        if job.get("status") == "complete":
            require(job.get("completed_worker_id") == worker_id, "failure is fenced by completed worker")
            require(int(job.get("completed_lease_epoch") or 0) == lease_epoch, "failure is fenced by completed epoch")
            return "complete"
        require(job.get("status") == "leased", "job is not leased")
        require(job.get("lease_owner") == worker_id, "failure worker is fenced")
        require(int(job.get("lease_epoch") or 0) == lease_epoch, "failure epoch is fenced")
        terminal = int(job["attempt_count"]) >= int(plan["max_attempts"])
        job["status"] = "failed" if terminal else "pending"
        job["failure"] = clean_field(reason)
        job["lease_owner"] = None
        job["lease_started_epoch_seconds"] = None
        job["lease_started_utc"] = None
        job["lease_expires_epoch_seconds"] = None
        job["attempt_dir"] = None
        worker = state["workers"][worker_id]
        worker["status"] = "failed" if terminal else "idle"
        worker["current_job_id"] = None
        worker["current_lease_epoch"] = None
        worker["heartbeat_epoch_seconds"] = epoch_now()
        worker["heartbeat_utc"] = utc_now()
        save_state(root, state)
        append_event(
            root,
            "job_failed_terminal" if terminal else "job_requeued",
            job_id=job_id,
            worker_id=worker_id,
            lease_epoch=lease_epoch,
            reason=reason,
        )
        return job["status"]


def mark_worker_offline(root: Path, worker_id: str) -> None:
    with pool_lock(root):
        _, state = load_frozen(root)
        worker = state["workers"].get(worker_id)
        if worker and not worker.get("current_job_id"):
            worker["status"] = "offline"
            worker["heartbeat_epoch_seconds"] = epoch_now()
            worker["heartbeat_utc"] = utc_now()
            save_state(root, state)


def pool_summary(root: Path) -> dict[str, Any]:
    now = epoch_now()
    with pool_lock(root):
        plan, state = load_frozen(root)
        changed = recover_publications(root, plan, state)
        changed = expire_leases(root, plan, state, now) or changed
        if changed:
            save_state(root, state)
        counts: dict[str, int] = {}
        for job in state["jobs"].values():
            counts[job["status"]] = counts.get(job["status"], 0) + 1
        return {
            "schema_version": STATUS_SCHEMA,
            "pool_id": state["pool_id"],
            "updated_utc": state["updated_utc"],
            "job_counts": counts,
            "workers": state["workers"],
        }


def format_placeholders(value: str, replacements: dict[str, str]) -> str:
    try:
        return value.format_map(replacements)
    except KeyError as error:
        raise PoolError(f"unknown runner placeholder: {error}") from error


def runner_replacements(claim: dict[str, Any], attempt_dir: Path) -> dict[str, str]:
    return {
        "claim_json": str(attempt_dir / "claim.json"),
        "attempt_dir": str(attempt_dir),
        "job_id": str(claim["job_id"]),
        "gene_id": str(claim["gene_id"]),
        "worker_id": str(claim["worker_id"]),
        "gpu_id": str(claim["gpu_id"]),
        "gpu_uuid": str(claim["gpu_uuid"]),
        "cpu_affinity": str(claim["cpu_affinity"]),
        "lease_epoch": str(claim["lease_epoch"]),
    }


def render_runner_command(plan: dict[str, Any], claim: dict[str, Any], attempt_dir: Path) -> list[str]:
    replacements = runner_replacements(claim, attempt_dir)
    return [format_placeholders(token, replacements) for token in plan["runner"]["command"]]


def render_runner_environment(plan: dict[str, Any], claim: dict[str, Any], attempt_dir: Path) -> dict[str, str]:
    replacements = runner_replacements(claim, attempt_dir)
    return {
        key: format_placeholders(value, replacements)
        for key, value in plan["runner"].get("environment", {}).items()
    }


def verify_worker_gpu(worker: dict[str, Any]) -> None:
    expected = str(worker.get("gpu_uuid") or "")
    if expected in {"", "unknown"}:
        raise PoolError("GPU UUID verification requested without a frozen UUID")
    command = [
        "nvidia-smi",
        f"--id={worker['gpu_id']}",
        "--query-gpu=uuid",
        "--format=csv,noheader",
    ]
    try:
        observed = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise PoolError(f"cannot verify GPU identity: {error}") from error
    require(observed == expected, f"GPU UUID mismatch: expected {expected}, observed {observed}")


def child_setup() -> None:
    parent = os.getppid()
    os.setsid()
    try:
        libc = ctypes.CDLL(None)
        libc.prctl(1, signal.SIGTERM)
        if os.getppid() != parent:
            os.kill(os.getpid(), signal.SIGTERM)
    except (AttributeError, OSError):
        pass


def terminate_process_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_worker(root: Path, worker_id: str, once: bool = False) -> int:
    plan, _ = load_frozen(root)
    configured = {worker["worker_id"]: worker for worker in plan["workers"]}
    require(worker_id in configured, f"unknown worker: {worker_id}")
    worker_config = configured[worker_id]
    if bool(worker_config.get("verify_gpu_uuid", False)):
        verify_worker_gpu(worker_config)
    worker_lock_path = root / f"worker-{worker_id}.lock"
    with worker_lock_path.open("a+", encoding="ascii") as worker_lock:
        try:
            fcntl.flock(worker_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PoolError(f"worker lock already held: {worker_id}") from error

        resource_handle = None
        resource_lock = worker_config.get("resource_lock")
        if resource_lock:
            resource_path = Path(str(resource_lock))
            resource_path.parent.mkdir(parents=True, exist_ok=True)
            resource_handle = resource_path.open("a+", encoding="ascii")
            try:
                fcntl.flock(resource_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                resource_handle.close()
                raise PoolError(f"resource lock already held: {resource_path}") from error

        try:
            while True:
                claim = claim_job(root, worker_id)
                if claim is None:
                    summary = pool_summary(root)
                    counts = summary["job_counts"]
                    if counts.get("pending", 0) == 0 and counts.get("leased", 0) == 0:
                        return 0 if counts.get("failed", 0) == 0 else 2
                    if once:
                        return 0
                    time.sleep(float(plan.get("poll_seconds", 5.0)))
                    continue

                attempt_dir = root / "attempts" / claim["job_id"] / f"epoch-{int(claim['lease_epoch']):06d}-{worker_id}"
                publish_dir = attempt_dir / "publish"
                if publish_dir.exists():
                    complete_job(root, worker_id, claim["job_id"], int(claim["lease_epoch"]))
                    if once:
                        return 0
                    continue

                command = render_runner_command(plan, claim, attempt_dir)
                log_path = attempt_dir / "worker.log"
                stop_heartbeat = threading.Event()
                lease_lost = threading.Event()
                process: subprocess.Popen[Any] | None = None

                def pulse() -> None:
                    while not stop_heartbeat.wait(float(plan["heartbeat_seconds"])):
                        if not heartbeat(root, worker_id, claim["job_id"], int(claim["lease_epoch"])):
                            lease_lost.set()
                            if process is not None:
                                terminate_process_group(process)
                            return

                environment = os.environ.copy()
                environment.update(render_runner_environment(plan, claim, attempt_dir))
                environment.update(
                    {
                        "LONGTARGET_POOL_ID": str(plan["pool_id"]),
                        "LONGTARGET_POOL_JOB_ID": str(claim["job_id"]),
                        "LONGTARGET_POOL_WORKER_ID": worker_id,
                        "LONGTARGET_POOL_LEASE_EPOCH": str(claim["lease_epoch"]),
                    }
                )
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"start_utc={utc_now()} command={json.dumps(command)}\n")
                    log.flush()
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        env=environment,
                        preexec_fn=child_setup,
                    )
                    heartbeat_thread = threading.Thread(target=pulse, daemon=True)
                    heartbeat_thread.start()
                    return_code = process.wait()
                    stop_heartbeat.set()
                    heartbeat_thread.join()
                    log.write(
                        f"end_utc={utc_now()} exit_code={return_code} lease_lost={int(lease_lost.is_set())}\n"
                    )
                    log.flush()

                if lease_lost.is_set():
                    if once:
                        return 3
                    continue
                if return_code != 0:
                    fail_job(root, worker_id, claim["job_id"], int(claim["lease_epoch"]), f"runner_exit_{return_code}")
                    if once:
                        return return_code
                    continue
                complete_job(root, worker_id, claim["job_id"], int(claim["lease_epoch"]))
                if once:
                    return 0
        finally:
            mark_worker_offline(root, worker_id)
            if resource_handle is not None:
                resource_handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("init")
    initialize.add_argument("--root", type=Path, required=True)
    initialize.add_argument("--plan", type=Path, required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--root", type=Path, required=True)

    claim = subparsers.add_parser("claim")
    claim.add_argument("--root", type=Path, required=True)
    claim.add_argument("--worker-id", required=True)

    beat = subparsers.add_parser("heartbeat")
    beat.add_argument("--root", type=Path, required=True)
    beat.add_argument("--worker-id", required=True)
    beat.add_argument("--job-id", required=True)
    beat.add_argument("--lease-epoch", type=int, required=True)

    complete = subparsers.add_parser("complete")
    complete.add_argument("--root", type=Path, required=True)
    complete.add_argument("--worker-id", required=True)
    complete.add_argument("--job-id", required=True)
    complete.add_argument("--lease-epoch", type=int, required=True)

    failure = subparsers.add_parser("fail")
    failure.add_argument("--root", type=Path, required=True)
    failure.add_argument("--worker-id", required=True)
    failure.add_argument("--job-id", required=True)
    failure.add_argument("--lease-epoch", type=int, required=True)
    failure.add_argument("--reason", required=True)

    worker = subparsers.add_parser("run-worker")
    worker.add_argument("--root", type=Path, required=True)
    worker.add_argument("--worker-id", required=True)
    worker.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            state = initialize_pool(args.root, args.plan)
            print(json.dumps({"status": "initialized", "pool_id": state["pool_id"], "jobs": len(state["jobs"]), "workers": len(state["workers"])}, sort_keys=True))
        elif args.command == "status":
            print(json.dumps(pool_summary(args.root), indent=2, sort_keys=True))
        elif args.command == "claim":
            print(json.dumps(claim_job(args.root, args.worker_id), indent=2, sort_keys=True))
        elif args.command == "heartbeat":
            ok = heartbeat(args.root, args.worker_id, args.job_id, args.lease_epoch)
            print(json.dumps({"heartbeat": ok}, sort_keys=True))
            return 0 if ok else 3
        elif args.command == "complete":
            path = complete_job(args.root, args.worker_id, args.job_id, args.lease_epoch)
            print(json.dumps({"status": "complete", "path": str(path)}, sort_keys=True))
        elif args.command == "fail":
            status = fail_job(args.root, args.worker_id, args.job_id, args.lease_epoch, args.reason)
            print(json.dumps({"status": status}, sort_keys=True))
        elif args.command == "run-worker":
            return run_worker(args.root, args.worker_id, args.once)
        else:
            raise PoolError(f"unsupported command: {args.command}")
        return 0
    except (OSError, PoolError, ValueError, KeyError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
