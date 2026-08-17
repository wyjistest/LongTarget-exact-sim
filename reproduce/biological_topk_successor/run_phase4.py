#!/usr/bin/env python3
"""Preflight or execute the successor biological Top-K Phase 4 epoch."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reproduce.biological_topk import run_fresh_holdout as _IMPL  # noqa: E402
from reproduce.biological_topk_successor import freeze_phase3 as frozen  # noqa: E402


PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/fresh-holdout"
PHASE3_COMMIT_MESSAGE = "repro: freeze successor fresh candidate-site holdout"

_ORIGINAL_EXECUTE_ATTEMPT = _IMPL.execute_attempt


def _configure() -> None:
    _IMPL.frozen = frozen
    _IMPL.PAPER = PAPER
    _IMPL.MANIFEST_PATH = PAPER / "fresh_holdout_manifest.tsv"
    _IMPL.ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_attempt_plan.tsv"
    _IMPL.PLAN_PATH = PAPER / "fresh_holdout_plan.json"
    _IMPL.MANIFEST_CHECKSUM_PATH = PAPER / "fresh_holdout_manifest.sha256"
    _IMPL.RESOURCE_DECISION_PATH = PAPER / "fresh_holdout_resource_decision.json"
    _IMPL.STATE_PATH = PAPER / "PROGRAM_STATE.json"
    _IMPL.ARTIFACT_ROOT = ARTIFACT_ROOT
    _IMPL.PHASE3_COMMIT_MESSAGE = PHASE3_COMMIT_MESSAGE
    _IMPL.__file__ = str(Path(__file__).resolve())


def execution_source_commit() -> str:
    head = _IMPL.git("rev-parse", "HEAD")
    _IMPL.require(_IMPL.git("log", "-1", "--format=%s", head) == PHASE3_COMMIT_MESSAGE, "formal successor execution requires the Phase 3 freeze commit at HEAD")
    committed_state = json.loads(_IMPL.git("show", f"{head}:paper/biological_topk_successor/PROGRAM_STATE.json"))
    _IMPL.require(committed_state["phase_status"]["3"] == "pass" and committed_state["active_phase"] == 4, "committed successor Phase 3 state did not authorize Phase 4")
    live_state = _IMPL.read_json(PAPER / "PROGRAM_STATE.json")
    _IMPL.require(live_state["phase_status"]["4"] == "active", "formal successor execution requires live Phase 4 active state")
    changed = set(_IMPL.git("status", "--porcelain=v1", "--untracked-files=all").splitlines())
    changed_paths = {line[3:] for line in changed if len(line) >= 4}
    allowlist_path = PAPER / "phase_4_change_allowlist.txt"
    _IMPL.require(allowlist_path.is_file(), "missing successor Phase 4 execution allowlist")
    allowed = {line.strip() for line in allowlist_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    _IMPL.require(changed_paths <= allowed, f"formal successor execution checkout has out-of-scope changes: {sorted(changed_paths - allowed)}")
    for path in (Path(__file__).resolve(), frozen.MANIFEST_PATH, frozen.ATTEMPT_PLAN_PATH, frozen.PLAN_PATH):
        relative = path.relative_to(ROOT).as_posix()
        _IMPL.require(not _IMPL.git("diff", "--name-only", head, "--", relative), f"frozen successor execution source changed after Phase 3: {relative}")
    return head


def gzip_file_deterministic(source: Path, destination: Path) -> dict[str, Any]:
    raw_digest = hashlib.sha256()
    raw_size = 0
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as input_handle, os.fdopen(descriptor, "wb") as output_handle:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=output_handle, mtime=0) as gzip_handle:
                for block in iter(lambda: input_handle.read(1024 * 1024), b""):
                    raw_digest.update(block)
                    raw_size += len(block)
                    gzip_handle.write(block)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    compressed = destination.read_bytes()
    _IMPL.require(compressed[:2] == b"\x1f\x8b" and compressed[4:8] == b"\0\0\0\0", "telemetry gzip header is not deterministic")
    return {
        "path": destination.name,
        "compression": "gzip_level_9_mtime_0_no_filename",
        "uncompressed_size_bytes": raw_size,
        "uncompressed_sha256": raw_digest.hexdigest(),
        "compressed_size_bytes": destination.stat().st_size,
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "validated_before_compression": True,
        "lossless": True,
    }


def finalize_attempt_telemetry(destination: Path, row: Mapping[str, str]) -> dict[str, Any]:
    receipt = _IMPL.read_json(destination / "attempt-complete.json")
    if row["arm"] != "G":
        return receipt
    raw = destination / "telemetry.json"
    archive = destination / "telemetry.json.gz"
    _IMPL.require(not (raw.exists() and archive.exists()), "both raw and compressed telemetry are retained")
    changed = False
    if raw.is_file():
        metadata = gzip_file_deterministic(raw, archive)
        raw.unlink()
        changed = True
    else:
        _IMPL.require(archive.is_file(), "G attempt lacks compressed telemetry")
        compressed = archive.read_bytes()
        _IMPL.require(compressed[:2] == b"\x1f\x8b" and compressed[4:8] == b"\0\0\0\0", "stored telemetry gzip header drift")
        metadata = receipt.get("telemetry_storage")
        _IMPL.require(isinstance(metadata, dict), "G attempt lacks telemetry storage receipt")
        _IMPL.require(metadata["path"] == archive.name, "telemetry storage path drift")
        _IMPL.require(metadata["compressed_size_bytes"] == archive.stat().st_size, "telemetry compressed size drift")
        _IMPL.require(metadata["compressed_sha256"] == hashlib.sha256(compressed).hexdigest(), "telemetry compressed digest drift")
    if changed or receipt.get("telemetry_storage") != metadata:
        receipt["telemetry_storage"] = metadata
        artifact_bytes = _IMPL.artifact_manifest(destination)
        _IMPL.atomic_write(destination / "artifact-manifest.tsv", artifact_bytes)
        artifact_sha = _IMPL.sha256_file(destination / "artifact-manifest.tsv")
        _IMPL.atomic_write(destination / "artifact-manifest.sha256", f"{artifact_sha}  artifact-manifest.tsv\n".encode("ascii"))
        receipt["artifact_manifest_sha256"] = artifact_sha
        _IMPL.atomic_json(destination / "attempt-complete.json", receipt)
    return _IMPL.validate_completed_attempt(destination, row)


def execute_attempt(
    row: Mapping[str, str],
    workload: Mapping[str, str],
    inputs: Any,
    snapshot: Path,
    source_commit: str,
) -> dict[str, Any]:
    destination = ROOT / row["artifact_root"]
    try:
        _ORIGINAL_EXECUTE_ATTEMPT(row, workload, inputs, snapshot, source_commit)
    except _IMPL.RunnerError:
        if (destination / "attempt-complete.json").is_file() and row["arm"] == "G":
            finalize_attempt_telemetry(destination, row)
        raise
    return finalize_attempt_telemetry(destination, row)


_configure()
_IMPL.execution_source_commit = execution_source_commit
_IMPL.execute_attempt = execute_attempt

for _name in _IMPL.__all__:
    globals()[_name] = getattr(_IMPL, _name)
globals().update(
    {
        "execution_source_commit": execution_source_commit,
        "execute_attempt": execute_attempt,
        "finalize_attempt_telemetry": finalize_attempt_telemetry,
        "gzip_file_deterministic": gzip_file_deterministic,
        "ARTIFACT_ROOT": ARTIFACT_ROOT,
        "PAPER": PAPER,
        "frozen": frozen,
    }
)


if __name__ == "__main__":
    raise SystemExit(_IMPL.main())
