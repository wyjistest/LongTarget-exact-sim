#!/usr/bin/env python3
"""Freeze or execute the single authorized Phase 4 infrastructure repair."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import freeze_fresh_holdout as frozen
    from . import run_fresh_holdout as base
except ImportError:  # pragma: no cover
    import freeze_fresh_holdout as frozen  # type: ignore[no-redef]
    import run_fresh_holdout as base  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
ORIGINAL_ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout"
REPAIR_ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout-repair1"
ORIGINAL_ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_attempt_plan.tsv"
REPAIR_ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_repair1_attempt_plan.tsv"
REPAIR_ATTEMPT_CHECKSUM_PATH = PAPER / "fresh_holdout_repair1_attempt_plan.sha256"
REPAIR_PLAN_PATH = PAPER / "fresh_holdout_repair1_plan.json"
INCIDENT_PATH = PAPER / "fresh_holdout_infrastructure_incident.json"
REPAIR_ANALYZER_PATH = ROOT / "reproduce/biological_topk/analyze_fresh_holdout_repair1.py"
PHASE4_ALLOWLIST_PATH = PAPER / "phase_4_change_allowlist.txt"
PHASE3_COMMIT = "ca6410c1fc986e91fd855a43ed71dfeb5940f68f"
REPAIR_FIELDS = (
    *frozen.ATTEMPT_FIELDS,
    "supersedes_attempt_id",
    "repair_epoch",
    "repair_reason",
    "telemetry_storage_policy",
)
TELEMETRY_STORAGE_POLICY = "validate_raw_then_lossless_gzip_mtime0"
TELEMETRY_RAW_RESERVATION_BYTES = 1536 * 1024**2


class RepairError(RuntimeError):
    """Raised for a repair-plan or execution failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RepairError(message)


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_tsv(path: Path, fields: Sequence[str]) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == tuple(fields), f"TSV schema drift: {path}")
        rows = list(reader)
    require(all(tuple(row) == tuple(fields) and None not in row for row in rows), f"malformed TSV: {path}")
    return rows


def render_tsv(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


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


def directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for child in path.rglob("*"):
        require(not child.is_symlink(), f"artifact tree contains a symlink: {child}")
        if child.is_file():
            total += child.stat().st_size
    return total


def artifact_inventory(path: Path) -> list[dict[str, Any]]:
    rows = []
    for child in sorted(path.rglob("*")):
        require(not child.is_symlink(), f"incident artifact is a symlink: {child}")
        if child.is_file():
            rows.append(
                {
                    "path": child.relative_to(ROOT).as_posix(),
                    "size_bytes": child.stat().st_size,
                    "sha256": sha256_file(child),
                }
            )
    return rows


def build_incident() -> dict[str, Any]:
    summary_path = ORIGINAL_ARTIFACT_ROOT / "run-summary.json"
    summary = read_json(summary_path)
    require(summary["terminal_attempt_count"] == 3, "superseded epoch terminal-attempt count drift")
    require(summary["successful_attempt_count"] == 1, "superseded epoch success count drift")
    require(summary["technical_failure_count"] == 2, "superseded epoch failure count drift")
    require(summary["comparison_started"] is False, "comparison started in superseded epoch")
    receipts = []
    for path in sorted(ORIGINAL_ARTIFACT_ROOT.glob("*/attempt-complete.json")):
        value = read_json(path)
        receipts.append(
            {
                "attempt_id": value["attempt_id"],
                "status": value["status"],
                "failure_reason": value["failure_reason"],
                "wall_seconds": value["wall_seconds"],
                "comparison_started": value["comparison_started"],
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
        )
    require(len(receipts) == 3, "superseded epoch receipt count drift")
    telemetry = []
    for path in sorted(ORIGINAL_ARTIFACT_ROOT.glob("*/telemetry.json")):
        telemetry.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    require(len(telemetry) == 2, "superseded epoch telemetry evidence drift")
    inventory = artifact_inventory(ORIGINAL_ARTIFACT_ROOT)
    return {
        "schema_version": 1,
        "phase": 4,
        "incident_kind": "fixed_storage_budget_projection_underestimate_and_preexecution_status_parser",
        "status": "superseded_epoch_retained_repair1_authorized",
        "preexecution_authorization_incident": {
            "scientific_output_created": False,
            "artifact_root_created": False,
            "failure": "first unstaged porcelain status path lost its leading character after strip",
            "resolution": "stage Phase 4 start-state paths before formal execution",
            "scientific_retry": False,
        },
        "superseded_execution_epoch": 0,
        "superseded_artifact_root": ORIGINAL_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
        "superseded_artifact_bytes": sum(row["size_bytes"] for row in inventory),
        "superseded_artifact_file_count": len(inventory),
        "superseded_artifact_inventory_sha256": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
        "run_summary_path": summary_path.relative_to(ROOT).as_posix(),
        "run_summary_sha256": sha256_file(summary_path),
        "terminal_attempt_receipts": receipts,
        "large_candidate_telemetry_observations": telemetry,
        "planned_attempt_count": 368,
        "terminal_attempt_count": 3,
        "successful_attempt_count": 1,
        "budget_stop_technical_failure_count": 2,
        "comparison_started": False,
        "fixed_storage_quota_bytes": frozen.MAX_STORAGE_BYTES,
        "phase3_projected_storage_upper_95_bytes": int(
            read_json(frozen.RESOURCE_DECISION_PATH)["projected_artifact_storage_bytes_upper_95"]
        ),
        "stop_reason": "observed uncompressed large-workload telemetry growth would exhaust the fixed quota before panel completion",
        "old_evidence_retention": "all terminal receipts, partial-derived failures, raw telemetry, inputs, outputs, logs, and snapshot retained byte-for-byte",
        "repair_epoch_authorized": 1,
        "repair_epoch_limit": 1,
        "repair_scope": [
            "full rerun of every frozen attempt under new attempt IDs and a new artifact root",
            "robust NUL-delimited git-status parsing",
            "lossless deterministic gzip of raw telemetry after telemetry validation",
        ],
        "scientific_input_changed": False,
        "scientific_contract_changed": False,
        "runtime_binary_changed": False,
        "panel_or_attempt_order_changed": False,
        "automatic_retry_used": False,
    }


def transformed_attempts(original: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    runner_sha = sha256_file(Path(__file__).resolve())
    analyzer_sha = sha256_file(REPAIR_ANALYZER_PATH)
    rows: list[dict[str, Any]] = []
    for source in original:
        row: dict[str, Any] = dict(source)
        original_attempt_id = source["attempt_id"]
        row["attempt_id"] = f"r1_{original_attempt_id}"
        row["validation_instance_id"] = f"r1_{source['validation_instance_id']}"
        row["artifact_root"] = (
            REPAIR_ARTIFACT_ROOT / row["attempt_id"]
        ).relative_to(ROOT).as_posix()
        row["runner_path"] = Path(__file__).resolve().relative_to(ROOT).as_posix()
        row["runner_sha256"] = runner_sha
        row["analyzer_path"] = REPAIR_ANALYZER_PATH.relative_to(ROOT).as_posix()
        row["analyzer_sha256"] = analyzer_sha
        row["status"] = "repair1_preregistered_not_run"
        row["supersedes_attempt_id"] = original_attempt_id
        row["repair_epoch"] = 1
        row["repair_reason"] = "fixed_storage_budget_telemetry_representation_only"
        row["telemetry_storage_policy"] = TELEMETRY_STORAGE_POLICY
        rows.append(row)
    require(len(rows) == 368, "repair plan must rerun all 368 attempts")
    require([int(row["execution_index"]) for row in rows] == list(range(1, 369)), "repair execution order drift")
    return rows


def build_repair_artifacts() -> dict[Path, bytes]:
    original = read_tsv(ORIGINAL_ATTEMPT_PLAN_PATH, frozen.ATTEMPT_FIELDS)
    incident = build_incident()
    incident_bytes = canonical_json_bytes(incident)
    rows = transformed_attempts(original)
    attempts_bytes = render_tsv(REPAIR_FIELDS, rows)
    attempts_sha = hashlib.sha256(attempts_bytes).hexdigest()
    plan = {
        "schema_version": 1,
        "phase": 4,
        "status": "repair1_frozen_not_run",
        "repair_epoch": 1,
        "repair_epoch_limit": 1,
        "repair_scope": "infrastructure_and_lossless_artifact_representation_only",
        "incident_path": INCIDENT_PATH.relative_to(ROOT).as_posix(),
        "incident_sha256": hashlib.sha256(incident_bytes).hexdigest(),
        "original_manifest_path": frozen.MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "original_manifest_sha256": sha256_file(frozen.MANIFEST_PATH),
        "original_attempt_plan_path": ORIGINAL_ATTEMPT_PLAN_PATH.relative_to(ROOT).as_posix(),
        "original_attempt_plan_sha256": sha256_file(ORIGINAL_ATTEMPT_PLAN_PATH),
        "repair_attempt_plan_path": REPAIR_ATTEMPT_PLAN_PATH.relative_to(ROOT).as_posix(),
        "repair_attempt_plan_sha256": attempts_sha,
        "original_artifact_root": ORIGINAL_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
        "repair_artifact_root": REPAIR_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
        "original_evidence_retained": True,
        "full_panel_rerun": True,
        "planned_primary_workloads": 178,
        "planned_validation_instances": 184,
        "planned_attempts": 368,
        "telemetry_storage_policy": TELEMETRY_STORAGE_POLICY,
        "telemetry_raw_reservation_bytes": TELEMETRY_RAW_RESERVATION_BYTES,
        "fixed_storage_quota_bytes": frozen.MAX_STORAGE_BYTES,
        "quota_includes_original_and_repair_roots": True,
        "runner_path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "analyzer_path": REPAIR_ANALYZER_PATH.relative_to(ROOT).as_posix(),
        "analyzer_sha256": sha256_file(REPAIR_ANALYZER_PATH),
        "authority_binary_sha256": frozen.AUTHORITY_BINARY_SHA256,
        "candidate_binary_sha256": frozen.CANDIDATE_BINARY_SHA256,
        "parameter_bundle_sha256": frozen.PARAMETER_BUNDLE_SHA256,
        "scientific_input_changed": False,
        "scientific_contract_changed": False,
        "runtime_binary_changed": False,
        "panel_or_attempt_order_changed": False,
        "exact_execution_command": [
            "python3",
            Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "--execute",
        ],
        "exact_analysis_command": [
            "python3",
            REPAIR_ANALYZER_PATH.relative_to(ROOT).as_posix(),
            "--analyze",
            "--artifact-root",
            REPAIR_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
        ],
    }
    return {
        INCIDENT_PATH: incident_bytes,
        REPAIR_ATTEMPT_PLAN_PATH: attempts_bytes,
        REPAIR_ATTEMPT_CHECKSUM_PATH: f"{attempts_sha}  {REPAIR_ATTEMPT_PLAN_PATH.name}\n".encode("ascii"),
        REPAIR_PLAN_PATH: canonical_json_bytes(plan),
    }


def validate_repair_plan() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any], base.FrozenInputs]:
    manifest, original, original_plan, inputs = base.validate_frozen_plan()
    del original_plan
    expected = build_repair_artifacts()
    for path, payload in expected.items():
        require(path.is_file() and path.read_bytes() == payload, f"repair freeze artifact drift: {path}")
    rows = read_tsv(REPAIR_ATTEMPT_PLAN_PATH, REPAIR_FIELDS)
    require(len(rows) == len(original) == 368, "repair plan count drift")
    checksum = REPAIR_ATTEMPT_CHECKSUM_PATH.read_text(encoding="ascii").split()
    require(checksum == [sha256_file(REPAIR_ATTEMPT_PLAN_PATH), REPAIR_ATTEMPT_PLAN_PATH.name], "repair plan checksum drift")
    plan = read_json(REPAIR_PLAN_PATH)
    require(plan["repair_epoch"] == plan["repair_epoch_limit"] == 1, "repair epoch limit drift")
    require(plan["full_panel_rerun"] is True and plan["original_evidence_retained"] is True, "repair retention/rerun policy drift")
    identity_fields = (
        "execution_index", "workload_id", "repeat_id", "primary_instance",
        "independent_sample", "arm", "pair_order", "arm_launch_order", "worker_index",
        "query_ordinal_namespace", "query_source_ordinal", "query_sequence_sha256",
        "target_ordinal_namespace", "target_source_ordinal", "target_sequence_sha256",
        "assembly", "target_coordinate_namespace", "query_extraction_recipe_id",
        "target_extraction_recipe_id", "input_pair_digest", "parameter_bundle_sha256",
        "binary_path", "binary_sha256", "gpu_physical_index", "cpu_affinity",
        "timeout_seconds", "retry_policy", "comparison_policy",
    )
    for source, row in zip(original, rows):
        require(row["supersedes_attempt_id"] == source["attempt_id"], "repair superseded attempt mapping drift")
        require(all(row[field] == source[field] for field in identity_fields), f"repair changed frozen attempt: {source['attempt_id']}")
        require(row["attempt_id"] == f"r1_{source['attempt_id']}", "repair attempt ID drift")
        require(row["validation_instance_id"] == f"r1_{source['validation_instance_id']}", "repair validation ID drift")
        require(row["telemetry_storage_policy"] == TELEMETRY_STORAGE_POLICY, "repair telemetry policy drift")
    return manifest, rows, plan, inputs


def load_inputs_for_analysis(manifest: Sequence[Mapping[str, str]]) -> base.FrozenInputs:
    return base.load_inputs(manifest)


def changed_paths() -> set[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))
    entries = completed.stdout.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        require(len(entry) >= 4 and entry[2:3] == b" ", f"cannot parse git status entry: {entry!r}")
        paths.add(entry[3:].decode("utf-8"))
        if entry[:1] in {b"R", b"C"} or entry[1:2] in {b"R", b"C"}:
            require(index < len(entries) and entries[index], "truncated rename status")
            paths.add(entries[index].decode("utf-8"))
            index += 1
    return paths


def execution_source_commit() -> str:
    head = base.git("rev-parse", "HEAD")
    require(head == PHASE3_COMMIT, "repair execution must remain based on the certified Phase 3 commit")
    state = read_json(base.STATE_PATH)
    require(state["phase_status"]["4"] == "active", "repair execution requires Phase 4 active state")
    require(PHASE4_ALLOWLIST_PATH.is_file(), "repair execution requires the Phase 4 allowlist")
    allowed = {line.strip() for line in PHASE4_ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}
    require(changed_paths() <= allowed, f"repair execution has out-of-allowlist changes: {sorted(changed_paths() - allowed)}")
    plan = read_json(REPAIR_PLAN_PATH)
    require(plan["runner_sha256"] == sha256_file(Path(__file__).resolve()), "repair runner changed after plan freeze")
    require(plan["analyzer_sha256"] == sha256_file(REPAIR_ANALYZER_PATH), "repair analyzer changed after plan freeze")
    return head


def initialize_snapshot(source_commit: str, attempts: Sequence[Mapping[str, str]]) -> Path:
    snapshot = REPAIR_ARTIFACT_ROOT / "execution-snapshot"
    if snapshot.is_dir():
        metadata = read_json(snapshot / "snapshot.json")
        require(metadata["source_commit"] == source_commit, "repair snapshot source commit drift")
        require(metadata["repair_attempt_plan_sha256"] == sha256_file(REPAIR_ATTEMPT_PLAN_PATH), "repair snapshot plan drift")
        for relative, identity in metadata["files"].items():
            path = snapshot / relative
            require(path.stat().st_size == identity["size_bytes"] and sha256_file(path) == identity["sha256"], f"repair snapshot file drift: {relative}")
        return snapshot
    require(not REPAIR_ARTIFACT_ROOT.exists(), "repair artifact root exists without a complete snapshot")
    REPAIR_ARTIFACT_ROOT.mkdir(parents=True)
    partial = REPAIR_ARTIFACT_ROOT / f".execution-snapshot.partial.{os.getpid()}"
    partial.mkdir()
    sources = (
        frozen.MANIFEST_PATH,
        ORIGINAL_ATTEMPT_PLAN_PATH,
        REPAIR_ATTEMPT_PLAN_PATH,
        REPAIR_ATTEMPT_CHECKSUM_PATH,
        REPAIR_PLAN_PATH,
        INCIDENT_PATH,
        frozen.RUNTIME_RECEIPT_PATH,
        frozen.CONTRACT_PATH,
        frozen.COMPARATOR_PATH,
        ROOT / "reproduce/biological_topk/run_fresh_holdout.py",
        Path(__file__).resolve(),
        REPAIR_ANALYZER_PATH,
        frozen.AUTHORITY_BINARY_PATH,
        frozen.CANDIDATE_BINARY_PATH,
    )
    names = [path.name for path in sources]
    require(len(names) == len(set(names)), "repair snapshot basenames collide")
    for source in sources:
        shutil.copy2(source, partial / source.name)
    files = {
        path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in sorted(partial.iterdir())
        if path.is_file()
    }
    base.atomic_json(
        partial / "snapshot.json",
        {
            "schema_version": 1,
            "source_commit": source_commit,
            "repair_epoch": 1,
            "repair_attempt_plan_sha256": sha256_file(REPAIR_ATTEMPT_PLAN_PATH),
            "incident_sha256": sha256_file(INCIDENT_PATH),
            "attempt_count": len(attempts),
            "gpu_inventory": base.visible_gpu_inventory(),
            "files": files,
            "created_utc": base.utc_now(),
        },
    )
    os.replace(partial, snapshot)
    return snapshot


def gzip_telemetry(destination: Path) -> None:
    raw = destination / "telemetry.json"
    if not raw.is_file():
        return
    receipt_path = destination / "attempt-complete.json"
    receipt = read_json(receipt_path)
    raw_size = raw.stat().st_size
    raw_sha = sha256_file(raw)
    compressed = destination / "attempt-telemetry.tsv.gz"
    temporary = destination / ".attempt-telemetry.tsv.gz.tmp"
    with raw.open("rb") as source, temporary.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=6, fileobj=sink, mtime=0) as encoder:
            shutil.copyfileobj(source, encoder, length=1024 * 1024)
        sink.flush()
        os.fsync(sink.fileno())
    os.replace(temporary, compressed)
    digest = hashlib.sha256()
    size = 0
    with gzip.open(compressed, "rb") as decoded:
        for block in iter(lambda: decoded.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    require(size == raw_size and digest.hexdigest() == raw_sha, "lossless telemetry gzip verification failed")
    raw.unlink()
    receipt["telemetry_storage_policy"] = TELEMETRY_STORAGE_POLICY
    receipt["telemetry_uncompressed_path"] = "telemetry.json"
    receipt["telemetry_uncompressed_size_bytes"] = raw_size
    receipt["telemetry_uncompressed_sha256"] = raw_sha
    receipt["telemetry_compressed_path"] = compressed.name
    receipt["telemetry_compressed_size_bytes"] = compressed.stat().st_size
    receipt["telemetry_compressed_sha256"] = sha256_file(compressed)
    manifest_bytes = base.artifact_manifest(destination)
    base.atomic_write(destination / "artifact-manifest.tsv", manifest_bytes)
    manifest_sha = sha256_file(destination / "artifact-manifest.tsv")
    base.atomic_write(destination / "artifact-manifest.sha256", f"{manifest_sha}  artifact-manifest.tsv\n".encode("ascii"))
    receipt["artifact_manifest_sha256"] = manifest_sha
    base.atomic_json(receipt_path, receipt)


ORIGINAL_EXECUTE_ATTEMPT = base.execute_attempt


def execute_attempt(
    row: Mapping[str, str],
    workload: Mapping[str, str],
    inputs: base.FrozenInputs,
    snapshot: Path,
    source_commit: str,
) -> dict[str, Any]:
    retained = directory_bytes(ORIGINAL_ARTIFACT_ROOT) + directory_bytes(REPAIR_ARTIFACT_ROOT)
    if row["arm"] == "G":
        require(
            retained + TELEMETRY_RAW_RESERVATION_BYTES <= frozen.MAX_STORAGE_BYTES,
            "fixed storage quota cannot reserve one raw telemetry attempt",
        )
    caught: Exception | None = None
    result: dict[str, Any] | None = None
    try:
        result = ORIGINAL_EXECUTE_ATTEMPT(row, workload, inputs, snapshot, source_commit)
    except Exception as error:  # Preserve and compress a terminal failure before propagating it.
        caught = error
    destination = ROOT / row["artifact_root"]
    if destination.is_dir():
        gzip_telemetry(destination)
    retained = directory_bytes(ORIGINAL_ARTIFACT_ROOT) + directory_bytes(REPAIR_ARTIFACT_ROOT)
    require(retained <= frozen.MAX_STORAGE_BYTES, "fixed artifact-storage quota reached")
    if caught is not None:
        raise caught
    require(result is not None, "repair attempt returned no receipt")
    return base.validate_completed_attempt(destination, row)


def execute() -> dict[str, Any]:
    manifest, attempts, plan, inputs = validate_repair_plan()
    del plan
    original_root = base.ARTIFACT_ROOT
    original_source = base.execution_source_commit
    original_snapshot = base.initialize_snapshot
    original_attempt = base.execute_attempt
    try:
        base.ARTIFACT_ROOT = REPAIR_ARTIFACT_ROOT
        base.execution_source_commit = execution_source_commit
        base.initialize_snapshot = initialize_snapshot
        base.execute_attempt = execute_attempt
        return base.execute(attempts, manifest, inputs)
    finally:
        base.ARTIFACT_ROOT = original_root
        base.execution_source_commit = original_source
        base.initialize_snapshot = original_snapshot
        base.execute_attempt = original_attempt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze-plan", action="store_true")
    modes.add_argument("--check-plan", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.freeze_plan:
            payloads = build_repair_artifacts()
            for path, payload in payloads.items():
                atomic_write(path, payload)
            print(f"wrote {len(payloads)} repair1 freeze artifacts")
            return 0
        manifest, attempts, plan, _ = validate_repair_plan()
        if args.check_plan:
            print("biological Top-K repair1 plan reproduces byte-for-byte")
            return 0
        if args.preflight:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "repair1_preflight_pass",
                        "repair_epoch": plan["repair_epoch"],
                        "full_panel_rerun": True,
                        "primary_workloads": len(manifest),
                        "attempts": len(attempts),
                        "original_evidence_bytes": directory_bytes(ORIGINAL_ARTIFACT_ROOT),
                        "fixed_storage_quota_bytes": frozen.MAX_STORAGE_BYTES,
                        "repair_artifact_root_exists": REPAIR_ARTIFACT_ROOT.exists(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        result = execute()
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (
        RepairError,
        base.RunnerError,
        frozen.FreezeError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"biological Top-K repair1 runner failed: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
