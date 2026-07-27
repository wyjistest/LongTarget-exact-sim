#!/usr/bin/env python3
"""Execute frozen canonical-hybrid-v2 regression, holdout, and pilot plans."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from canonical_hybrid_v2_telemetry import validate_attempt as validate_telemetry  # noqa: E402
from collect_fasim_gasal2_paper_run import max_rss_kb  # noqa: E402
from run_fasim_gasal2_paper_benchmarks import GpuSampler  # noqa: E402


RUNNER_PATH = Path(__file__).resolve()
RUNTIME_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_runtime.json"
CANONICAL_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2"
PLAN_PATHS = {
    "regression": ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_plan.tsv",
    "fresh-holdout": ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan.tsv",
    "performance-pilot": ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_plan.tsv",
}
PLAN_CHECKSUM_PATHS = {stage: path.with_suffix(".sha256") for stage, path in PLAN_PATHS.items()}
PLAN_FIELDS = (
    "attempt_id",
    "stage",
    "validation_id",
    "arm",
    "order",
    "repeat_id",
    "query_id",
    "target_id",
    "query_path",
    "target_path",
    "query_sha256",
    "target_sha256",
    "authority_reference_kind",
    "authority_reference",
    "authority_reference_sha256",
    "runtime_commit",
    "hybrid_binary_sha256",
    "authority_binary_sha256",
    "runner_commit",
    "runner_sha256",
    "runtime_receipt_sha256",
    "backend_timeout_seconds",
    "gpu_physical_index",
    "contract",
    "claim_role",
    "promotion_eligible",
    "formal_source_data",
    "retry_policy",
    "expected_artifact_root",
    "status",
)
COMPARATOR_METRICS = (
    "baseline_rows",
    "candidate_rows",
    "full_missing_rows",
    "full_extra_rows",
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "all_three_top5_equal",
    "boundary_ties_equal",
)
HYBRID_ENVIRONMENT = {
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
AUTHORITY_ENVIRONMENT = {"FASIM_OUTPUT_MODE": "tfosorted", "FASIM_VERBOSE": "0"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
SNAPSHOT_SUPPORT_FILES = (
    RUNNER_PATH,
    ROOT / "scripts/canonical_hybrid_v2_telemetry.py",
    ROOT / "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json",
    RUNTIME_RECEIPT_PATH,
)
COMPARATOR_SUPPORT_FILES = (
    ROOT / "scripts/compare_fasim_lite_offline_cluster_topk.py",
    ROOT / "scripts/fasim_tfo_archive.py",
)


class RunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolPaths:
    hybrid_binary: Path = ROOT / "fasim_longtarget_gasal2"
    authority_binary: Path = ROOT / "fasim_longtarget_x86"
    comparator: Path = ROOT / "scripts/compare_fasim_segmented_contract.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError(message)


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


def canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def read_tsv(path: Path, fieldnames: Sequence[str]) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == tuple(fieldnames), f"TSV schema drift: {path}")
        rows = list(reader)
    for row in rows:
        require(tuple(row) == tuple(fieldnames), f"malformed TSV row: {path}")
    return rows


def atomic_bytes(path: Path, payload: bytes) -> None:
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


def atomic_json(path: Path, payload: object) -> None:
    atomic_bytes(path, canonical_json_bytes(payload))


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="raise"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def resolve_repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    require(path == ROOT or ROOT in path.parents, f"path escapes repository: {value}")
    return path


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


def clean_head() -> str:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all", "--ignored=no")
    require(not status, f"formal rescue execution requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def validate_artifact_root(stage: str, stage_root: Path) -> None:
    expected = Path(os.path.abspath(CANONICAL_ARTIFACT_ROOT / stage))
    candidate = Path(os.path.abspath(stage_root))
    require(candidate == expected, "execution requires the canonical stage artifact root")
    current = ROOT
    for part in candidate.relative_to(ROOT).parts:
        current = current / part
        require(not current.is_symlink(), f"artifact root component is a symlink: {current}")


def read_runtime_receipt(path: Path = RUNTIME_RECEIPT_PATH) -> dict[str, object]:
    require(path.is_file() and not path.is_symlink(), "runtime epoch receipt is missing or unsafe")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema_version") == 1, "runtime receipt schema drift")
    require(receipt.get("runtime_epoch") == 1, "canonical hybrid runtime epoch drift")
    require(receipt.get("contract") == "canonical-hybrid-v2", "runtime contract drift")
    require(receipt.get("complete_cpu_authority_inside_hybrid") is False, "hybrid embeds authority")
    for field in ("runtime_commit", "runner_commit"):
        require(
            isinstance(receipt.get(field), str)
            and COMMIT_PATTERN.fullmatch(str(receipt[field])) is not None,
            f"invalid runtime receipt {field}",
        )
    digest_paths = {
        "runner_sha256": RUNNER_PATH,
        "telemetry_validator_sha256": ROOT / "scripts/canonical_hybrid_v2_telemetry.py",
        "telemetry_schema_sha256": ROOT / "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json",
        "comparator_sha256": ROOT / "scripts/compare_fasim_segmented_contract.py",
    }
    for field, source in digest_paths.items():
        require(is_sha256(receipt.get(field)), f"invalid runtime receipt {field}")
        require(sha256_file(source) == receipt[field], f"runtime receipt {field} drift")
    comparator_dependencies = receipt.get("comparator_dependency_sha256")
    require(isinstance(comparator_dependencies, dict), "missing comparator dependency identity")
    for source in COMPARATOR_SUPPORT_FILES:
        relative = source.relative_to(ROOT).as_posix()
        require(
            comparator_dependencies.get(relative) == sha256_file(source),
            f"runtime comparator dependency drift: {relative}",
        )
    for field in ("hybrid_binary_sha256", "authority_binary_sha256"):
        require(is_sha256(receipt.get(field)), f"invalid runtime receipt {field}")
    for field in ("hybrid_build_commands", "authority_build_commands"):
        commands = receipt.get(field)
        require(
            isinstance(commands, list)
            and commands
            and all(
                isinstance(command, list)
                and command
                and all(isinstance(value, str) and value for value in command)
                for command in commands
            ),
            f"missing or malformed {field}",
        )
    return receipt


def read_plan(stage: str) -> list[dict[str, str]]:
    path = PLAN_PATHS[stage]
    checksum_path = PLAN_CHECKSUM_PATHS[stage]
    require(path.is_file() and not path.is_symlink(), f"missing frozen {stage} plan")
    require(checksum_path.is_file() and not checksum_path.is_symlink(), f"missing {stage} checksum")
    checksum_fields = checksum_path.read_text(encoding="utf-8").strip().split()
    require(len(checksum_fields) == 2 and checksum_fields[1] == path.name, "plan checksum format drift")
    require(sha256_file(path) == checksum_fields[0], f"{stage} plan digest drift")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == PLAN_FIELDS, f"{stage} plan schema drift")
        rows = list(reader)
    require(rows, f"empty {stage} plan")
    ids: set[str] = set()
    orders: set[int] = set()
    runtime = read_runtime_receipt()
    runtime_receipt_sha256 = sha256_file(RUNTIME_RECEIPT_PATH)
    for row in rows:
        require(tuple(row) == PLAN_FIELDS, "malformed plan row")
        require(row["stage"] == stage, "plan stage drift")
        require(row["attempt_id"] not in ids, "duplicate plan attempt ID")
        ids.add(row["attempt_id"])
        try:
            order = int(row["order"])
            timeout_seconds = int(row["backend_timeout_seconds"])
        except ValueError as exc:
            raise RunnerError("invalid plan order or timeout") from exc
        require(order > 0 and order not in orders, "invalid or duplicate plan order")
        orders.add(order)
        require(timeout_seconds > 0, "backend timeout must be positive")
        require(row["arm"] in ("A", "H"), "unknown rescue arm")
        require(row["retry_policy"] == "none", "retry policy drift")
        require(row["status"] == "preregistered_not_run", "plan status drift")
        require(row["contract"] == "all-ranked-top5-canonical-row-v2", "contract drift")
        require(row["runtime_commit"] == runtime["runtime_commit"], "runtime commit drift")
        require(row["hybrid_binary_sha256"] == runtime["hybrid_binary_sha256"], "hybrid binary drift")
        require(row["authority_binary_sha256"] == runtime["authority_binary_sha256"], "authority binary drift")
        require(row["runner_commit"] == runtime["runner_commit"], "runner commit drift")
        require(row["runtime_receipt_sha256"] == runtime_receipt_sha256, "runtime receipt digest drift")
        require(row["runner_sha256"] == sha256_file(RUNNER_PATH), "runner digest drift")
        require(row["runner_sha256"] == runtime["runner_sha256"], "runtime/plan runner digest drift")
        require(row["promotion_eligible"] in ("0", "1"), "invalid promotion flag")
        require(row["formal_source_data"] in ("0", "1"), "invalid source-data flag")
        query = resolve_repo_path(row["query_path"])
        target = resolve_repo_path(row["target_path"])
        require(query.is_file() and not query.is_symlink(), "unsafe query input")
        require(target.is_file() and not target.is_symlink(), "unsafe target input")
        require(sha256_file(query) == row["query_sha256"], "query digest drift")
        require(sha256_file(target) == row["target_sha256"], "target digest drift")
        require(row["expected_artifact_root"] == f"{stage}/{row['attempt_id']}", "artifact root drift")
        if row["arm"] == "H":
            require(row["gpu_physical_index"] in ("0", "1"), "hybrid GPU assignment drift")
            require(row["authority_reference_kind"] in ("frozen_file", "stage_attempt"), "missing authority reference")
            if row["authority_reference_kind"] == "stage_attempt":
                require(
                    row["authority_reference_sha256"] == "derived_from_completed_stage_A_attempt",
                    "stage authority digest policy drift",
                )
            else:
                reference = resolve_repo_path(row["authority_reference"])
                require(reference.is_file() and not reference.is_symlink(), "unsafe frozen authority reference")
                require(is_sha256(row["authority_reference_sha256"]), "invalid authority reference digest")
                require(sha256_file(reference) == row["authority_reference_sha256"], "authority reference digest drift")
        else:
            require(row["authority_reference_kind"] == "none", "authority arm has a reference")
            require(row["gpu_physical_index"] == "NA", "authority arm has a GPU assignment")
    require(orders == set(range(1, len(rows) + 1)), "plan orders must be contiguous from one")

    by_id = {row["attempt_id"]: row for row in rows}
    for row in rows:
        if row["authority_reference_kind"] != "stage_attempt":
            continue
        reference = by_id.get(row["authority_reference"])
        require(reference is not None, "stage authority reference is not in the plan")
        require(reference["arm"] == "A", "stage authority reference is not arm A")
        require(reference["validation_id"] == row["validation_id"], "stage authority validation ID drift")
        require(int(reference["order"]) < int(row["order"]), "stage authority must precede hybrid")

    if stage == "regression":
        require(all(row["arm"] == "H" for row in rows), "regression may execute only arm H")
        require(all(row["authority_reference_kind"] == "frozen_file" for row in rows), "regression must use frozen authority")
        require(all(row["promotion_eligible"] == "0" for row in rows), "regression cannot promote v2")
        require(all(row["formal_source_data"] == "0" for row in rows), "regression is not new formal source data")
        require(all(row["claim_role"] == "regression_only" for row in rows), "regression claim role drift")
    return sorted(rows, key=lambda row: int(row["order"]))


def plan_summary(stage: str, rows: list[dict[str, str]]) -> dict[str, object]:
    counts = {arm: sum(row["arm"] == arm for row in rows) for arm in ("A", "H")}
    return {
        "stage": stage,
        "plan_sha256": sha256_file(PLAN_PATHS[stage]),
        "attempt_count": len(rows),
        "arm_counts": counts,
        "formal_source_data_count": sum(row["formal_source_data"] == "1" for row in rows),
        "promotion_eligible_count": sum(row["promotion_eligible"] == "1" for row in rows),
        "retry_policy": "none",
        "artifact_root": str((CANONICAL_ARTIFACT_ROOT / stage).relative_to(ROOT)),
    }


def sanitized_environment(row: dict[str, str], telemetry_path: Path | None) -> tuple[dict[str, str], dict[str, str]]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FASIM_")}
    explicit = dict(HYBRID_ENVIRONMENT if row["arm"] == "H" else AUTHORITY_ENVIRONMENT)
    if row["arm"] == "H":
        require(telemetry_path is not None, "hybrid telemetry path is required")
        explicit["FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH"] = str(telemetry_path)
        explicit["CUDA_VISIBLE_DEVICES"] = row["gpu_physical_index"]
    environment.update(explicit)
    return environment, explicit


def backend_command(binary: Path, target: Path, query: Path, output: Path) -> list[str]:
    return [str(binary), "-f1", str(target), "-f2", str(query), "-r", "0", "-O", str(output)]


def output_file(output_root: Path) -> Path:
    files = sorted(path for path in output_root.iterdir() if path.is_file() and path.name.endswith("TFOsorted"))
    require(len(files) == 1, f"expected one TFOsorted output, found {len(files)}")
    return files[0]


def detect_oom(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(token in lowered for token in ("out of memory", "std::bad_alloc", "cuda_error_memory_allocation"))


def parse_comparator(stdout: str, returncode: int) -> dict[str, object]:
    values: dict[str, int] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name in COMPARATOR_METRICS:
            values[name] = int(value)
    missing = sorted(set(COMPARATOR_METRICS) - set(values))
    require(not missing, f"missing comparator metrics: {', '.join(missing)}")
    require(returncode in (0, 1), "comparator technical failure")
    declared_clean = all(
        values[name] == 1
        for name in (
            "clustered_score_top5_equal",
            "clustered_stability_top5_equal",
            "clustered_nt_top5_equal",
            "all_three_top5_equal",
        )
    )
    return {"returncode": returncode, "declared_contract_clean": declared_clean, "metrics": values}


def validate_snapshot_contents(snapshot: Path) -> dict[str, object]:
    require(snapshot.is_dir() and not snapshot.is_symlink(), "execution snapshot is missing or unsafe")
    metadata_path = snapshot / "snapshot.json"
    require(metadata_path.is_file() and not metadata_path.is_symlink(), "incomplete stage execution snapshot")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    files = metadata.get("files")
    require(isinstance(files, dict) and files, "snapshot file manifest is missing")
    observed_files: set[str] = set()
    for path in sorted(snapshot.rglob("*")):
        require(not path.is_symlink(), f"snapshot contains a symlink: {path}")
        if path.is_file():
            observed_files.add(path.relative_to(snapshot).as_posix())
    require(observed_files == set(files) | {"snapshot.json"}, "snapshot file set drift")
    for relative, identity in files.items():
        require(isinstance(relative, str) and isinstance(identity, dict), "malformed snapshot identity")
        path = snapshot / relative
        require(path.is_file() and not path.is_symlink(), f"missing snapshot file: {relative}")
        require(path.stat().st_size == identity.get("size_bytes"), f"snapshot size drift: {relative}")
        require(sha256_file(path) == identity.get("sha256"), f"snapshot digest drift: {relative}")
    return metadata


def execute_comparator(
    comparator: Path,
    authority_reference: Path,
    candidate: Path,
    details: Path,
    artifact_root: Path,
) -> dict[str, object]:
    snapshot = comparator.parent
    validate_snapshot_contents(snapshot)
    command = [
        sys.executable,
        "-B",
        str(comparator),
        "--baseline",
        str(authority_reference),
        "--candidate",
        str(candidate),
        "--k",
        "5",
        "--cluster-distance",
        "15",
        "--cluster-length",
        "50",
        "--details",
        str(details),
    ]
    environment = {
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    compared = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    atomic_bytes(artifact_root / "comparator-stdout.log", compared.stdout.encode("utf-8"))
    atomic_bytes(artifact_root / "comparator-stderr.log", compared.stderr.encode("utf-8"))
    comparison = {
        "command": command,
        "explicit_environment": environment,
        **parse_comparator(compared.stdout, compared.returncode),
    }
    validate_snapshot_contents(snapshot)
    return comparison


def resolve_authority_reference(
    row: dict[str, str], stage_root: Path
) -> Path | None:
    kind = row["authority_reference_kind"]
    if kind == "none":
        return None
    if kind == "frozen_file":
        path = resolve_repo_path(row["authority_reference"])
    else:
        reference_attempt = stage_root / row["authority_reference"]
        plan_rows = read_tsv(PLAN_PATHS[row["stage"]], PLAN_FIELDS)
        reference_rows = [
            candidate
            for candidate in plan_rows
            if candidate["attempt_id"] == row["authority_reference"]
        ]
        require(len(reference_rows) == 1, "paired authority plan row is missing or duplicated")
        reference_row = reference_rows[0]
        receipt = validate_attempt_receipt(reference_attempt, reference_row)
        path = reference_attempt / receipt["output_path"]
        require(
            receipt["arm"] == "A" and receipt["validation_id"] == row["validation_id"],
            "paired authority identity drift",
        )
    require(path.is_file() and not path.is_symlink(), "unsafe authority reference")
    expected = (
        receipt["output_sha256"]
        if kind == "stage_attempt"
        else row["authority_reference_sha256"]
    )
    require(sha256_file(path) == expected, "authority reference digest drift")
    return path


def artifact_manifest(root: Path) -> tuple[bytes, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"artifact tree contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in (
            "artifact-manifest.tsv",
            "artifact-manifest.sha256",
            "attempt-complete.json",
        ):
            continue
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return tsv_bytes(("path", "size_bytes", "sha256"), rows), len(rows)


def validate_attempt_receipt(
    destination: Path, row: dict[str, str]
) -> dict[str, object]:
    require(destination.is_dir() and not destination.is_symlink(), "attempt directory is missing or unsafe")
    receipt_path = destination / "attempt-complete.json"
    require(receipt_path.is_file() and not receipt_path.is_symlink(), "attempt receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema_version") == 1, "attempt receipt schema drift")
    require(receipt.get("status") == "complete", "attempt receipt is not complete")
    require(receipt.get("attempt_id") == row["attempt_id"], "attempt receipt ID drift")
    require(receipt.get("stage") == row["stage"], "attempt receipt stage drift")
    require(receipt.get("validation_id") == row["validation_id"], "attempt validation ID drift")
    require(receipt.get("arm") == row["arm"], "attempt arm drift")
    require(receipt.get("config_sha256") == canonical_digest(row), "completed attempt config drift")
    require(receipt.get("plan_sha256") == sha256_file(PLAN_PATHS[row["stage"]]), "attempt plan digest drift")
    require(
        receipt.get("runtime_receipt_sha256") == sha256_file(RUNTIME_RECEIPT_PATH),
        "attempt runtime receipt digest drift",
    )
    require(receipt.get("runtime_commit") == row["runtime_commit"], "attempt runtime commit drift")
    expected_binary_sha = (
        row["hybrid_binary_sha256"] if row["arm"] == "H" else row["authority_binary_sha256"]
    )
    require(receipt.get("binary_sha256") == expected_binary_sha, "attempt binary digest drift")
    require(receipt.get("retry_policy") == "none", "attempt retry policy drift")
    require(receipt.get("replacement_retry_allowed") is False, "replacement retry was enabled")

    manifest_path = destination / "artifact-manifest.tsv"
    checksum_path = destination / "artifact-manifest.sha256"
    require(manifest_path.is_file() and not manifest_path.is_symlink(), "attempt manifest is missing")
    require(checksum_path.is_file() and not checksum_path.is_symlink(), "attempt manifest checksum is missing")
    manifest_sha256 = sha256_file(manifest_path)
    require(receipt.get("artifact_manifest_sha256") == manifest_sha256, "artifact manifest digest drift")
    require(
        checksum_path.read_text(encoding="ascii").split()
        == [manifest_sha256, "artifact-manifest.tsv"],
        "artifact manifest checksum drift",
    )
    manifest_rows = read_tsv(manifest_path, ("path", "size_bytes", "sha256"))
    require(len(manifest_rows) == receipt.get("artifact_count"), "artifact count drift")
    expected_files = {
        manifest_path.relative_to(destination).as_posix(),
        checksum_path.relative_to(destination).as_posix(),
        receipt_path.relative_to(destination).as_posix(),
    } | {item["path"] for item in manifest_rows}
    observed_files: set[str] = set()
    for artifact in sorted(destination.rglob("*")):
        require(not artifact.is_symlink(), f"attempt artifact is a symlink: {artifact}")
        if artifact.is_file():
            observed_files.add(artifact.relative_to(destination).as_posix())
    require(observed_files == expected_files, "attempt artifact file set drift")
    for item in manifest_rows:
        artifact = destination / item["path"]
        require(artifact.is_file() and not artifact.is_symlink(), f"missing artifact: {item['path']}")
        require(artifact.stat().st_size == int(item["size_bytes"]), f"artifact size drift: {item['path']}")
        require(sha256_file(artifact) == item["sha256"], f"artifact digest drift: {item['path']}")

    output = destination / str(receipt.get("output_path", ""))
    require(output.is_file() and not output.is_symlink(), "completed output is missing")
    require(sha256_file(output) == receipt.get("output_sha256"), "completed output digest drift")
    execution = receipt.get("execution")
    require(isinstance(execution, dict), "attempt execution receipt is missing")
    require(execution.get("returncode") == 0, "completed attempt has a nonzero return code")
    require(execution.get("timed_out") is False, "completed attempt timed out")
    require(execution.get("oom_detected") is False, "completed attempt reports OOM")
    if row["arm"] == "H":
        telemetry = receipt.get("telemetry_summary")
        require(isinstance(telemetry, dict), "hybrid telemetry summary is missing")
        require(telemetry.get("fallbacks") == 0, "hybrid attempt used fallback")
        require(
            telemetry.get("selected_attempts") == telemetry.get("cpu_traceback_calls"),
            "hybrid selected/CPU traceback count drift",
        )
        require(receipt.get("complete_cpu_authority_inside_hybrid") is False, "hybrid embeds authority")
        comparison = receipt.get("comparison")
        require(isinstance(comparison, dict), "hybrid authority comparison is missing")
        require(comparison.get("returncode") in (0, 1), "invalid comparator return code")
    else:
        require(receipt.get("telemetry_summary") is None, "authority attempt has hybrid telemetry")
    return receipt


def run_process(
    command: list[str],
    environment: dict[str, str],
    run_root: Path,
    timeout_seconds: int,
    gpu_physical_index: int | None,
    sampler_factory=GpuSampler,
) -> dict[str, object]:
    time_path = run_root / "time.txt"
    gpu_path = run_root / "gpu-memory.csv"
    timed_command = command
    if Path("/usr/bin/time").is_file():
        timed_command = ["/usr/bin/time", "-v", "-o", str(time_path), *command]
    else:
        atomic_bytes(time_path, b"")
    sampler = sampler_factory(gpu_path) if gpu_physical_index is not None else None
    if sampler is None:
        atomic_bytes(gpu_path, b"")
    else:
        sampler.start()
    started_utc = utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        timed_command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    finally:
        if sampler is not None:
            sampler.stop()
    wall_seconds = time.perf_counter() - started
    atomic_bytes(run_root / "stdout.log", stdout.encode("utf-8"))
    atomic_bytes(run_root / "stderr.log", stderr.encode("utf-8"))
    resources = gpu_metrics_for_index(gpu_path, gpu_physical_index)
    resources["max_rss_kib"] = max_rss_kb(time_path) if time_path.stat().st_size else None
    return {
        "command": command,
        "timed_command": timed_command,
        "returncode": 124 if timed_out else process.returncode,
        "timed_out": timed_out,
        "oom_detected": detect_oom(stderr),
        "wall_seconds": wall_seconds,
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "resources": resources,
        "stdout": stdout,
        "stderr": stderr,
    }


def gpu_metrics_for_index(path: Path, gpu_physical_index: int | None) -> dict[str, object]:
    if gpu_physical_index is None:
        return {
            "gpu_measurement_status": "not_applicable",
            "gpu_sample_count": 0,
            "gpu_memory_peak_mib": None,
            "gpu_utilization_peak_percent": None,
            "gpu_temperature_peak_c": None,
            "gpu_power_peak_w": None,
            "gpu_sm_clock_peak_mhz": None,
        }
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["measurement_status"] == "available"
            and row["gpu_index"] == str(gpu_physical_index)
        ]
    if not rows:
        return {
            "gpu_measurement_status": "unavailable",
            "gpu_sample_count": 0,
            "gpu_memory_peak_mib": None,
            "gpu_utilization_peak_percent": None,
            "gpu_temperature_peak_c": None,
            "gpu_power_peak_w": None,
            "gpu_sm_clock_peak_mhz": None,
        }
    def peak(field: str) -> float:
        return max(float(row[field]) for row in rows)

    return {
        "gpu_measurement_status": "available",
        "gpu_sample_count": len(rows),
        "gpu_memory_peak_mib": peak("memory_used_mib"),
        "gpu_utilization_peak_percent": peak("utilization_gpu_percent"),
        "gpu_temperature_peak_c": peak("temperature_gpu_c"),
        "gpu_power_peak_w": peak("power_draw_w"),
        "gpu_sm_clock_peak_mhz": peak("clocks_sm_mhz"),
    }


def execute_attempt(
    row: dict[str, str],
    stage_root: Path,
    tools: ToolPaths,
    resume: bool,
    sampler_factory=GpuSampler,
) -> dict[str, object]:
    destination = stage_root / row["attempt_id"]
    receipt_path = destination / "attempt-complete.json"
    if destination.exists():
        require(resume, f"attempt already exists; use --resume: {destination}")
        require(receipt_path.is_file(), f"failed or partial attempt cannot be retried: {destination}")
        receipt = validate_attempt_receipt(destination, row)
        return {"status": "reused", "receipt": receipt}
    stale = list(stage_root.glob(f".{row['attempt_id']}.partial.*"))
    require(not stale, f"stale failed attempt requires manual adjudication: {row['attempt_id']}")
    partial = stage_root / f".{row['attempt_id']}.partial.{os.getpid()}"
    partial.mkdir(parents=True, exist_ok=False)
    atomic_json(partial / "attempt-config.json", {"schema_version": 1, "config_sha256": canonical_digest(row), **row})
    inputs = partial / "inputs"
    inputs.mkdir()
    query = inputs / "query.fa"
    target = inputs / "target.fa"
    shutil.copy2(resolve_repo_path(row["query_path"]), query)
    shutil.copy2(resolve_repo_path(row["target_path"]), target)
    require(sha256_file(query) == row["query_sha256"], "snapshotted query digest drift")
    require(sha256_file(target) == row["target_sha256"], "snapshotted target digest drift")
    authority_source = resolve_authority_reference(row, stage_root)
    authority_reference = None
    if authority_source is not None:
        authority_reference = inputs / "authority-reference.tfosorted"
        shutil.copy2(authority_source, authority_reference)
        require(
            sha256_file(authority_reference) == sha256_file(authority_source),
            "snapshotted authority digest drift",
        )
    output_root = partial / "output"
    output_root.mkdir()
    telemetry_path = partial / "attempt-telemetry.tsv" if row["arm"] == "H" else None
    environment, explicit_environment = sanitized_environment(row, telemetry_path)
    binary = tools.hybrid_binary if row["arm"] == "H" else tools.authority_binary
    require(binary.is_file() and not binary.is_symlink() and os.access(binary, os.X_OK), "unsafe backend binary")
    expected_binary_sha = row["hybrid_binary_sha256"] if row["arm"] == "H" else row["authority_binary_sha256"]
    require(sha256_file(binary) == expected_binary_sha, "backend binary digest drift")
    command = backend_command(binary, target, query, output_root)
    execution = run_process(
        command,
        environment,
        partial,
        int(row["backend_timeout_seconds"]),
        int(row["gpu_physical_index"]) if row["arm"] == "H" else None,
        sampler_factory=sampler_factory,
    )
    atomic_json(partial / "execution.json", {key: value for key, value in execution.items() if key not in ("stdout", "stderr")})
    if execution["returncode"] != 0 or execution["timed_out"] or execution["oom_detected"]:
        atomic_json(
            partial / "attempt-failure.json",
            {
                "schema_version": 1,
                "attempt_id": row["attempt_id"],
                "returncode": execution["returncode"],
                "timed_out": execution["timed_out"],
                "oom_detected": execution["oom_detected"],
                "replacement_retry_allowed": False,
            },
        )
        raise RunnerError(f"backend attempt failed and was preserved: {row['attempt_id']}")
    output = output_file(output_root)
    telemetry_summary = None
    if row["arm"] == "H":
        require(telemetry_path is not None, "internal telemetry path error")
        telemetry_summary = validate_telemetry(telemetry_path, output, str(execution["stderr"]))
        atomic_json(partial / "telemetry-summary.json", telemetry_summary)
    comparison = None
    if authority_reference is not None:
        details = partial / "comparison-details.tsv"
        comparison = execute_comparator(
            tools.comparator,
            authority_reference,
            output,
            details,
            partial,
        )
        atomic_json(partial / "comparison.json", comparison)
    manifest_payload, artifact_count = artifact_manifest(partial)
    atomic_bytes(partial / "artifact-manifest.tsv", manifest_payload)
    manifest_sha256 = sha256_file(partial / "artifact-manifest.tsv")
    atomic_bytes(
        partial / "artifact-manifest.sha256",
        f"{manifest_sha256}  artifact-manifest.tsv\n".encode("ascii"),
    )
    relative_output = output.relative_to(partial).as_posix()
    receipt = {
        "schema_version": 1,
        "status": "complete",
        "attempt_id": row["attempt_id"],
        "stage": row["stage"],
        "validation_id": row["validation_id"],
        "arm": row["arm"],
        "config_sha256": canonical_digest(row),
        "plan_sha256": sha256_file(PLAN_PATHS[row["stage"]]),
        "runtime_receipt_sha256": sha256_file(RUNTIME_RECEIPT_PATH),
        "runtime_commit": row["runtime_commit"],
        "binary_sha256": expected_binary_sha,
        "explicit_environment": explicit_environment,
        "complete_cpu_authority_inside_hybrid": False if row["arm"] == "H" else None,
        "output_path": relative_output,
        "output_sha256": sha256_file(output),
        "output_rows": len(output.read_text(encoding="utf-8").splitlines()) - 1,
        "telemetry_summary": telemetry_summary,
        "comparison": comparison,
        "execution": {key: value for key, value in execution.items() if key not in ("stdout", "stderr")},
        "artifact_count": artifact_count,
        "artifact_manifest_sha256": manifest_sha256,
        "formal_source_data": row["formal_source_data"] == "1",
        "promotion_eligible": row["promotion_eligible"] == "1",
        "retry_policy": "none",
        "replacement_retry_allowed": False,
        "completed_utc": utc_now(),
    }
    atomic_json(partial / "attempt-complete.json", receipt)
    validate_attempt_receipt(partial, row)
    os.replace(partial, destination)
    return {"status": "completed", "receipt": receipt}


def rebuild_stage_summary(stage: str, rows: list[dict[str, str]], stage_root: Path) -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    incomplete_attempt_ids: list[str] = []
    for row in rows:
        attempt_root = stage_root / row["attempt_id"]
        receipt_path = attempt_root / "attempt-complete.json"
        if receipt_path.is_file():
            attempts.append(validate_attempt_receipt(attempt_root, row))
        elif attempt_root.exists():
            incomplete_attempt_ids.append(row["attempt_id"])
    partial_roots = sorted(stage_root.glob(".*.partial.*"))
    partial_roots = [path for path in partial_roots if path.is_dir() and not path.name.startswith(".execution-snapshot")]
    partial_failures: list[dict[str, object]] = []
    for path in partial_roots:
        config_path = path / "attempt-config.json"
        if config_path.is_file():
            try:
                attempt_id = str(json.loads(config_path.read_text(encoding="utf-8"))["attempt_id"])
            except (KeyError, json.JSONDecodeError):
                attempt_id = path.name
        else:
            attempt_id = path.name
        if attempt_id not in incomplete_attempt_ids:
            incomplete_attempt_ids.append(attempt_id)
        failure_path = path / "attempt-failure.json"
        if failure_path.is_file() and not failure_path.is_symlink():
            try:
                failure = json.loads(failure_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failure = {}
            partial_failures.append(failure)

    comparisons = [
        receipt["comparison"]
        for receipt in attempts
        if isinstance(receipt.get("comparison"), dict)
    ]

    def comparison_count(metric: str) -> int:
        return sum(int(comparison["metrics"][metric]) == 1 for comparison in comparisons)

    fallback_count = sum(
        int(receipt["telemetry_summary"].get("fallbacks", 0))
        for receipt in attempts
        if isinstance(receipt.get("telemetry_summary"), dict)
    )
    timeout_count = sum(bool(receipt["execution"]["timed_out"]) for receipt in attempts) + sum(
        bool(failure.get("timed_out")) for failure in partial_failures
    )
    oom_count = sum(bool(receipt["execution"]["oom_detected"]) for receipt in attempts) + sum(
        bool(failure.get("oom_detected")) for failure in partial_failures
    )
    declared_mismatches = sum(not bool(comparison["declared_contract_clean"]) for comparison in comparisons)
    complete_representation = len(attempts) == len(rows) and not incomplete_attempt_ids
    if incomplete_attempt_ids:
        stage_status = "blocked_by_technical_or_interrupted_attempt"
    elif complete_representation and declared_mismatches:
        stage_status = "complete_with_scientific_mismatch"
    elif complete_representation:
        stage_status = "complete_clean"
    else:
        stage_status = "in_progress"
    summary = {
        "schema_version": 1,
        "stage": stage,
        "stage_status": stage_status,
        "plan_sha256": sha256_file(PLAN_PATHS[stage]),
        "planned_attempts": len(rows),
        "completed_attempts": len(attempts),
        "complete_representation": complete_representation,
        "arm_counts": {arm: sum(receipt["arm"] == arm for receipt in attempts) for arm in ("A", "H")},
        "comparison_attempts": len(comparisons),
        "clustered_score_top5_equal": comparison_count("clustered_score_top5_equal"),
        "clustered_stability_top5_equal": comparison_count("clustered_stability_top5_equal"),
        "clustered_nt_top5_equal": comparison_count("clustered_nt_top5_equal"),
        "all_three_top5_equal": comparison_count("all_three_top5_equal"),
        "full_output_equal": sum(
            int(comparison["metrics"]["full_missing_rows"]) == 0
            and int(comparison["metrics"]["full_extra_rows"]) == 0
            for comparison in comparisons
        ),
        "declared_contract_mismatches": declared_mismatches,
        "technical_failures": len(incomplete_attempt_ids),
        "incomplete_attempt_ids": sorted(incomplete_attempt_ids),
        "fallbacks": fallback_count,
        "timeouts": timeout_count,
        "ooms": oom_count,
        "promotion_evidence": False if stage == "regression" else None,
        "updated_utc": utc_now(),
    }
    atomic_json(stage_root / "stage-summary.json", summary)
    return summary


def validate_stage_snapshot(
    stage: str, snapshot: Path, rows: list[dict[str, str]]
) -> ToolPaths:
    metadata = validate_snapshot_contents(snapshot)
    require(metadata.get("schema_version") == 1, "snapshot schema drift")
    require(metadata.get("stage") == stage, "snapshot stage drift")
    require(metadata.get("git_head") == git_output("rev-parse", "HEAD"), "snapshot execution commit drift")
    require(metadata.get("plan_sha256") == sha256_file(PLAN_PATHS[stage]), "snapshot plan digest drift")
    require(
        metadata.get("runtime_receipt_sha256") == sha256_file(RUNTIME_RECEIPT_PATH),
        "snapshot runtime receipt drift",
    )
    tool_names = metadata.get("tool_names")
    require(isinstance(tool_names, dict), "snapshot tool identity is missing")
    hybrid = snapshot / str(tool_names.get("hybrid_binary", ""))
    authority = snapshot / str(tool_names.get("authority_binary", ""))
    comparator = snapshot / str(tool_names.get("comparator", ""))
    runtime = read_runtime_receipt()
    require(sha256_file(hybrid) == runtime["hybrid_binary_sha256"], "snapshot hybrid binary drift")
    if any(row["arm"] == "A" for row in rows):
        require(sha256_file(authority) == runtime["authority_binary_sha256"], "snapshot authority binary drift")
    require(sha256_file(comparator) == runtime["comparator_sha256"], "snapshot comparator drift")
    return ToolPaths(hybrid_binary=hybrid, authority_binary=authority, comparator=comparator)


def initialize_stage_snapshot(
    stage: str, stage_root: Path, tools: ToolPaths, rows: list[dict[str, str]]
) -> ToolPaths:
    stage_root.mkdir(parents=True, exist_ok=True)
    require(not stage_root.is_symlink(), "stage artifact root is a symlink")
    snapshot = stage_root / "execution-snapshot"
    if snapshot.exists():
        return validate_stage_snapshot(stage, snapshot, rows)
    stale_snapshots = sorted(stage_root.glob(".execution-snapshot.partial.*"))
    require(not stale_snapshots, "stale execution snapshot requires manual adjudication")
    runtime = read_runtime_receipt()
    require(tools.hybrid_binary.is_file() and not tools.hybrid_binary.is_symlink(), "unsafe hybrid binary")
    require(sha256_file(tools.hybrid_binary) == runtime["hybrid_binary_sha256"], "hybrid binary digest drift")
    require(tools.comparator.is_file() and not tools.comparator.is_symlink(), "unsafe comparator")
    require(sha256_file(tools.comparator) == runtime["comparator_sha256"], "comparator digest drift")
    if any(row["arm"] == "A" for row in rows):
        require(tools.authority_binary.is_file() and not tools.authority_binary.is_symlink(), "unsafe authority binary")
        require(sha256_file(tools.authority_binary) == runtime["authority_binary_sha256"], "authority binary digest drift")
    partial = stage_root / f".execution-snapshot.partial.{os.getpid()}"
    partial.mkdir()
    sources = [
        PLAN_PATHS[stage],
        PLAN_CHECKSUM_PATHS[stage],
        *SNAPSHOT_SUPPORT_FILES,
        tools.comparator,
        *COMPARATOR_SUPPORT_FILES,
        tools.hybrid_binary,
    ]
    if any(row["arm"] == "A" for row in rows):
        sources.append(tools.authority_binary)
    names = [path.name for path in sources]
    require(len(names) == len(set(names)), "snapshot source basenames collide")
    for source in sources:
        shutil.copy2(source, partial / source.name)
    files = {
        path.relative_to(partial).as_posix(): {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in sorted(candidate for candidate in partial.iterdir() if candidate.is_file())
    }
    atomic_json(
        partial / "snapshot.json",
        {
            "schema_version": 1,
            "stage": stage,
            "git_head": git_output("rev-parse", "HEAD"),
            "plan_sha256": sha256_file(PLAN_PATHS[stage]),
            "runtime_receipt_sha256": sha256_file(RUNTIME_RECEIPT_PATH),
            "tool_names": {
                "hybrid_binary": tools.hybrid_binary.name,
                "authority_binary": tools.authority_binary.name,
                "comparator": tools.comparator.name,
            },
            "files": files,
        },
    )
    os.replace(partial, snapshot)
    return validate_stage_snapshot(stage, snapshot, rows)


def execute_stage(stage: str, rows: list[dict[str, str]], tools: ToolPaths, resume: bool) -> dict[str, object]:
    clean_head()
    stage_root = CANONICAL_ARTIFACT_ROOT / stage
    validate_artifact_root(stage, stage_root)
    if stage_root.exists() and not resume:
        raise RunnerError(f"stage artifact root exists; use --resume: {stage_root}")
    execution_tools = initialize_stage_snapshot(stage, stage_root, tools, rows)
    try:
        for row in rows:
            execute_attempt(row, stage_root, execution_tools, resume=resume)
            rebuild_stage_summary(stage, rows, stage_root)
    except (RunnerError, OSError, ValueError, json.JSONDecodeError):
        rebuild_stage_summary(stage, rows, stage_root)
        raise
    summary = rebuild_stage_summary(stage, rows, stage_root)
    require(summary["complete_representation"], "stage representation is incomplete")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=tuple(PLAN_PATHS))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--hybrid-binary", type=Path, default=ToolPaths.hybrid_binary)
    parser.add_argument("--authority-binary", type=Path, default=ToolPaths.authority_binary)
    parser.add_argument("--comparator", type=Path, default=ToolPaths.comparator)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        require(not args.resume or args.execute, "--resume requires --execute")
        rows = read_plan(args.stage)
        tools = ToolPaths(
            hybrid_binary=args.hybrid_binary.resolve(),
            authority_binary=args.authority_binary.resolve(),
            comparator=args.comparator.resolve(),
        )
        result = execute_stage(args.stage, rows, tools, args.resume) if args.execute else plan_summary(args.stage, rows)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (RunnerError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"canonical-hybrid-v2 runner failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
