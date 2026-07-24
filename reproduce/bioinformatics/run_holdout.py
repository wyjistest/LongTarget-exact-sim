#!/usr/bin/env python3
"""Execute the preregistered Bioinformatics Phase 2 holdout without data loss."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from gasal2_longtarget import SCHEMA_PATH as PHASE1_REPORT_SCHEMA_PATH  # noqa: E402
from gasal2_longtarget import validate_schema_value  # noqa: E402
from collect_fasim_gasal2_paper_run import gpu_metrics, max_rss_kb  # noqa: E402
from compare_fasim_segmented_contract import RANKING_MODES, _analyze  # noqa: E402
from fasim_tfo_archive import TFOSORTED_COLUMNS  # noqa: E402
from run_fasim_gasal2_paper_benchmarks import GpuSampler  # noqa: E402


DEFAULT_MANIFEST = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
CANONICAL_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
RUNNER_PATH = Path(__file__).resolve()
FREEZE_ID = "bioinformatics-phase2-holdout-v1-9e293b2c"
MANIFEST_SHA256 = "9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6"
PILOT_WORKLOAD_ID = "hq01_ht01"
FORMAL_STATUS = "preregistered_not_run"
MODES = ("cpu-authority", "fast-experimental", "verified")
BACKEND_TIMEOUT_SECONDS = 3600
MODE_OUTER_TIMEOUT_SECONDS = {
    "cpu-authority": 3720,
    "fast-experimental": 3720,
    "verified": 10920,
}
MANIFEST_SCHEMA = (
    "workload_id",
    "query_id",
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
    "target_id",
    "target_gene_id",
    "target_gene_name",
    "target_chromosome",
    "target_strand",
    "target_tss",
    "target_region_start",
    "target_region_end",
    "target_length_bp",
    "target_sequence_sha256",
    "target_file_sha256",
    "target_path",
    "assembly",
    "annotation_release",
    "selection_seed",
    "requested_contract",
    "run_modes",
    "repeat_count",
    "status",
)
QUERY_FIELDS = (
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
)
TARGET_FIELDS = (
    "target_gene_id",
    "target_gene_name",
    "target_chromosome",
    "target_strand",
    "target_tss",
    "target_region_start",
    "target_region_end",
    "target_length_bp",
    "target_sequence_sha256",
    "target_file_sha256",
    "target_path",
)
MODE_LAYOUT = (
    ("authority", "cpu-authority", "all-ranked-top5"),
    ("candidate", "fast-experimental", "auto"),
    ("verified", "verified", "all-ranked-top5"),
)
COMPARATOR_REQUIRED_METRICS = (
    "baseline_rows",
    "candidate_rows",
    "baseline_unique_rows",
    "candidate_unique_rows",
    "full_missing_rows",
    "full_extra_rows",
    "raw_score_top5_equal",
    "raw_stability_top5_equal",
    "raw_nt_top5_equal",
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "all_three_top5_equal",
    "boundary_ties_equal",
    "baseline_boundary_tie_groups",
    "candidate_boundary_tie_groups",
    "representative_conflict_clusters",
    "candidate_representative_conflict_clusters",
)
COMPARATOR_BINARY_METRICS = (
    "raw_score_top5_equal",
    "raw_stability_top5_equal",
    "raw_nt_top5_equal",
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "all_three_top5_equal",
    "boundary_ties_equal",
)
COMPARATOR_COUNT_METRICS = tuple(
    field for field in COMPARATOR_REQUIRED_METRICS if field not in COMPARATOR_BINARY_METRICS
)
COMPARATOR_DETAILS_SCHEMA = (
    "side",
    "kind",
    "mode",
    "rank",
    "cluster_id",
    *TFOSORTED_COLUMNS,
)
FORMAL_TABLE_NAMES = (
    "formal-attempts.tsv",
    "formal-failures.tsv",
    "formal-artifacts.tsv",
    "formal-summary.json",
)
SNAPSHOT_SUPPORT_RELATIVE_PATHS = (
    "scripts/fasim_tfo_archive.py",
    "scripts/compare_fasim_lite_offline_cluster_topk.py",
    "schemas/gasal2_longtarget_run_report.schema.json",
)
PHASE1_REPORT_SCHEMA = json.loads(PHASE1_REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ExecutionTools:
    workflow: Path = ROOT / "scripts/gasal2_longtarget.py"
    comparator: Path = ROOT / "scripts/compare_fasim_segmented_contract.py"
    environment_capture: Path = ROOT / "scripts/capture_fasim_gasal2_paper_environment.py"
    authority_binary: Path = ROOT / "fasim_longtarget_x86"
    candidate_binary: Path = ROOT / "fasim_longtarget_gasal2"


@dataclass(frozen=True)
class ExecutionSnapshot:
    root: Path
    tools: ExecutionTools
    query: Path
    target: Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"cannot resolve Git HEAD: {type(exc).__name__}") from exc
    head = result.stdout.strip()
    require(result.returncode == 0 and len(head) == 40 and set(head) <= set("0123456789abcdef"), "cannot resolve exact Git HEAD")
    return head


def production_checkout_changes() -> list[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--ignored=no",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"git-status-unavailable:{type(exc).__name__}"]
    if result.returncode != 0:
        return [f"git-status-returncode:{result.returncode}"]
    return [line for line in result.stdout.splitlines() if line]


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    root = root.absolute()
    require(root.is_dir() and not root.is_symlink(), f"fsync tree root is invalid or symlinked: {root}")
    entries = sorted(root.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    require(not symlinks, f"fsync tree contains symlink: {symlinks[0] if symlinks else 'NA'}")
    unexpected = [path for path in entries if not path.is_file() and not path.is_dir()]
    require(not unexpected, f"fsync tree contains non-regular entry: {unexpected[0] if unexpected else 'NA'}")

    for path in (entry for entry in entries if entry.is_file()):
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    directories = [entry for entry in entries if entry.is_dir()]
    directories.sort(key=lambda path: len(path.relative_to(root).parts), reverse=True)
    for path in directories:
        _fsync_directory(path)
    _fsync_directory(root)


def _write_fsynced(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _tsv_bytes(
    fieldnames: tuple[str, ...], rows: list[dict[str, object]]
) -> bytes:
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


def write_json(path: Path, payload: object) -> None:
    _write_fsynced(path, _json_bytes(payload))


def write_tsv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    _write_fsynced(path, _tsv_bytes(fieldnames, rows))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and set(value) <= set("0123456789abcdef")


def _load_fasta(path: Path) -> str:
    records = 0
    sequence: list[str] = []
    with path.open(encoding="ascii") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                records += 1
                require(records == 1, f"multiple FASTA records in {path}")
            else:
                require(records == 1, f"sequence before header at {path}:{line_number}")
                sequence.append(line.upper())
    joined = "".join(sequence)
    require(records == 1 and joined, f"empty FASTA input: {path}")
    require(set(joined) <= set("ACGT"), f"noncanonical FASTA input: {path}")
    return joined


def _repository_root(manifest: Path) -> Path:
    resolved = manifest.resolve()
    require(
        resolved.parent.name == "bioinformatics" and resolved.parent.parent.name == "paper",
        "manifest must be paper/bioinformatics/holdout_manifest.tsv within a repository root",
    )
    return resolved.parents[2]


def _resolve_input(root: Path, raw: str, label: str) -> Path:
    relative = Path(raw)
    require(not relative.is_absolute(), f"{label} path must be repository-relative")
    unresolved = root / relative
    require(not unresolved.is_symlink(), f"{label} path may not be a symlink")
    resolved = unresolved.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} path escapes repository root") from exc
    require(resolved.is_file() and not resolved.is_symlink(), f"missing regular {label}: {raw}")
    return resolved


def _read_manifest(manifest: Path) -> list[dict[str, str]]:
    if not manifest.is_file():
        raise ValueError(f"holdout manifest is missing: {manifest}")
    observed_digest = sha256_file(manifest)
    require(
        observed_digest == MANIFEST_SHA256,
        f"manifest SHA-256 digest drift: expected {MANIFEST_SHA256}, observed {observed_digest}",
    )
    with manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(
            tuple(reader.fieldnames or ()) == MANIFEST_SCHEMA,
            f"manifest schema drift: expected {list(MANIFEST_SCHEMA)}, observed {reader.fieldnames or []}",
        )
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            require(None not in row, f"malformed manifest row {line_number}")
            require(all(value is not None and value != "" for value in row.values()), f"empty manifest field at row {line_number}")
            rows.append(dict(row))
    return rows


def _consistent(rows: Iterable[dict[str, str]], fields: tuple[str, ...], label: str) -> None:
    rows = list(rows)
    for field in fields:
        require(len({row[field] for row in rows}) == 1, f"{label} metadata drift for {field}")


def validate_manifest(manifest: Path) -> list[dict[str, str]]:
    manifest = manifest.resolve()
    root = _repository_root(manifest)
    rows = _read_manifest(manifest)
    query_ids = tuple(f"hq{index:02d}" for index in range(1, 13))
    target_ids = ("ht01", "ht02")
    expected_pairs = [(query_id, target_id) for query_id in query_ids for target_id in target_ids]
    actual_pairs = [(row["query_id"], row["target_id"]) for row in rows]
    require(len(rows) == 24, "manifest must contain the exact 12x2 Cartesian panel")
    require(len(set(actual_pairs)) == len(actual_pairs), "manifest contains a duplicate query-target pair")
    require(actual_pairs == expected_pairs, "manifest is not the ordered exact 12x2 Cartesian product")
    workload_ids = [row["workload_id"] for row in rows]
    require(len(set(workload_ids)) == len(workload_ids), "manifest contains duplicate workload IDs")
    require(
        all(row["workload_id"] == f"{row['query_id']}_{row['target_id']}" for row in rows),
        "workload ID does not match its query-target pair",
    )

    representative_queries = {"hq01", "hq05", "hq09"}
    expected_strata = {
        **{f"hq{index:02d}": "le_800" for index in range(1, 5)},
        **{f"hq{index:02d}": "801_1600" for index in range(5, 9)},
        **{f"hq{index:02d}": "1601_2812" for index in range(9, 13)},
    }
    input_digests: dict[Path, str] = {}
    input_sequences: dict[Path, str] = {}
    for row in rows:
        workload_id = row["workload_id"]
        require(row["status"] == FORMAL_STATUS, f"{workload_id}: status drift")
        require(row["requested_contract"] == "all-ranked-top5", f"{workload_id}: requested contract drift")
        require(row["run_modes"] == "authority,candidate,verified", f"{workload_id}: run mode drift")
        require(row["assembly"] == "GRCh38", f"{workload_id}: assembly drift")
        require(row["annotation_release"] == "GENCODE v49", f"{workload_id}: annotation drift")
        require(
            row["selection_seed"] == "gasal2-longtarget-phase2-holdout-v1-20260724",
            f"{workload_id}: selection seed drift",
        )
        expected_repeat = "3" if row["query_id"] in representative_queries else "1"
        require(row["repeat_count"] == expected_repeat, f"{workload_id}: repeat count drift")
        require(row["length_stratum"] == expected_strata[row["query_id"]], f"{workload_id}: length stratum drift")
        for digest_field in (
            "query_sequence_sha256",
            "query_file_sha256",
            "target_sequence_sha256",
            "target_file_sha256",
        ):
            require(_is_sha256(row[digest_field]), f"{workload_id}: invalid SHA-256 in {digest_field}")

        for prefix in ("query", "target"):
            path = _resolve_input(root, row[f"{prefix}_path"], f"{prefix} input")
            observed_file = input_digests.setdefault(path, sha256_file(path))
            require(
                observed_file == row[f"{prefix}_file_sha256"],
                f"{workload_id}: {prefix} file SHA-256 digest mismatch",
            )
            sequence = input_sequences.setdefault(path, _load_fasta(path))
            observed_sequence = hashlib.sha256(sequence.encode("ascii")).hexdigest()
            require(
                observed_sequence == row[f"{prefix}_sequence_sha256"],
                f"{workload_id}: {prefix} sequence SHA-256 digest mismatch",
            )
        require(len(input_sequences[_resolve_input(root, row["query_path"], "query input")]) == int(row["query_length_nt"]), f"{workload_id}: query length drift")
        require(len(input_sequences[_resolve_input(root, row["target_path"], "target input")]) == int(row["target_length_bp"]), f"{workload_id}: target length drift")

    for query_id in query_ids:
        _consistent((row for row in rows if row["query_id"] == query_id), QUERY_FIELDS, query_id)
    for target_id in target_ids:
        _consistent((row for row in rows if row["target_id"] == target_id), TARGET_FIELDS, target_id)
    return rows


def _attempt(row: dict[str, str], repeat_index: int, attempt_id: str) -> dict[str, object]:
    return {
        "attempt_id": attempt_id,
        "workload_id": row["workload_id"],
        "repeat_index": repeat_index,
        "query_id": row["query_id"],
        "target_id": row["target_id"],
        "query_path": row["query_path"],
        "target_path": row["target_path"],
        "query_file_sha256": row["query_file_sha256"],
        "query_sequence_sha256": row["query_sequence_sha256"],
        "target_file_sha256": row["target_file_sha256"],
        "target_sequence_sha256": row["target_sequence_sha256"],
        "rule": 0,
        "top_k": 5,
        "assembly": row["assembly"],
        "annotation_release": row["annotation_release"],
    }


def build_plan(manifest: Path) -> dict[str, object]:
    manifest = manifest.resolve()
    rows = validate_manifest(manifest)
    formal_attempts: list[dict[str, object]] = []
    for row in rows:
        for repeat_index in range(int(row["repeat_count"])):
            formal_attempts.append(
                _attempt(row, repeat_index, f"{row['workload_id']}__repeat{repeat_index:02d}")
            )
    pilot_row = next(row for row in rows if row["workload_id"] == PILOT_WORKLOAD_ID)
    pilot = _attempt(pilot_row, 0, f"pilot__{PILOT_WORKLOAD_ID}__repeat00")
    formal_attempt_count = len(formal_attempts)
    backend_execution_count = formal_attempt_count * 4
    top_level_run_count = formal_attempt_count * len(MODES)
    max_top_level_wall = formal_attempt_count * sum(MODE_OUTER_TIMEOUT_SECONDS.values())
    return {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "manifest": str(manifest),
        "manifest_sha256": MANIFEST_SHA256,
        "workload_count": len(rows),
        "formal_attempt_count": formal_attempt_count,
        "top_level_run_count": top_level_run_count,
        "backend_execution_count": backend_execution_count,
        "pilot": pilot,
        "formal_attempts": formal_attempts,
        "resource_bounds": {
            "backend_timeout_seconds": BACKEND_TIMEOUT_SECONDS,
            "mode_outer_timeout_seconds": MODE_OUTER_TIMEOUT_SECONDS,
            "max_backend_wall_seconds": backend_execution_count * BACKEND_TIMEOUT_SECONDS,
            "max_top_level_outer_wall_seconds": max_top_level_wall,
            "gpu_sample_file_count": top_level_run_count,
        },
    }


def _tool_payload(tools: ExecutionTools) -> dict[str, dict[str, str]]:
    payload: dict[str, dict[str, str]] = {}
    for name in (
        "workflow",
        "comparator",
        "environment_capture",
        "authority_binary",
        "candidate_binary",
    ):
        unresolved = getattr(tools, name)
        require(not unresolved.is_symlink(), f"{name} tool may not be a symlink: {unresolved}")
        path = unresolved.resolve()
        require(path.is_file(), f"missing regular {name} tool: {path}")
        payload[name] = {"path": str(path), "sha256": sha256_file(path)}
    return payload


def _require_clean_execution_checkout() -> None:
    changes = production_checkout_changes()
    require(
        not changes,
        "execution identity drift: checkout is not clean: " + " | ".join(changes),
    )


def capture_execution_identity(
    manifest: Path,
    tools: ExecutionTools,
    attempts: Iterable[dict[str, object]],
) -> dict[str, object]:
    unresolved_manifest = manifest.absolute()
    require(not unresolved_manifest.is_symlink(), "execution manifest may not be a symlink")
    manifest = unresolved_manifest.resolve()
    repository_root = _repository_root(manifest)
    clean_checkout_required = repository_root == ROOT.resolve()
    if clean_checkout_required:
        _require_clean_execution_checkout()

    inputs: dict[str, dict[str, str]] = {}
    for attempt in attempts:
        for prefix in ("query", "target"):
            relative = str(attempt[f"{prefix}_path"])
            file_digest = str(attempt[f"{prefix}_file_sha256"])
            sequence_digest = str(attempt[f"{prefix}_sequence_sha256"])
            require(_is_sha256(file_digest), f"invalid pinned {prefix} file SHA-256")
            require(_is_sha256(sequence_digest), f"invalid pinned {prefix} sequence SHA-256")
            path = _resolve_input(repository_root, relative, f"{prefix} input")
            binding = {
                "path": str(path),
                "file_sha256": file_digest,
                "sequence_sha256": sequence_digest,
            }
            if relative in inputs:
                require(inputs[relative] == binding, f"inconsistent frozen input binding: {relative}")
                continue
            require(sha256_file(path) == file_digest, f"execution identity input file digest drift: {relative}")
            observed_sequence = hashlib.sha256(_load_fasta(path).encode("ascii")).hexdigest()
            require(
                observed_sequence == sequence_digest,
                f"execution identity input sequence digest drift: {relative}",
            )
            inputs[relative] = binding

    require(not RUNNER_PATH.is_symlink() and RUNNER_PATH.is_file(), "execution runner is missing or symlinked")
    support_files: dict[str, dict[str, str]] = {}
    for relative in SNAPSHOT_SUPPORT_RELATIVE_PATHS:
        path = ROOT / relative
        require(not path.is_symlink() and path.is_file(), f"execution support file is missing or symlinked: {relative}")
        support_files[relative] = {"path": str(path), "sha256": sha256_file(path)}
    return {
        "schema_version": 1,
        "repository_root": str(repository_root),
        "clean_checkout_required": clean_checkout_required,
        "manifest": {"path": str(manifest), "sha256": sha256_file(manifest)},
        "runner": {"path": str(RUNNER_PATH), "sha256": sha256_file(RUNNER_PATH)},
        "git_head": git_head(),
        "tools": _tool_payload(tools),
        "support_files": support_files,
        "inputs": dict(sorted(inputs.items())),
    }


def validate_execution_identity(identity: dict[str, object]) -> None:
    if identity["clean_checkout_required"] is True:
        _require_clean_execution_checkout()
    require(git_head() == identity["git_head"], "execution identity Git HEAD drift")

    for label in ("manifest", "runner"):
        binding = identity[label]
        path = Path(str(binding["path"]))
        require(not path.is_symlink() and path.is_file(), f"execution identity {label} is missing or symlinked")
        require(
            sha256_file(path) == binding["sha256"],
            f"execution identity {label} SHA-256 drift",
        )
    for name, binding in identity["tools"].items():
        path = Path(str(binding["path"]))
        require(not path.is_symlink() and path.is_file(), f"execution identity tool is missing or symlinked: {name}")
        require(
            sha256_file(path) == binding["sha256"],
            f"execution identity tool SHA-256 drift: {name}",
        )
    for relative, binding in identity["support_files"].items():
        path = Path(str(binding["path"]))
        require(not path.is_symlink() and path.is_file(), f"execution identity support file is missing or symlinked: {relative}")
        require(
            sha256_file(path) == binding["sha256"],
            f"execution identity support file SHA-256 drift: {relative}",
        )
    for relative, binding in identity["inputs"].items():
        path = Path(str(binding["path"]))
        require(not path.is_symlink() and path.is_file(), f"execution identity input is missing or symlinked: {relative}")
        require(
            sha256_file(path) == binding["file_sha256"],
            f"execution identity input file digest drift: {relative}",
        )
        observed_sequence = hashlib.sha256(_load_fasta(path).encode("ascii")).hexdigest()
        require(
            observed_sequence == binding["sequence_sha256"],
            f"execution identity input sequence digest drift: {relative}",
        )


def _snapshot_expected_files(
    identity: dict[str, object], query_relative: str, target_relative: str
) -> dict[str, dict[str, str]]:
    tools = identity["tools"]
    query_binding = identity["inputs"][query_relative]
    target_binding = identity["inputs"][target_relative]
    expected = {
        "repository/scripts/gasal2_longtarget.py": tools["workflow"],
        "repository/scripts/compare_fasim_segmented_contract.py": tools["comparator"],
        "repository/scripts/capture_fasim_gasal2_paper_environment.py": tools[
            "environment_capture"
        ],
        "binaries/fasim_longtarget_x86": tools["authority_binary"],
        "binaries/fasim_longtarget_gasal2": tools["candidate_binary"],
        "inputs/query.fa": {
            "path": query_binding["path"],
            "sha256": query_binding["file_sha256"],
        },
        "inputs/target.fa": {
            "path": target_binding["path"],
            "sha256": target_binding["file_sha256"],
        },
    }
    for relative, binding in identity["support_files"].items():
        expected[f"repository/{relative}"] = binding
    return expected


def validate_execution_snapshot(
    snapshot: ExecutionSnapshot, identity: dict[str, object]
) -> None:
    root = snapshot.root.absolute()
    require(not root.is_symlink() and root.is_dir(), "execution snapshot root is missing or symlinked")
    entries = sorted(root.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    require(not symlinks, f"execution snapshot contains symlink: {symlinks[0] if symlinks else 'NA'}")
    unexpected = [path for path in entries if not path.is_file() and not path.is_dir()]
    require(not unexpected, f"execution snapshot contains nonregular entry: {unexpected[0] if unexpected else 'NA'}")

    manifest_path = root / "snapshot-manifest.json"
    try:
        raw_manifest = manifest_path.read_bytes()
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("execution snapshot manifest is missing or invalid") from exc
    require(isinstance(manifest, dict), "execution snapshot manifest must be an object")
    require(
        raw_manifest == _json_bytes(manifest),
        "execution snapshot manifest is not canonical",
    )
    require(
        manifest.get("execution_identity_sha256") == canonical_digest(identity),
        "execution snapshot source identity drift",
    )
    query_relative = str(manifest.get("query_source_relative_path"))
    target_relative = str(manifest.get("target_source_relative_path"))
    expected = _snapshot_expected_files(identity, query_relative, target_relative)
    files = manifest.get("files")
    require(isinstance(files, dict) and set(files) == set(expected), "execution snapshot manifest file set drift")
    observed_files = {
        str(path.relative_to(root))
        for path in entries
        if path.is_file() and path != manifest_path
    }
    require(observed_files == set(expected), "execution snapshot retained file set drift")
    for relative, binding in expected.items():
        path = root / relative
        row = files[relative]
        require(path.is_file() and not path.is_symlink(), f"execution snapshot file is missing: {relative}")
        require(row.get("source_path") == binding["path"], f"execution snapshot source path drift: {relative}")
        require(row.get("sha256") == binding["sha256"], f"execution snapshot bound digest drift: {relative}")
        require(row.get("size_bytes") == path.stat().st_size, f"execution snapshot size drift: {relative}")
        require(sha256_file(path) == binding["sha256"], f"execution snapshot SHA-256 drift: {relative}")
        require(path.stat().st_mode & 0o222 == 0, f"execution snapshot file is writable: {relative}")
    require(manifest_path.stat().st_mode & 0o222 == 0, "execution snapshot manifest is writable")
    for path in [root, *(entry for entry in entries if entry.is_dir())]:
        require(path.stat().st_mode & 0o222 == 0, f"execution snapshot directory is writable: {path}")


def create_execution_snapshot(
    partial: Path,
    attempt: dict[str, object],
    identity: dict[str, object],
) -> ExecutionSnapshot:
    root = partial / "execution-snapshot"
    require(not root.exists() and not root.is_symlink(), f"execution snapshot already exists: {root}")
    query_relative = str(attempt["query_path"])
    target_relative = str(attempt["target_path"])
    expected = _snapshot_expected_files(identity, query_relative, target_relative)
    files: dict[str, dict[str, object]] = {}
    for relative, binding in expected.items():
        source = Path(binding["path"])
        require(not source.is_symlink() and source.is_file(), f"snapshot source is missing or symlinked: {source}")
        destination = root / relative
        _write_fsynced(destination, source.read_bytes())
        require(
            sha256_file(destination) == binding["sha256"],
            f"snapshot source changed while copying: {source}",
        )
        files[relative] = {
            "source_path": str(source),
            "sha256": binding["sha256"],
            "size_bytes": destination.stat().st_size,
        }

    manifest = {
        "schema_version": 1,
        "attempt_id": attempt["attempt_id"],
        "execution_identity_sha256": canonical_digest(identity),
        "query_source_relative_path": query_relative,
        "target_source_relative_path": target_relative,
        "files": dict(sorted(files.items())),
    }
    manifest_path = root / "snapshot-manifest.json"
    write_json(manifest_path, manifest)
    for path in (entry for entry in root.rglob("*") if entry.is_file()):
        executable = path.relative_to(root).parts[0] == "binaries"
        path.chmod(0o555 if executable else 0o444)
    directories = [entry for entry in root.rglob("*") if entry.is_dir()]
    directories.sort(key=lambda path: len(path.relative_to(root).parts), reverse=True)
    for path in directories:
        path.chmod(0o555)
    root.chmod(0o555)
    _fsync_tree(root)

    snapshot = ExecutionSnapshot(
        root=root,
        tools=ExecutionTools(
            workflow=root / "repository/scripts/gasal2_longtarget.py",
            comparator=root / "repository/scripts/compare_fasim_segmented_contract.py",
            environment_capture=root
            / "repository/scripts/capture_fasim_gasal2_paper_environment.py",
            authority_binary=root / "binaries/fasim_longtarget_x86",
            candidate_binary=root / "binaries/fasim_longtarget_gasal2",
        ),
        query=root / "inputs/query.fa",
        target=root / "inputs/target.fa",
    )
    validate_execution_snapshot(snapshot, identity)
    return snapshot


def attempt_config(
    attempt: dict[str, object],
    manifest: Path,
    tools: ExecutionTools,
    execution_identity: dict[str, object] | None = None,
) -> dict[str, object]:
    if execution_identity is None:
        execution_identity = capture_execution_identity(manifest, tools, [attempt])
    for prefix in ("query", "target"):
        relative = str(attempt[f"{prefix}_path"])
        binding = execution_identity["inputs"].get(relative)
        require(binding is not None, f"attempt input is absent from execution identity: {relative}")
        require(
            binding["file_sha256"] == attempt[f"{prefix}_file_sha256"]
            and binding["sequence_sha256"] == attempt[f"{prefix}_sequence_sha256"],
            f"attempt input digest binding mismatch: {relative}",
        )
    payload: dict[str, object] = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "execution_identity": execution_identity,
        "execution_identity_sha256": canonical_digest(execution_identity),
        "manifest": execution_identity["manifest"]["path"],
        "manifest_sha256": execution_identity["manifest"]["sha256"],
        "runner": execution_identity["runner"],
        "git_head": execution_identity["git_head"],
        "attempt": attempt,
        "modes": [
            {"artifact_namespace": namespace, "mode": mode, "contract": contract}
            for namespace, mode, contract in MODE_LAYOUT
        ],
        "backend_timeout_seconds": BACKEND_TIMEOUT_SECONDS,
        "rule": 0,
        "triplex_preset": "normal",
        "top_k": 5,
        "tools": execution_identity["tools"],
    }
    payload["config_digest_sha256"] = canonical_digest(payload)
    return payload


def _kill_process_group(process: subprocess.Popen[object]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def _run_captured(
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    *,
    snapshot: ExecutionSnapshot | None = None,
    execution_identity: dict[str, object] | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    timed_out = False
    if snapshot is not None:
        require(execution_identity is not None, "snapshot launch is missing source identity")
        validate_execution_snapshot(snapshot, execution_identity)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=stdout_path.parent,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            try:
                returncode = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_group(process)
                returncode = 124
            except BaseException:
                _kill_process_group(process)
                raise
        finally:
            if snapshot is not None:
                validate_execution_snapshot(snapshot, execution_identity)
    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": time.perf_counter() - started,
    }


def _mode_command(
    tools: ExecutionTools,
    namespace: str,
    mode: str,
    contract: str,
    attempt: dict[str, object],
    query: Path,
    target: Path,
    mode_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        str(tools.workflow.resolve()),
        "--mode",
        mode,
        "--contract",
        contract,
        "--query",
        str(query),
        "--target",
        str(target),
        "--output",
        str((mode_dir / "output").resolve()),
        "--report",
        str((mode_dir / "report.json").resolve()),
        "--rule",
        "0",
        "--triplex-preset",
        "normal",
        "--top-k",
        "5",
        "--assembly",
        str(attempt["assembly"]),
        "--annotation-release",
        str(attempt["annotation_release"]),
        "--timeout",
        str(BACKEND_TIMEOUT_SECONDS),
        "--authority-binary",
        str(tools.authority_binary.resolve()),
        "--candidate-binary",
        str(tools.candidate_binary.resolve()),
        "--comparator",
        str(tools.comparator.resolve()),
    ]


def _read_report(path: Path) -> tuple[dict[str, object] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "invalid:not_object"
    return payload, None


def _validate_published_outputs(report: dict[str, object], output_dir: Path) -> None:
    require(not output_dir.is_symlink() and output_dir.is_dir(), "mode output directory is missing or symlinked")
    output_dir = output_dir.resolve()
    entries = sorted(output_dir.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    require(not symlinks, f"mode output tree contains symlink: {symlinks[0] if symlinks else 'NA'}")
    unexpected = [path for path in entries if not path.is_file() and not path.is_dir()]
    require(not unexpected, f"mode output tree contains non-regular entry: {unexpected[0] if unexpected else 'NA'}")
    actual_files = {
        str(path.relative_to(output_dir)): path
        for path in entries
        if path.is_file()
    }

    declared: dict[str, dict[str, object]] = {}
    for row in report["published_outputs"]:
        relative_raw = row["relative_path"]
        relative = Path(relative_raw)
        require(
            relative_raw != ""
            and not relative.is_absolute()
            and relative != Path(".")
            and ".." not in relative.parts
            and str(relative) == relative_raw,
            f"unsafe published output relative path: {relative_raw}",
        )
        require(relative_raw not in declared, f"duplicate published output relative path: {relative_raw}")
        expected_path = output_dir / relative
        require(row["path"] == str(expected_path), f"published output absolute path mismatch: {relative_raw}")
        require(expected_path.is_file() and not expected_path.is_symlink(), f"published output is missing: {relative_raw}")
        require(row["size_bytes"] == expected_path.stat().st_size, f"published output size mismatch: {relative_raw}")
        require(_is_sha256(row["sha256"]), f"published output SHA-256 is invalid: {relative_raw}")
        require(row["sha256"] == sha256_file(expected_path), f"published output SHA-256 mismatch: {relative_raw}")
        expected_records: int | None = None
        if expected_path.name.endswith("-TFOsorted") or expected_path.suffix == ".tsv":
            with expected_path.open(encoding="utf-8", errors="replace") as handle:
                expected_records = max(sum(1 for _ in handle) - 1, 0)
        require(row["record_count"] == expected_records, f"published output record count mismatch: {relative_raw}")
        declared[relative_raw] = row
    require(set(declared) == set(actual_files), "published output file set mismatch")


def _validate_mode_report(
    report: dict[str, object],
    *,
    mode: str,
    contract: str,
    attempt: dict[str, object],
    input_paths: dict[str, Path],
    output_dir: Path,
    tools: ExecutionTools,
    returncode: int,
) -> None:
    validate_schema_value(PHASE1_REPORT_SCHEMA, report, "report")
    expected_resolved_contract = (
        "experimental-native" if mode == "fast-experimental" else "all-ranked-top5"
    )
    require(report["mode"] == mode, "mode report mode binding mismatch")
    require(report["requested_contract"] == contract, "mode report requested contract mismatch")
    require(report["resolved_contract"] == expected_resolved_contract, "mode report resolved contract mismatch")
    require(report["resolved_execution"] == mode, "mode report resolved execution mismatch")
    require(
        report["authority_backend"] == str(tools.authority_binary.resolve()),
        "mode report authority binary mismatch",
    )
    require(
        report["candidate_backend"] == str(tools.candidate_binary.resolve()),
        "mode report candidate binary mismatch",
    )
    for prefix in ("query", "target"):
        expected_path = input_paths[prefix].resolve()
        observed = report["inputs"][prefix]
        require(
            Path(str(observed["path"])).resolve() == expected_path,
            f"mode report {prefix} path mismatch",
        )
        require(
            observed["sha256"] == attempt[f"{prefix}_file_sha256"],
            f"mode report {prefix} pinned digest mismatch",
        )
    metadata = report["biological_metadata"]
    require(metadata["assembly"] == attempt["assembly"], "mode report assembly mismatch")
    require(
        metadata["annotation_release"] == attempt["annotation_release"],
        "mode report annotation mismatch",
    )
    counters = report["counters"]
    for field in ("fallback", "guard", "oom", "timeout"):
        value = counters[field]
        require(
            type(value) is int and value >= 0,
            f"mode report counter {field} must be an exact nonnegative integer",
        )
    status = report["result_status"]
    source = report["published_source"]
    if returncode == 0:
        _validate_published_outputs(report, output_dir)
        if mode == "cpu-authority":
            require(status == "authority_complete" and source == "authority", "authority report result/source incoherent")
            require(counters["fallback"] == 0, "authority report cannot claim fallback")
        elif mode == "fast-experimental":
            require(status == "experimental_unverified" and source == "candidate", "candidate report result/source incoherent")
            require(counters["fallback"] == 0, "direct candidate report cannot claim fallback")
        else:
            allowed = {
                "candidate_clean": "candidate",
                "cpu_fallback_after_mismatch": "authority",
                "cpu_fallback_after_candidate_failure": "authority",
                "cpu_fallback_after_comparator_failure": "authority",
            }
            require(status in allowed and source == allowed[status], "verified report result/source incoherent")
            require(
                (status == "candidate_clean" and counters["fallback"] == 0)
                or (status != "candidate_clean" and counters["fallback"] > 0),
                "verified report fallback counter incoherent",
            )
            nested = report["comparators"]
            declared_fields = (
                "score_top5_equal",
                "stability_top5_equal",
                "nt_top5_equal",
                "boundary_ties_equal",
            )
            if status == "candidate_clean":
                require(
                    nested["status"] == "clean"
                    and all(nested[field] is True for field in declared_fields)
                    and nested["all_ranked_top5_equal"] is True,
                    "candidate_clean report lacks clean nested all-ranked evidence",
                )
            elif status == "cpu_fallback_after_mismatch":
                require(
                    nested["status"] == "mismatch"
                    and any(nested[field] is False for field in declared_fields),
                    "mismatch fallback lacks nested mismatch evidence",
                )
            elif status == "cpu_fallback_after_candidate_failure":
                require(nested["status"] == "not_run", "candidate failure fallback comparator must be not_run")
            else:
                require(nested["status"] == "failed", "comparator failure fallback lacks failed evidence")
    else:
        failure_statuses = {
            "cpu-authority": {"authority_failure", "invalid_input", "internal_error", "interrupted"},
            "fast-experimental": {"candidate_failure", "invalid_input", "environment_unavailable", "internal_error", "interrupted"},
            "verified": {"authority_failure", "environment_unavailable", "invalid_input", "internal_error", "interrupted"},
        }
        require(status in failure_statuses[mode] and source is None, "failed mode report result/source incoherent")


def time_evidence(path: Path, attempted: bool) -> dict[str, object]:
    unavailable = {
        "time_telemetry_available": False,
        "time_telemetry_status": "unavailable",
        "time_telemetry_reason": "time_tool_unavailable" if not attempted else "time_output_missing",
        "max_rss_kb": "NA",
    }
    if not attempted:
        return unavailable
    if not path.is_file():
        return unavailable
    try:
        rss = max_rss_kb(path)
    except BaseException as exc:
        unavailable["time_telemetry_reason"] = f"invalid_time_output:{type(exc).__name__}"
        return unavailable
    if type(rss) is not int or rss < 0:
        unavailable["time_telemetry_reason"] = "missing_or_invalid_max_rss"
        return unavailable
    return {
        "time_telemetry_available": True,
        "time_telemetry_status": "available",
        "time_telemetry_reason": "validated_gnu_time",
        "max_rss_kb": rss,
    }


def gpu_evidence(path: Path, attempted: bool) -> dict[str, object]:
    unavailable = {
        "gpu_telemetry_available": False,
        "gpu_telemetry_status": "unavailable",
        "gpu_telemetry_reason": "sampler_not_started" if not attempted else "gpu_output_missing",
        "gpu_sample_count": 0,
        "gpu_memory_peak_mib": "NA",
        "gpu_utilization_peak_percent": "NA",
        "gpu_temperature_peak_c": "NA",
        "gpu_power_peak_w": "NA",
        "gpu_sm_clock_peak_mhz": "NA",
    }
    if not attempted or not path.is_file():
        return unavailable
    try:
        metrics = gpu_metrics(path)
    except BaseException as exc:
        unavailable["gpu_telemetry_reason"] = f"invalid_gpu_output:{type(exc).__name__}"
        return unavailable
    available = metrics.get("gpu_measurement_status") == "available"
    metrics["gpu_telemetry_available"] = available
    metrics["gpu_telemetry_status"] = "available" if available else "unavailable"
    metrics["gpu_telemetry_reason"] = "validated_samples" if available else "no_available_samples"
    return metrics


def _run_mode(
    namespace: str,
    mode: str,
    contract: str,
    attempt: dict[str, object],
    partial: Path,
    snapshot: ExecutionSnapshot,
    execution_identity: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    mode_dir = partial / namespace
    mode_dir.mkdir(parents=True)
    command = _mode_command(
        snapshot.tools,
        namespace,
        mode,
        contract,
        attempt,
        snapshot.query,
        snapshot.target,
        mode_dir,
    )
    time_path = mode_dir / "time.txt"
    timed = Path("/usr/bin/time").is_file()
    measured_command = command
    if timed:
        measured_command = ["/usr/bin/time", "-v", "-o", str(time_path), *command]
    else:
        _write_fsynced(time_path, b"resource_measurement=NA\n")
    gpu_path = mode_dir / "gpu-memory.csv"
    telemetry_errors: list[str] = []
    sampler = None
    sampler_started = False
    try:
        sampler = GpuSampler(gpu_path)
        try:
            sampler.start()
            sampler_started = True
        except BaseException as exc:
            telemetry_errors.append(f"gpu_sampler_start:{type(exc).__name__}:{exc}")
        try:
            measured = _run_captured(
                measured_command,
                mode_dir / "stdout.log",
                mode_dir / "stderr.log",
                timeout_seconds,
                snapshot=snapshot,
                execution_identity=execution_identity,
            )
        finally:
            if sampler_started:
                try:
                    sampler.stop()
                except BaseException as exc:
                    telemetry_errors.append(f"gpu_sampler_stop:{type(exc).__name__}:{exc}")
    except BaseException:
        raise
    if timed and not time_path.exists():
        _write_fsynced(time_path, b"resource_measurement=NA\n")
    report, report_error = _read_report(mode_dir / "report.json")
    report_validation_status = "missing"
    if report is not None:
        try:
            _validate_mode_report(
                report,
                mode=mode,
                contract=contract,
                attempt=attempt,
                input_paths={"query": snapshot.query, "target": snapshot.target},
                output_dir=mode_dir / "output",
                tools=snapshot.tools,
                returncode=int(measured["returncode"]),
            )
            report_validation_status = "valid"
        except (KeyError, TypeError, ValueError) as exc:
            report_validation_status = "invalid"
            report_error = f"invalid:{exc}"
    counters = report.get("counters", {}) if report_validation_status == "valid" else {}
    time_metrics = time_evidence(time_path, attempted=timed)
    gpu_metrics_payload = gpu_evidence(gpu_path, attempted=sampler_started)
    if timed and not time_metrics["time_telemetry_available"]:
        telemetry_errors.append(str(time_metrics["time_telemetry_reason"]))
    if sampler_started and gpu_metrics_payload["gpu_telemetry_reason"].startswith(
        ("gpu_output_missing", "invalid_gpu_output")
    ):
        telemetry_errors.append(str(gpu_metrics_payload["gpu_telemetry_reason"]))
    result = {
        "artifact_namespace": namespace,
        "mode": mode,
        "contract": contract,
        "command": command,
        "returncode": measured["returncode"],
        "timed_out": measured["timed_out"],
        "wall_seconds": measured["wall_seconds"],
        "time_available": time_metrics["time_telemetry_available"],
        "report_available": report is not None,
        "report_error": report_error or "NA",
        "report_validation_status": report_validation_status,
        "result_status": report.get("result_status", "NA") if report else "NA",
        "published_source": report.get("published_source", "NA") if report else "NA",
        "fallback_count": int(counters.get("fallback", 0) or 0),
        "oom_count": int(counters.get("oom", 0) or 0),
        "reported_timeout_count": int(counters.get("timeout", 0) or 0),
        "telemetry_errors": telemetry_errors,
    }
    result.update(time_metrics)
    result.update(gpu_metrics_payload)
    return result


def _exception_mode_result(
    namespace: str,
    mode: str,
    contract: str,
    command: list[str],
    exc: Exception,
) -> dict[str, object]:
    return {
        "artifact_namespace": namespace,
        "mode": mode,
        "contract": contract,
        "command": command,
        "returncode": 125,
        "timed_out": False,
        "wall_seconds": "NA",
        "time_available": Path("/usr/bin/time").is_file(),
        "report_available": False,
        "report_error": f"exception:{type(exc).__name__}:{exc}",
        "result_status": "technical_failure",
        "published_source": "NA",
        "fallback_count": 0,
        "oom_count": 0,
        "reported_timeout_count": 0,
        "report_validation_status": "invalid",
        "telemetry_errors": [f"mode_exception:{type(exc).__name__}"],
        "time_telemetry_available": False,
        "time_telemetry_status": "unavailable",
        "time_telemetry_reason": "mode_exception",
        "max_rss_kb": "NA",
        "gpu_telemetry_available": False,
        "gpu_telemetry_status": "unavailable",
        "gpu_telemetry_reason": "mode_exception",
        "gpu_sample_count": 0,
        "gpu_memory_peak_mib": "NA",
        "gpu_utilization_peak_percent": "NA",
        "gpu_temperature_peak_c": "NA",
        "gpu_power_peak_w": "NA",
        "gpu_sm_clock_peak_mhz": "NA",
    }


def _single_raw_output(mode_dir: Path) -> tuple[Path | None, str | None]:
    output = mode_dir / "output"
    if output.is_symlink():
        return None, "raw_output_directory_is_symlink"
    if output.is_dir():
        symlinks = sorted(path for path in output.rglob("*") if path.is_symlink())
        if symlinks:
            return None, f"raw_output_tree_contains_symlink:{symlinks[0]}"
    candidates = sorted(
        path for path in output.rglob("*TFOsorted*") if path.is_file()
    ) if output.is_dir() else []
    if len(candidates) != 1:
        return None, f"expected_one_raw_TFOsorted_found_{len(candidates)}"
    return candidates[0], None


def _parse_comparator_metrics(stdout: str) -> dict[str, object]:
    raw: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw[key] = value
    missing = [field for field in COMPARATOR_REQUIRED_METRICS if field not in raw]
    if missing:
        raise ValueError("comparator output missing metrics: " + ",".join(missing))
    metrics: dict[str, object] = {}
    for key, value in raw.items():
        if key in COMPARATOR_REQUIRED_METRICS:
            try:
                metrics[key] = int(value)
            except ValueError as exc:
                raise ValueError(f"comparator metric is not an integer: {key}={value}") from exc
    return metrics


def _validate_comparator_details(
    path: Path, baseline: Path, candidate: Path, k: int
) -> None:
    require(path.is_file() and not path.is_symlink(), "comparator details are missing or symlinked")
    contracts = {
        "baseline": _analyze(baseline, k, 15, 50),
        "candidate": _analyze(candidate, k, 15, 50),
    }
    observed: list[tuple[str, str, str, int, str, tuple[str, ...]]] = []
    seen: set[tuple[str, str, str, int]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(
            tuple(reader.fieldnames or ()) == COMPARATOR_DETAILS_SCHEMA,
            "comparator details schema mismatch",
        )
        for line_number, row in enumerate(reader, start=2):
            require(
                None not in row and all(value is not None for value in row.values()),
                f"malformed comparator details row {line_number}",
            )
            side = row["side"]
            kind = row["kind"]
            mode = row["mode"]
            require(side in contracts, f"invalid comparator details side at row {line_number}")
            require(kind in {"raw", "clustered"}, f"invalid comparator details kind at row {line_number}")
            require(mode in RANKING_MODES, f"invalid comparator details mode at row {line_number}")
            try:
                rank = int(row["rank"])
            except ValueError as exc:
                raise ValueError(f"invalid comparator details rank at row {line_number}") from exc
            require(1 <= rank <= k, f"comparator details rank outside 1..{k} at row {line_number}")
            key = (side, kind, mode, rank)
            require(key not in seen, f"duplicate comparator details rank group at row {line_number}")
            seen.add(key)
            cluster_id = row["cluster_id"]
            if kind == "raw":
                require(cluster_id == "NA", f"raw comparator details cluster ID must be NA at row {line_number}")
            else:
                try:
                    parsed_cluster_id = int(cluster_id)
                except ValueError as exc:
                    raise ValueError(f"invalid clustered comparator details cluster ID at row {line_number}") from exc
                require(parsed_cluster_id > 0, f"invalid clustered comparator details cluster ID at row {line_number}")
            full_row = tuple(row[column] for column in TFOSORTED_COLUMNS)
            require(
                full_row in contracts[side].row_keys,
                f"comparator details row is absent from {side} source at row {line_number}",
            )
            observed.append((side, kind, mode, rank, cluster_id, full_row))

    expected: list[tuple[str, str, str, int, str, tuple[str, ...]]] = []
    for side, contract in contracts.items():
        for mode in RANKING_MODES:
            for rank, row in enumerate(contract.raw_top_rows[mode], start=1):
                expected.append(
                    (side, "raw", mode, rank, "NA", tuple(row[column] for column in TFOSORTED_COLUMNS))
                )
            for rank, (cluster_id, row) in enumerate(
                contract.clustered_top_rows[mode], start=1
            ):
                expected.append(
                    (
                        side,
                        "clustered",
                        mode,
                        rank,
                        str(cluster_id),
                        tuple(row[column] for column in TFOSORTED_COLUMNS),
                    )
                )
    require(observed == expected, "comparator details are incomplete, noncontiguous, or out of order")


def _compare_output_paths(
    baseline: Path,
    candidate: Path,
    comparator_dir: Path,
    snapshot: ExecutionSnapshot,
    execution_identity: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    comparator_dir.mkdir()
    details = comparator_dir / "details.tsv"
    stdout_path = comparator_dir / "stdout.log"
    stderr_path = comparator_dir / "stderr.log"
    command = [
        sys.executable,
        str(snapshot.tools.comparator.resolve()),
        "--baseline",
        str(baseline),
        "--candidate",
        str(candidate),
        "--k",
        "5",
        "--details",
        str(details),
    ]
    measured = _run_captured(
        command,
        stdout_path,
        stderr_path,
        timeout_seconds,
        snapshot=snapshot,
        execution_identity=execution_identity,
    )
    if not details.exists():
        _write_fsynced(details, b"")
    result: dict[str, object] = {
        "command": command,
        "baseline_path": str(baseline),
        "candidate_path": str(candidate),
        "comparator_returncode": measured["returncode"],
        "timed_out": measured["timed_out"],
        "wall_seconds": measured["wall_seconds"],
        "metrics": {},
    }
    try:
        _validate_comparator_details(details, baseline, candidate, 5)
    except (OSError, UnicodeError, ValueError) as exc:
        result.update(status="technical_failure", reason=f"invalid_comparator_details:{exc}")
        return result
    if measured["timed_out"]:
        result.update(status="technical_failure", reason="comparator_timeout")
        return result
    if measured["returncode"] not in {0, 1}:
        result.update(status="technical_failure", reason="unsupported_comparator_returncode")
        return result
    try:
        result["metrics"] = _parse_comparator_metrics(stdout_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        result.update(status="technical_failure", reason=f"invalid_comparator_output:{exc}")
        return result
    metrics = result["metrics"]
    if any(type(metrics[field]) is not int or metrics[field] not in {0, 1} for field in COMPARATOR_BINARY_METRICS):
        result.update(
            status="technical_failure",
            reason="nonbinary_comparator_metric",
            declared_contract_clean=False,
        )
        return result
    if any(type(metrics[field]) is not int or metrics[field] < 0 for field in COMPARATOR_COUNT_METRICS):
        result.update(
            status="technical_failure",
            reason="negative_or_invalid_comparator_count",
            declared_contract_clean=False,
        )
        return result
    full_truth_clean = (
        metrics["full_missing_rows"] == 0
        and metrics["full_extra_rows"] == 0
        and all(metrics[field] == 1 for field in COMPARATOR_BINARY_METRICS)
    )
    if (measured["returncode"] == 0) != full_truth_clean:
        result.update(
            status="technical_failure",
            reason="comparator_returncode_truth_mismatch",
            declared_contract_clean=False,
        )
        return result
    declared_gate_fields = (
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "boundary_ties_equal",
    )
    clustered_all = all(
        metrics[field] == 1
        for field in declared_gate_fields[:3]
    )
    if metrics["all_three_top5_equal"] != int(clustered_all):
        result.update(
            status="technical_failure",
            reason="inconsistent_clustered_gate_metrics",
            declared_contract_clean=False,
        )
        return result
    declared_contract_clean = clustered_all and metrics["boundary_ties_equal"] == 1
    result["declared_contract"] = "all-ranked-top5"
    result["declared_contract_clean"] = declared_contract_clean
    if measured["returncode"] == 0 and not declared_contract_clean:
        result.update(status="technical_failure", reason="inconsistent_clean_returncode")
        return result
    result.update(
        status="clean" if declared_contract_clean else "mismatch",
        reason="evaluated",
    )
    return result


def _compare_direct_outputs(
    partial: Path,
    snapshot: ExecutionSnapshot,
    execution_identity: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    comparator_dir = partial / "comparator"
    authority, authority_error = _single_raw_output(partial / "authority")
    candidate, candidate_error = _single_raw_output(partial / "candidate")
    if authority is None or candidate is None:
        comparator_dir.mkdir()
        for name in ("details.tsv", "stdout.log", "stderr.log"):
            _write_fsynced(comparator_dir / name, b"")
        return {
            "status": "technical_failure",
            "reason": ";".join(filter(None, (authority_error, candidate_error))),
            "baseline_path": str(authority) if authority else "NA",
            "candidate_path": str(candidate) if candidate else "NA",
            "comparator_returncode": "NA",
            "timed_out": False,
            "metrics": {},
        }
    return _compare_output_paths(
        authority,
        candidate,
        comparator_dir,
        snapshot,
        execution_identity,
        timeout_seconds,
    )


def _verified_nested_declared_contract(report: dict[str, object]) -> bool | None:
    nested = report.get("comparators")
    if not isinstance(nested, dict) or nested.get("status") not in {"clean", "mismatch"}:
        return None
    fields = (
        "score_top5_equal",
        "stability_top5_equal",
        "nt_top5_equal",
        "boundary_ties_equal",
    )
    if any(type(nested.get(field)) is not bool for field in fields):
        return None
    return all(nested[field] for field in fields)


def _capture_environment(
    partial: Path,
    snapshot: ExecutionSnapshot,
    execution_identity: dict[str, object],
) -> str | None:
    output = partial / "environment.json"
    validate_execution_snapshot(snapshot, execution_identity)
    try:
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(snapshot.tools.environment_capture.resolve()),
                    "--output",
                    str(output),
                ],
                cwd=partial,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except OSError as exc:
            write_json(output, {"schema_version": 1, "capture_status": "technical_failure", "error": type(exc).__name__})
            return f"environment_capture:{type(exc).__name__}"
        try:
            stdout, stderr = process.communicate(timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            _kill_process_group(process)
            try:
                process.communicate()
            except (OSError, ValueError):
                pass
            write_json(output, {"schema_version": 1, "capture_status": "technical_failure", "error": type(exc).__name__})
            return f"environment_capture:{type(exc).__name__}"
        except BaseException:
            _kill_process_group(process)
            process.communicate()
            raise
        if process.returncode != 0 or not output.is_file():
            write_json(
                output,
                {
                    "schema_version": 1,
                    "capture_status": "technical_failure",
                    "returncode": process.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                },
            )
            return "environment_capture:nonzero_or_missing"
        return None
    finally:
        validate_execution_snapshot(snapshot, execution_identity)


def _artifact_rows(partial: Path) -> list[dict[str, object]]:
    excluded = {"attempt-artifacts.tsv", "attempt-complete.json"}
    rows: list[dict[str, object]] = []
    entries = sorted(partial.rglob("*"))
    symlinks = [path for path in entries if path.is_symlink()]
    require(not symlinks, f"attempt artifact tree contains symlink: {symlinks[0] if symlinks else 'NA'}")
    for path in (item for item in entries if item.is_file()):
        relative = str(path.relative_to(partial))
        if relative in excluded:
            continue
        rows.append(
            {
                "artifact_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def _publish_attempt_receipt(
    partial: Path,
    destination: Path,
    config: dict[str, object],
    summary: dict[str, object],
    execution_identity: dict[str, object],
    snapshot: ExecutionSnapshot,
) -> None:
    write_json(partial / "attempt-summary.json", summary)
    artifact_rows = _artifact_rows(partial)
    write_tsv(
        partial / "attempt-artifacts.tsv",
        ("artifact_path", "size_bytes", "sha256"),
        artifact_rows,
    )
    receipt = {
        "schema_version": 1,
        "status": "complete",
        "attempt_id": summary["attempt_id"],
        "outcome": summary["outcome"],
        "config_digest_sha256": config["config_digest_sha256"],
        "config_sha256": sha256_file(partial / "attempt-config.json"),
        "summary_sha256": sha256_file(partial / "attempt-summary.json"),
        "artifact_manifest_sha256": sha256_file(partial / "attempt-artifacts.tsv"),
        "artifact_count": len(artifact_rows),
    }
    write_json(partial / "attempt-complete.json", receipt)
    _fsync_tree(partial)
    validate_execution_identity(execution_identity)
    validate_execution_snapshot(snapshot, execution_identity)
    os.rename(partial, destination)
    _fsync_directory(destination.parent)


def _read_canonical_json(path: Path, label: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is missing or invalid: {path}") from exc
    require(isinstance(payload, dict), f"{label} must be a JSON object")
    canonical = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    require(raw == canonical, f"{label} is not canonical; possible tampering: {path}")
    return payload


def _read_artifact_manifest(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            require(
                tuple(reader.fieldnames or ()) == ("artifact_path", "size_bytes", "sha256"),
                "attempt artifact manifest schema drift",
            )
            rows = []
            for line_number, row in enumerate(reader, start=2):
                require(None not in row and all(value is not None for value in row.values()), f"malformed artifact manifest row {line_number}")
                rows.append(dict(row))
    except OSError as exc:
        raise ValueError(f"attempt artifact manifest is missing: {path}") from exc
    return rows


def validate_attempt_receipt(
    attempt_dir: Path,
    expected_config: dict[str, object] | None = None,
    *,
    expected_parent: Path | None = None,
    expected_attempt_id: str | None = None,
) -> dict[str, object]:
    """Fail closed unless an immutable attempt directory is internally complete."""

    unresolved_attempt_dir = attempt_dir.absolute()
    require(not unresolved_attempt_dir.is_symlink(), f"attempt directory may not be a symlink: {unresolved_attempt_dir}")
    if expected_parent is not None:
        require(
            unresolved_attempt_dir.parent.resolve() == expected_parent.resolve(),
            "attempt directory is outside expected parent containment",
        )
    if expected_attempt_id is not None:
        require(
            unresolved_attempt_dir.name == expected_attempt_id,
            "attempt directory ID does not match expected containment",
        )
    require(unresolved_attempt_dir.is_dir(), f"missing attempt directory: {unresolved_attempt_dir}")
    symlinks = sorted(path for path in unresolved_attempt_dir.rglob("*") if path.is_symlink())
    require(not symlinks, f"attempt receipt tree contains symlink: {symlinks[0] if symlinks else 'NA'}")
    attempt_dir = unresolved_attempt_dir.resolve()
    config_path = attempt_dir / "attempt-config.json"
    summary_path = attempt_dir / "attempt-summary.json"
    manifest_path = attempt_dir / "attempt-artifacts.tsv"
    receipt_path = attempt_dir / "attempt-complete.json"
    config = _read_canonical_json(config_path, "attempt config")
    summary = _read_canonical_json(summary_path, "attempt summary")
    receipt = _read_canonical_json(receipt_path, "attempt complete receipt")
    required_receipt_fields = {
        "schema_version",
        "status",
        "attempt_id",
        "outcome",
        "config_digest_sha256",
        "config_sha256",
        "summary_sha256",
        "artifact_manifest_sha256",
        "artifact_count",
    }
    require(set(receipt) == required_receipt_fields, "attempt receipt schema drift or tampering")
    require(receipt["schema_version"] == 1 and receipt["status"] == "complete", "attempt receipt is incomplete")
    config_without_digest = dict(config)
    observed_config_digest = config_without_digest.pop("config_digest_sha256", None)
    require(
        observed_config_digest == canonical_digest(config_without_digest),
        "attempt config digest mismatch or tampering",
    )
    require(
        receipt["config_digest_sha256"] == observed_config_digest,
        "receipt/config digest mismatch or tampering",
    )
    if expected_config is not None:
        require(config == expected_config, "resume config digest mismatch")
    require(receipt["config_sha256"] == sha256_file(config_path), "attempt config checksum mismatch")
    require(receipt["summary_sha256"] == sha256_file(summary_path), "attempt summary checksum mismatch")
    require(receipt["artifact_manifest_sha256"] == sha256_file(manifest_path), "artifact manifest checksum mismatch")
    require(receipt["attempt_id"] == summary.get("attempt_id"), "receipt attempt ID mismatch")
    require(receipt["outcome"] == summary.get("outcome"), "receipt outcome mismatch")
    require(receipt["attempt_id"] == config.get("attempt", {}).get("attempt_id"), "receipt/config attempt ID mismatch")

    artifact_rows = _read_artifact_manifest(manifest_path)
    require(len(artifact_rows) == receipt["artifact_count"], "artifact count mismatch")
    paths = [row["artifact_path"] for row in artifact_rows]
    require(len(paths) == len(set(paths)), "duplicate attempt artifact path")
    for row in artifact_rows:
        relative = Path(row["artifact_path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe attempt artifact path")
        path = (attempt_dir / relative).resolve()
        try:
            path.relative_to(attempt_dir)
        except ValueError as exc:
            raise ValueError("attempt artifact path escapes receipt directory") from exc
        require(path.is_file() and not path.is_symlink(), f"missing retained artifact: {relative}")
        require(str(path.stat().st_size) == row["size_bytes"], f"artifact size mismatch or tampering: {relative}")
        require(_is_sha256(row["sha256"]), f"invalid artifact checksum: {relative}")
        require(sha256_file(path) == row["sha256"], f"artifact checksum mismatch or tampering: {relative}")
    observed = {
        str(path.relative_to(attempt_dir))
        for path in attempt_dir.rglob("*")
        if path.is_file()
    }
    expected = set(paths) | {"attempt-artifacts.tsv", "attempt-complete.json"}
    require(observed == expected, "attempt artifact set mismatch or unrecorded tampering")
    return {
        "config": config,
        "summary": summary,
        "receipt": receipt,
        "artifacts": artifact_rows,
        "receipt_sha256": sha256_file(receipt_path),
    }


def reject_stale_attempt_partials(destination_parent: Path, attempt_id: str) -> None:
    stale = sorted(destination_parent.glob(f".{attempt_id}.partial.*"))
    if stale:
        rendered = ",".join(str(path) for path in stale)
        raise ValueError(
            "stale primary-attempt partial requires manual adjudication; "
            f"preserved without cleanup or replacement: {rendered}"
        )


def validate_artifact_root_components(artifact_root: Path, trusted_root: Path = ROOT) -> None:
    trusted = Path(os.path.abspath(trusted_root))
    candidate = Path(os.path.abspath(artifact_root))
    try:
        relative = candidate.relative_to(trusted)
    except ValueError as exc:
        raise ValueError("artifact root is outside trusted repository containment") from exc
    current = trusted
    require(not current.is_symlink(), f"artifact root component is a symlink: {current}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"artifact root component is a symlink: {current}")
    try:
        candidate.resolve().relative_to(trusted.resolve())
    except ValueError as exc:
        raise ValueError("artifact root resolves outside trusted repository containment") from exc


def execution_start_markers(artifact_root: Path = CANONICAL_ARTIFACT_ROOT) -> list[Path]:
    artifact_root = artifact_root.resolve()
    if not artifact_root.exists():
        return []
    markers = [artifact_root]
    if artifact_root.is_dir():
        markers.extend(sorted(artifact_root.rglob("*")))
    return markers


def execute_attempt(
    *,
    attempt: dict[str, object],
    manifest: Path,
    destination_parent: Path,
    tools: ExecutionTools,
    resume: bool,
    outer_timeouts: dict[str, float] | None = None,
    execution_identity: dict[str, object] | None = None,
) -> dict[str, object]:
    """Execute one primary or pilot attempt and publish one immutable receipt."""

    manifest = manifest.resolve()
    repository_root = _repository_root(manifest)
    attempt_id = str(attempt["attempt_id"])
    require(Path(attempt_id).name == attempt_id and attempt_id not in {".", ".."}, "unsafe attempt ID")
    destination_parent = destination_parent.resolve()
    reject_stale_attempt_partials(destination_parent, attempt_id)
    if execution_identity is None:
        execution_identity = capture_execution_identity(manifest, tools, [attempt])
    validate_execution_identity(execution_identity)
    config = attempt_config(attempt, manifest, tools, execution_identity)
    destination = destination_parent / attempt_id
    if destination.exists():
        if not resume:
            raise ValueError(f"attempt destination already exists; duplicate attempt: {destination}")
        validated = validate_attempt_receipt(
            destination,
            config,
            expected_parent=destination_parent,
            expected_attempt_id=attempt_id,
        )
        return {
            "status": "reused",
            "attempt_id": attempt_id,
            "attempt_dir": str(destination),
            "outcome": validated["summary"]["outcome"],
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.parent / f".{attempt_id}.partial.{os.getpid()}"
    require(not partial.exists(), f"partial attempt directory already exists: {partial}")
    partial.mkdir()
    snapshot = create_execution_snapshot(partial, attempt, execution_identity)
    validate_execution_identity(execution_identity)
    write_json(partial / "attempt-config.json", config)
    failure_reasons: list[str] = []
    validate_execution_identity(execution_identity)
    environment_failure = _capture_environment(
        partial, snapshot, execution_identity
    )
    validate_execution_identity(execution_identity)
    if environment_failure:
        failure_reasons.append(environment_failure)

    timeouts = dict(MODE_OUTER_TIMEOUT_SECONDS)
    if outer_timeouts is not None:
        timeouts.update(outer_timeouts)
    mode_results: list[dict[str, object]] = []
    for namespace, mode, contract in MODE_LAYOUT:
        validate_execution_identity(execution_identity)
        command = _mode_command(
            snapshot.tools,
            namespace,
            mode,
            contract,
            attempt,
            snapshot.query,
            snapshot.target,
            partial / namespace,
        )
        try:
            result = _run_mode(
                namespace,
                mode,
                contract,
                attempt,
                partial,
                snapshot,
                execution_identity,
                float(timeouts[mode]),
            )
        except Exception as exc:
            mode_dir = partial / namespace
            mode_dir.mkdir(parents=True, exist_ok=True)
            (mode_dir / "output").mkdir(exist_ok=True)
            for name in ("stdout.log", "stderr.log", "time.txt", "gpu-memory.csv"):
                path = mode_dir / name
                if not path.exists():
                    _write_fsynced(path, b"")
            result = _exception_mode_result(namespace, mode, contract, command, exc)
            failure_reasons.append("mode_exception")
        validate_execution_identity(execution_identity)
        validate_execution_snapshot(snapshot, execution_identity)
        mode_results.append(result)
        if result["timed_out"]:
            failure_reasons.append("timeout")
        if result["returncode"] != 0:
            failure_reasons.append("mode_failure")
        if not result["report_available"] and not result["timed_out"]:
            failure_reasons.append("mode_report_missing")
        if result["report_validation_status"] == "invalid":
            failure_reasons.append("mode_report_invalid")
        if result["telemetry_errors"]:
            failure_reasons.append("mode_telemetry_failure")

    validate_execution_identity(execution_identity)
    try:
        comparison = _compare_direct_outputs(
            partial,
            snapshot,
            execution_identity,
            max(float(timeouts["cpu-authority"]), BACKEND_TIMEOUT_SECONDS + 120),
        )
    except Exception as exc:
        comparator_dir = partial / "comparator"
        comparator_dir.mkdir(exist_ok=True)
        for name in ("details.tsv", "stdout.log", "stderr.log"):
            path = comparator_dir / name
            if not path.exists():
                _write_fsynced(path, b"")
        comparison = {
            "status": "technical_failure",
            "reason": f"comparator_exception:{type(exc).__name__}:{exc}",
            "baseline_path": "NA",
            "candidate_path": "NA",
            "comparator_returncode": "NA",
            "timed_out": False,
            "metrics": {},
        }
    validate_execution_identity(execution_identity)
    validate_execution_snapshot(snapshot, execution_identity)
    write_json(partial / "comparison.json", comparison)
    if comparison["status"] == "technical_failure":
        failure_reasons.append("comparator_failure")

    verified = next(row for row in mode_results if row["mode"] == "verified")
    verified_report, _ = _read_report(partial / "verified/report.json")
    nested_declared = (
        _verified_nested_declared_contract(verified_report)
        if verified_report is not None and verified["report_validation_status"] == "valid"
        else None
    )
    direct_declared = comparison.get("declared_contract_clean")
    direct_vs_verified_consistent: bool | str = "NA"
    if type(nested_declared) is bool and type(direct_declared) is bool:
        direct_vs_verified_consistent = nested_declared == direct_declared
        if not direct_vs_verified_consistent:
            failure_reasons.append("verified_direct_contract_disagreement")

    verified_fallback = str(verified["result_status"]).startswith("cpu_fallback_after_")
    if verified_fallback and verified["report_validation_status"] == "valid":
        evidence_dir = partial / "verified-evidence"
        authority_raw, authority_error = _single_raw_output(partial / "authority")
        verified_raw, verified_error = _single_raw_output(partial / "verified")
        if authority_raw is None or verified_raw is None:
            evidence_dir.mkdir()
            for name in ("details.tsv", "stdout.log", "stderr.log"):
                _write_fsynced(evidence_dir / name, b"")
            verified_evidence = {
                "status": "technical_failure",
                "reason": ";".join(filter(None, (authority_error, verified_error))),
                "baseline_path": str(authority_raw) if authority_raw else "NA",
                "candidate_path": str(verified_raw) if verified_raw else "NA",
                "comparator_returncode": "NA",
                "timed_out": False,
                "metrics": {},
            }
        else:
            validate_execution_identity(execution_identity)
            try:
                verified_evidence = _compare_output_paths(
                    authority_raw,
                    verified_raw,
                    evidence_dir,
                    snapshot,
                    execution_identity,
                    max(float(timeouts["cpu-authority"]), BACKEND_TIMEOUT_SECONDS + 120),
                )
            except Exception as exc:
                evidence_dir.mkdir(exist_ok=True)
                for name in ("details.tsv", "stdout.log", "stderr.log"):
                    path = evidence_dir / name
                    if not path.exists():
                        _write_fsynced(path, b"")
                verified_evidence = {
                    "status": "technical_failure",
                    "reason": f"verified_evidence_exception:{type(exc).__name__}:{exc}",
                    "baseline_path": str(authority_raw),
                    "candidate_path": str(verified_raw),
                    "comparator_returncode": "NA",
                    "timed_out": False,
                    "metrics": {},
                }
            validate_execution_identity(execution_identity)
            validate_execution_snapshot(snapshot, execution_identity)
        write_json(evidence_dir / "comparison.json", verified_evidence)
        if verified_evidence["status"] == "technical_failure":
            failure_reasons.append("verified_fallback_evidence_failure")
        elif (
            verified_evidence["metrics"].get("full_missing_rows") != 0
            or verified_evidence["metrics"].get("full_extra_rows") != 0
        ):
            failure_reasons.append("verified_fallback_artifact_mismatch")

    fallback_count = sum(int(row["fallback_count"]) for row in mode_results)
    oom_count = sum(int(row["oom_count"]) for row in mode_results)
    timeout_count = sum(
        int(bool(row["timed_out"])) + int(row["reported_timeout_count"])
        for row in mode_results
    )
    fallback_consistent = verified_fallback == (int(verified["fallback_count"]) > 0)
    if verified_fallback and verified["published_source"] != "authority":
        fallback_consistent = False
    if not fallback_consistent:
        failure_reasons.append("verified_fallback_inconsistent")
    instability_reason = "verified_direct_contract_disagreement"
    technical_reasons = [reason for reason in failure_reasons if reason != instability_reason]
    if technical_reasons:
        outcome = "technical_failure"
    elif instability_reason in failure_reasons:
        outcome = "scientific_instability"
    elif comparison["status"] == "mismatch":
        outcome = "scientific_mismatch"
    else:
        outcome = "complete"
    summary = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "workload_id": attempt["workload_id"],
        "repeat_index": attempt["repeat_index"],
        "outcome": outcome,
        "scientific_comparison_status": comparison["status"],
        "failure_reasons": list(dict.fromkeys(failure_reasons)),
        "fallback_count": fallback_count,
        "oom_count": oom_count,
        "timeout_count": timeout_count,
        "verified_result_status": verified["result_status"],
        "verified_published_source": verified["published_source"],
        "verified_fallback_consistent": fallback_consistent,
        "verified_nested_declared_contract_clean": nested_declared if nested_declared is not None else "NA",
        "direct_vs_verified_declared_contract_consistent": direct_vs_verified_consistent,
        "mode_results": mode_results,
    }
    _publish_attempt_receipt(
        partial,
        destination,
        config,
        summary,
        execution_identity,
        snapshot,
    )
    return {"status": "executed", "attempt_id": attempt_id, "attempt_dir": str(destination), "outcome": outcome}


def capture_plan_execution_identity(
    plan: dict[str, object], manifest: Path, tools: ExecutionTools
) -> dict[str, object]:
    pilot = plan.get("pilot")
    attempts = plan.get("formal_attempts")
    require(isinstance(pilot, dict), "plan is missing pilot execution identity input")
    require(isinstance(attempts, list), "plan is missing formal execution identity inputs")
    require(all(isinstance(attempt, dict) for attempt in attempts), "plan execution identity attempt is invalid")
    identity = capture_execution_identity(manifest, tools, [pilot, *attempts])
    require(
        identity["manifest"]["sha256"] == plan.get("manifest_sha256"),
        "execution identity manifest digest drift from plan",
    )
    return identity


def run_pilot(
    *,
    plan: dict[str, object],
    manifest: Path,
    artifact_root: Path,
    tools: ExecutionTools,
    resume: bool,
) -> dict[str, object]:
    pilot = plan.get("pilot")
    require(isinstance(pilot, dict), "plan is missing the fixed pilot")
    require(
        pilot.get("attempt_id") == "pilot__hq01_ht01__repeat00"
        and pilot.get("workload_id") == PILOT_WORKLOAD_ID,
        "pilot identity drift",
    )
    execution_identity = capture_plan_execution_identity(plan, manifest, tools)
    return execute_attempt(
        attempt=pilot,
        manifest=manifest,
        destination_parent=artifact_root.resolve() / "pilot",
        tools=tools,
        resume=resume,
        execution_identity=execution_identity,
    )


def publish_formal_tables_transactionally(
    root: Path,
    outputs: dict[str, bytes],
    after_replace: Callable[[int, str], None] | None = None,
    execution_identity: dict[str, object] | None = None,
) -> None:
    root = root.absolute()
    require(root.is_dir() and not root.is_symlink(), f"formal table root is invalid or symlinked: {root}")
    require(set(outputs) == set(FORMAL_TABLE_NAMES), "formal table transaction output set drift")
    require(all(type(outputs[name]) is bytes for name in FORMAL_TABLE_NAMES), "formal table transaction outputs must be bytes")

    transaction = root / f".formal-tables.transaction.{os.getpid()}"
    require(not transaction.exists() and not transaction.is_symlink(), f"formal table transaction already exists: {transaction}")
    staged = transaction / "staged"
    backups = transaction / "backups"
    staged.mkdir(parents=True)
    backups.mkdir()
    _fsync_directory(root)

    replaced: list[str] = []
    backed_up: set[str] = set()
    try:
        for name in FORMAL_TABLE_NAMES:
            _write_fsynced(staged / name, outputs[name])
        _fsync_directory(staged)

        for name in FORMAL_TABLE_NAMES:
            destination = root / name
            require(not destination.is_symlink(), f"formal table destination may not be a symlink: {destination}")
            if destination.exists():
                require(destination.is_file(), f"formal table destination is not regular: {destination}")
                _write_fsynced(backups / name, destination.read_bytes())
                backed_up.add(name)
        _fsync_directory(backups)
        _fsync_directory(transaction)

        for index, name in enumerate(FORMAL_TABLE_NAMES, start=1):
            if execution_identity is not None:
                validate_execution_identity(execution_identity)
            os.replace(staged / name, root / name)
            replaced.append(name)
            _fsync_directory(root)
            if after_replace is not None:
                after_replace(index, name)
    except BaseException:
        try:
            for name in reversed(replaced):
                destination = root / name
                if name in backed_up:
                    os.replace(backups / name, destination)
                elif destination.exists() or destination.is_symlink():
                    destination.unlink()
                _fsync_directory(root)
        except BaseException as rollback_error:
            raise RuntimeError(
                f"formal table rollback failed; transaction preserved: {transaction}"
            ) from rollback_error
        shutil.rmtree(transaction)
        _fsync_directory(root)
        raise
    shutil.rmtree(transaction)
    _fsync_directory(root)


def rebuild_formal_tables(
    *,
    plan: dict[str, object],
    manifest: Path,
    artifact_root: Path,
    tools: ExecutionTools,
    execution_identity: dict[str, object] | None = None,
) -> dict[str, object]:
    attempts = plan.get("formal_attempts")
    require(isinstance(attempts, list), "plan formal attempts are invalid")
    if execution_identity is None:
        execution_identity = capture_plan_execution_identity(plan, manifest, tools)
    artifact_root = artifact_root.resolve()
    formal_root = artifact_root / "formal"
    artifact_root.mkdir(parents=True, exist_ok=True)
    attempt_rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    artifact_rows: list[dict[str, object]] = []
    missing: list[str] = []
    outcomes: dict[str, int] = {}
    for attempt in attempts:
        require(isinstance(attempt, dict), "formal attempt entry is invalid")
        attempt_id = str(attempt["attempt_id"])
        attempt_dir = formal_root / attempt_id
        if not attempt_dir.exists():
            missing.append(attempt_id)
            continue
        expected_config = attempt_config(
            attempt, manifest.resolve(), tools, execution_identity
        )
        validated = validate_attempt_receipt(
            attempt_dir,
            expected_config,
            expected_parent=formal_root,
            expected_attempt_id=attempt_id,
        )
        summary = validated["summary"]
        receipt = validated["receipt"]
        outcome = str(summary["outcome"])
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        attempt_rows.append(
            {
                "attempt_id": attempt_id,
                "workload_id": summary["workload_id"],
                "repeat_index": summary["repeat_index"],
                "outcome": outcome,
                "fallback_count": summary["fallback_count"],
                "oom_count": summary["oom_count"],
                "timeout_count": summary["timeout_count"],
                "receipt_path": str(Path("formal") / attempt_id / "attempt-complete.json"),
                "receipt_sha256": validated["receipt_sha256"],
                "config_digest_sha256": receipt["config_digest_sha256"],
            }
        )
        if outcome != "complete":
            failure_rows.append(
                {
                    "attempt_id": attempt_id,
                    "workload_id": summary["workload_id"],
                    "failure_type": outcome,
                    "failure_reasons": ";".join(summary["failure_reasons"]) or "evaluated_mismatch",
                    "receipt_path": str(Path("formal") / attempt_id / "attempt-complete.json"),
                }
            )
        for row in validated["artifacts"]:
            artifact_rows.append(
                {
                    "attempt_id": attempt_id,
                    "artifact_path": str(Path("formal") / attempt_id / row["artifact_path"]),
                    "size_bytes": row["size_bytes"],
                    "sha256": row["sha256"],
                }
            )
        for name in ("attempt-artifacts.tsv", "attempt-complete.json"):
            path = attempt_dir / name
            artifact_rows.append(
                {
                    "attempt_id": attempt_id,
                    "artifact_path": str(Path("formal") / attempt_id / name),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    formal_summary = {
        "schema_version": 1,
        "freeze_id": plan["freeze_id"],
        "planned_attempt_count": len(attempts),
        "represented_attempt_count": len(attempt_rows),
        "missing_attempt_count": len(missing),
        "missing_attempt_ids": missing,
        "outcome_counts": dict(sorted(outcomes.items())),
        "complete_representation": len(attempt_rows) == len(attempts),
    }
    outputs = {
        "formal-attempts.tsv": _tsv_bytes(
            (
                "attempt_id",
                "workload_id",
                "repeat_index",
                "outcome",
                "fallback_count",
                "oom_count",
                "timeout_count",
                "receipt_path",
                "receipt_sha256",
                "config_digest_sha256",
            ),
            attempt_rows,
        ),
        "formal-failures.tsv": _tsv_bytes(
            (
                "attempt_id",
                "workload_id",
                "failure_type",
                "failure_reasons",
                "receipt_path",
            ),
            failure_rows,
        ),
        "formal-artifacts.tsv": _tsv_bytes(
            ("attempt_id", "artifact_path", "size_bytes", "sha256"),
            artifact_rows,
        ),
        "formal-summary.json": _json_bytes(formal_summary),
    }
    publish_formal_tables_transactionally(
        artifact_root,
        outputs,
        execution_identity=execution_identity,
    )
    return formal_summary


def run_formal(
    *,
    plan: dict[str, object],
    manifest: Path,
    artifact_root: Path,
    tools: ExecutionTools,
    resume: bool,
) -> dict[str, object]:
    attempts = plan.get("formal_attempts")
    require(isinstance(attempts, list), "plan is missing formal attempts")
    require(len(attempts) == int(plan["formal_attempt_count"]), "formal plan representation count drift")
    attempt_ids = [str(attempt["attempt_id"]) for attempt in attempts]
    require(len(attempt_ids) == len(set(attempt_ids)), "formal plan contains duplicate attempt IDs")
    pilot = plan.get("pilot")
    require(isinstance(pilot, dict), "plan is missing pilot")
    execution_identity = capture_plan_execution_identity(plan, manifest, tools)
    pilot_dir = artifact_root.resolve() / "pilot" / "pilot__hq01_ht01__repeat00"
    expected_pilot_config = attempt_config(
        pilot, manifest.resolve(), tools, execution_identity
    )
    try:
        validate_attempt_receipt(
            pilot_dir,
            expected_pilot_config,
            expected_parent=artifact_root.resolve() / "pilot",
            expected_attempt_id="pilot__hq01_ht01__repeat00",
        )
    except ValueError as exc:
        raise ValueError(f"formal execution requires a checksum-valid pilot receipt: {exc}") from exc

    formal_root = artifact_root.resolve() / "formal"
    for attempt in attempts:
        reject_stale_attempt_partials(formal_root, str(attempt["attempt_id"]))
    for attempt in attempts:
        destination = formal_root / str(attempt["attempt_id"])
        if not destination.exists():
            continue
        if not resume:
            raise ValueError(f"formal primary attempt already exists; use --resume: {destination}")
        validate_attempt_receipt(
            destination,
            attempt_config(
                attempt, manifest.resolve(), tools, execution_identity
            ),
            expected_parent=formal_root,
            expected_attempt_id=str(attempt["attempt_id"]),
        )

    for attempt in attempts:
        execute_attempt(
            attempt=attempt,
            manifest=manifest,
            destination_parent=formal_root,
            tools=tools,
            resume=resume,
            execution_identity=execution_identity,
        )
        rebuild_formal_tables(
            plan=plan,
            manifest=manifest,
            artifact_root=artifact_root,
            tools=tools,
            execution_identity=execution_identity,
        )
    return rebuild_formal_tables(
        plan=plan,
        manifest=manifest,
        artifact_root=artifact_root,
        tools=tools,
        execution_identity=execution_identity,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    result.add_argument("--artifact-root", type=Path, default=CANONICAL_ARTIFACT_ROOT)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan-only", action="store_true")
    modes.add_argument("--pilot", action="store_true")
    modes.add_argument("--formal", action="store_true")
    result.add_argument("--resume", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if (args.pilot or args.formal) and args.artifact_root.resolve() != CANONICAL_ARTIFACT_ROOT.resolve():
            raise ValueError(
                "pilot/formal execution is pinned to canonical artifact root: "
                f"{CANONICAL_ARTIFACT_ROOT}"
            )
        if args.pilot or args.formal:
            validate_artifact_root_components(args.artifact_root, ROOT)
            changes = production_checkout_changes()
            if changes:
                raise ValueError(
                    "production pilot/formal execution requires a clean tracked and "
                    "untracked checkout; observed: " + " | ".join(changes)
                )
        plan = build_plan(args.manifest)
        if args.plan_only:
            if args.resume:
                raise ValueError("--resume is valid only with --pilot or --formal")
            json.dump(plan, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            return 0
        tools = ExecutionTools()
        if args.pilot:
            result = run_pilot(
                plan=plan,
                manifest=args.manifest,
                artifact_root=args.artifact_root,
                tools=tools,
                resume=args.resume,
            )
        else:
            result = run_formal(
                plan=plan,
                manifest=args.manifest,
                artifact_root=args.artifact_root,
                tools=tools,
                resume=args.resume,
            )
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        if args.formal and not result["complete_representation"]:
            return 3
        return 0
    except (OSError, ValueError) as exc:
        print(f"holdout runner error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
