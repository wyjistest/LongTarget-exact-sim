#!/usr/bin/env python3
"""Validate and summarize the immutable Bioinformatics Phase 2 holdout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable


FREEZE_ID = "bioinformatics-phase2-holdout-v1-9e293b2c"
MANIFEST_SHA256 = "9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6"
CHECKPOINT_COMMIT = "1c07823bc3a56704415d242b3ddc937cfa03ee86"
RUNNER_SHA256 = "6a1e3d5cc91dae5b9d03eaffbc02af347c7e80f2d385f08151fd061e9ffb813b"
EXECUTION_IDENTITY_SHA256 = "742b70d16f81a715debb1edc90802de5a3f2a4715ad578cebc84395d9393b7a9"
PILOT_RECEIPT_SHA256 = "d8636edb025da431ce4a97ec507d73955be0781d0cfcbdcbad847f8f542ec76d"
PAPER_RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
COMPARATOR_SHA256 = "6a589d7960a69be7c84a410f1bbd9d3ea34de929f8f04943d9c7ae033d682eda"
REPORT_SCHEMA_SHA256 = "fcf4831173746d31e8fd8105e1bf1fcc834b79a13e864d5009aa034de183399b"
RANKS = ("score", "stability", "nt")
OUTPUT_NAMES = (
    "holdout_attempt_results.tsv",
    "holdout_workload_results.tsv",
    "holdout_rank_results.tsv",
    "holdout_mode_results.tsv",
    "holdout_mismatch_details.tsv",
    "holdout_raw_artifacts.tsv",
    "holdout_summary.json",
    "phase2_decision.md",
)
MODE_PLAN = (
    ("authority", "cpu-authority", "all-ranked-top5", "all-ranked-top5", "cpu-authority"),
    ("candidate", "fast-experimental", "auto", "experimental-native", "fast-experimental"),
    ("verified", "verified", "all-ranked-top5", "all-ranked-top5", "verified"),
)
MODE_STATES = {
    "authority": {("authority_complete", "authority", 0)},
    "candidate": {("experimental_unverified", "candidate", 0)},
    "verified": {
        ("candidate_clean", "candidate", 0),
        ("cpu_fallback_after_mismatch", "authority", 1),
        ("cpu_fallback_after_candidate_failure", "authority", 1),
        ("cpu_fallback_after_comparator_failure", "authority", 1),
    },
}

MANIFEST_FIELDS = """workload_id query_id gene_id gene_name transcript_id query_length_nt length_stratum query_sequence_sha256 query_file_sha256 query_path target_id target_gene_id target_gene_name target_chromosome target_strand target_tss target_region_start target_region_end target_length_bp target_sequence_sha256 target_file_sha256 target_path assembly annotation_release selection_seed requested_contract run_modes repeat_count status""".split()
ATTEMPT_FIELDS = """attempt_id workload_id repeat_index outcome query_id target_id query_length_nt length_stratum score_equal stability_equal nt_equal all_ranked_equal full_row_equal baseline_rows candidate_rows full_missing_rows full_extra_rows boundary_ties_equal verified_fallback verified_result_status verified_published_source verified_publication_contract_safe fallback_count oom_count timeout_count receipt_path receipt_sha256 config_digest_sha256 execution_identity_sha256""".split()
WORKLOAD_FIELDS = """workload_id query_id target_id query_length_nt length_stratum repeat_count repeat_basis repeat_contract_consistent repeat_top5_signatures_consistent score_clean score_mismatch stability_clean stability_mismatch nt_clean nt_mismatch all_ranked_clean all_ranked_mismatch full_row_clean full_row_mismatch boundary_ties_clean verified_fallback_count oom_count timeout_count""".split()
RANK_FIELDS = """attempt_id workload_id repeat_index rank rank_equal differing_position_count differing_positions baseline_top5_count candidate_top5_count baseline_top5_signature candidate_top5_signature baseline_primary_values candidate_primary_values baseline_row_identities candidate_row_identities boundary_ties_equal""".split()
MODE_FIELDS = """attempt_id workload_id repeat_index artifact_namespace mode contract report_available report_validation_status result_status published_source returncode timed_out fallback_count oom_count timeout_count wall_seconds max_rss_kb gpu_telemetry_status gpu_memory_peak_mib gpu_temperature_peak_c gpu_power_peak_w""".split()

ROOT_ATTEMPT_FIELDS = """attempt_id workload_id repeat_index outcome fallback_count oom_count timeout_count receipt_path receipt_sha256 config_digest_sha256""".split()
ROOT_FAILURE_FIELDS = """attempt_id workload_id failure_type failure_reasons receipt_path""".split()
ROOT_ARTIFACT_FIELDS = """attempt_id artifact_path size_bytes sha256""".split()
ATTEMPT_ARTIFACT_FIELDS = """artifact_path size_bytes sha256""".split()

TFOSORTED_COLUMNS = (
    "QueryStart", "QueryEnd", "StartInSeq", "EndInSeq", "Direction", "Chr",
    "StartInGenome", "EndInGenome", "MeanStability", "MeanIdentity(%)",
    "Strand", "Rule", "Score", "Nt(bp)", "Class", "MidPoint", "Center",
    "TFO sequence", "TTS sequence",
)
DETAIL_FIELDS = [
    "attempt_id", "workload_id", "evidence_kind", "side", "kind", "mode",
    "rank", "cluster_id", *TFOSORTED_COLUMNS,
]

EXPECTED_TOOL_SHA256 = {
    "workflow": "42a1c90f9850d28b3e7226140362fa488fdcf46730e2d858cd540c8a0762b91c",
    "comparator": COMPARATOR_SHA256,
    "environment_capture": "49d9b40623fca1f818b5fb56a8645ae05e391b18203b44a38eb69c4003019b12",
    "authority_binary": "2dc13100233698d0031717c3609a0a6508dc8cc3a0b85568417426a3848eeb48",
    "candidate_binary": "584ff639e09ede813a645f6ef0927a183eadbf6c216a530c2ed998fe800e4759",
}
EXPECTED_SUPPORT_SHA256 = {
    "schemas/gasal2_longtarget_run_report.schema.json": REPORT_SCHEMA_SHA256,
    "scripts/compare_fasim_lite_offline_cluster_topk.py": "2765d76b6c8e742596b1072a413309a88ef415f3576c9de62be67213ee76dc80",
    "scripts/fasim_tfo_archive.py": "3fb42809c4f31b31ec05bcaf9d3249f4059a910164a6ca33d5a789fb0efab856",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ValueError(f"required artifact is missing: {path}") from exc
    return digest.hexdigest()


def canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path_has_suffix(value: object, *suffix: str) -> bool:
    if not isinstance(value, str):
        return False
    path = Path(value)
    return path.is_absolute() and path.parts[-len(suffix):] == suffix


def _regular_file_tree(root: Path, label: str) -> dict[str, Path]:
    try:
        root_metadata = root.lstat()
    except OSError as exc:
        raise ValueError(f"{label} is missing: {root}") from exc
    require(stat.S_ISDIR(root_metadata.st_mode), f"{label} is not a real directory: {root}")
    files: dict[str, Path] = {}

    def visit(directory: Path) -> None:
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError as exc:
            raise ValueError(f"cannot enumerate {label}: {directory}") from exc
        for path in children:
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise ValueError(f"cannot inspect {label} entry: {path}") from exc
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f"{label} contains a symlink: {relative}")
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)
            elif stat.S_ISREG(metadata.st_mode):
                files[relative] = path
            else:
                raise ValueError(f"{label} contains a nonregular entry: {relative}")

    visit(root)
    return files


def read_canonical_json(path: Path, label: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is missing or invalid: {path}") from exc
    require(isinstance(payload, dict), f"{label} must be an object: {path}")
    expected = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    require(raw == expected, f"{label} is not canonical: {path}")
    return payload


def read_tsv(path: Path, fields: list[str] | tuple[str, ...], label: str) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            require(list(reader.fieldnames or ()) == list(fields), f"{label} schema drift: {path}")
            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                require(None not in row and all(value is not None for value in row.values()), f"malformed {label} row {line_number}")
                rows.append(dict(row))
            return rows
    except OSError as exc:
        raise ValueError(f"{label} is missing: {path}") from exc


def render_tsv(fields: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    output = io.StringIO(newline="")
    field_list = list(fields)
    writer = csv.DictWriter(output, fieldnames=field_list, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_fsynced(path: Path, payload: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _copy_fsynced(source: Path, destination: Path) -> None:
    with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
        shutil.copyfileobj(source_handle, destination_handle)
        destination_handle.flush()
        os.fsync(destination_handle.fileno())


def _require_no_symlink_components(path: Path, label: str) -> None:
    absolute = path.absolute()
    components = [*reversed(absolute.parents), absolute]
    for component in components:
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ValueError(f"cannot inspect {label} path component: {component}") from exc
        require(not stat.S_ISLNK(metadata.st_mode), f"{label} contains a symlink path component: {component}")
        if component != absolute:
            require(stat.S_ISDIR(metadata.st_mode), f"{label} parent is not a real directory: {component}")


def publish_outputs_transactionally(
    output_dir: Path,
    outputs: dict[str, str],
    after_replace: Callable[[int, str], None] | None = None,
) -> None:
    require(tuple(outputs) == OUTPUT_NAMES, f"publication output set/order drift: {tuple(outputs)}")
    _require_no_symlink_components(output_dir, "publication output directory")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    _require_no_symlink_components(output_dir, "publication output directory")
    require(stat.S_ISDIR(output_dir.lstat().st_mode), f"publication output is not a real directory: {output_dir}")
    existed: dict[str, bool] = {}
    for name in OUTPUT_NAMES:
        destination = output_dir / name
        try:
            metadata = destination.lstat()
        except FileNotFoundError:
            existed[name] = False
        except OSError as exc:
            raise ValueError(f"cannot inspect publication destination: {destination}") from exc
        else:
            require(stat.S_ISREG(metadata.st_mode), f"publication destination is not a regular file: {destination}")
            existed[name] = True
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.phase2-staging-", dir=output_dir.parent))
    replaced: list[str] = []
    try:
        for name in OUTPUT_NAMES:
            destination = output_dir / name
            _write_fsynced(staging / f"{name}.new", outputs[name].encode("utf-8"))
            if existed[name]:
                _copy_fsynced(destination, staging / f"{name}.backup")
        _fsync_directory(staging)
        for step, name in enumerate(OUTPUT_NAMES, start=1):
            os.replace(staging / f"{name}.new", output_dir / name)
            replaced.append(name)
            _fsync_directory(output_dir)
            if after_replace is not None:
                after_replace(step, name)
    except BaseException:
        for name in reversed(replaced):
            destination = output_dir / name
            if existed[name]:
                os.replace(staging / f"{name}.backup", destination)
            else:
                destination.unlink(missing_ok=True)
        _fsync_directory(output_dir)
        raise
    finally:
        shutil.rmtree(staging)


def _load_comparator(repo_root: Path):
    comparator = repo_root / "scripts/compare_fasim_segmented_contract.py"
    require(sha256_file(comparator) == COMPARATOR_SHA256, "comparator checksum drift")
    scripts = str(repo_root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from compare_fasim_segmented_contract import _analyze  # pylint: disable=import-outside-toplevel
    return _analyze


def _load_report_validator(repo_root: Path):
    schema_path = repo_root / "schemas/gasal2_longtarget_run_report.schema.json"
    workflow_path = repo_root / "scripts/gasal2_longtarget.py"
    require(sha256_file(schema_path) == REPORT_SCHEMA_SHA256, "report schema checksum drift")
    require(sha256_file(workflow_path) == EXPECTED_TOOL_SHA256["workflow"], "workflow checksum drift")
    scripts = str(repo_root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from gasal2_longtarget import validate_schema_value  # pylint: disable=import-outside-toplevel
    return json.loads(schema_path.read_text(encoding="utf-8")), validate_schema_value


def _validate_schema_subset(schema: dict[str, object], value: object, path: str) -> None:
    if "const" in schema:
        require(value == schema["const"], f"{path} must equal {schema['const']!r}")
    if "enum" in schema:
        require(value in schema["enum"], f"{path} is outside the allowed enum")
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        matches = {
            "array": lambda item: isinstance(item, list),
            "boolean": lambda item: isinstance(item, bool),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "null": lambda item: item is None,
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "object": lambda item: isinstance(item, dict),
            "string": lambda item: isinstance(item, str),
        }
        require(any(matches[name](value) for name in allowed), f"{path} has the wrong JSON type")
    if isinstance(value, str) and "minLength" in schema:
        require(len(value) >= int(schema["minLength"]), f"{path} is shorter than minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        require(value >= schema["minimum"], f"{path} is below minimum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        require(isinstance(properties, dict), f"{path} schema properties are invalid")
        for field in schema.get("required", []):
            require(field in value, f"{path}.{field} is required")
        if schema.get("additionalProperties") is False:
            unexpected = sorted(set(value) - set(properties))
            require(not unexpected, f"{path} has unexpected properties: {', '.join(unexpected)}")
        for field, child_schema in properties.items():
            if field in value:
                _validate_schema_subset(child_schema, value[field], f"{path}.{field}")
    if isinstance(value, list):
        require(len(value) >= int(schema.get("minItems", 0)), f"{path} has too few items")
        if "maxItems" in schema:
            require(len(value) <= int(schema["maxItems"]), f"{path} has too many items")
        if schema.get("uniqueItems") is True:
            require(all(item not in value[:index] for index, item in enumerate(value)), f"{path} contains duplicate items")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_schema_subset(schema["items"], item, f"{path}[{index}]")


def validate_contract_registry_data(schema: dict[str, object], registry: dict[str, object]) -> None:
    """Validate the exact, non-executable post-holdout registry decision."""

    _validate_schema_subset(schema, registry, "registry")
    require(registry.get("schema_version") == "2.0.0", "registry schema version drift")
    require(registry.get("registry_version") == "2.0.0-post-holdout", "registry version drift")
    require(registry.get("registry_state") == "post_holdout_decision", "registry state drift")
    require(registry.get("holdout_freeze_id") == FREEZE_ID, "registry holdout freeze drift")
    require(registry.get("phase2_decision") == "verified_only_contract", "registry Phase 2 decision drift")
    require(registry.get("safe_resolution") == {
        "strategy": "verified_or_authority",
        "eligible_named_contracts": "verified",
        "mismatch_or_comparator_failure_publication": "authority",
        "full_output_or_ineligible": "cpu-authority",
        "fast_experimental": "explicit_opt_in_only",
        "gpu_only_contract_promoted": False,
    }, "unsafe or inconsistent safe resolution")
    require(registry.get("holdout_results") == {
        "dataset_id": FREEZE_ID,
        "status": "complete_with_results",
        "query_count": 12,
        "workload_count": 24,
        "attempt_count": 36,
        "scientific_mismatch_count": 2,
        "verified_fallback_count": 3,
        "pilot_receipt_sha256": PILOT_RECEIPT_SHA256,
        "pilot_excluded": True,
        "common_execution_identity_sha256": EXECUTION_IDENTITY_SHA256,
    }, "registry holdout result receipt drift")
    contracts = registry.get("contracts")
    require(isinstance(contracts, list) and len(contracts) == 3, "registry contract count drift")
    by_id = {contract.get("contract_id"): contract for contract in contracts}
    require(len(by_id) == 3 and set(by_id) == {"score_top5_v1", "all_ranked_top5_v1", "full_output_v1"}, "registry contract IDs drift")
    holdout_contract_counts = {
        "score_top5_v1": (23, 1),
        "all_ranked_top5_v1": (22, 2),
        "full_output_v1": (20, 4),
    }
    development_contract_counts = {
        "score_top5_v1": (13, 0),
        "all_ranked_top5_v1": (10, 3),
        "full_output_v1": (0, 13),
    }
    development_ranks = {
        "score": {"clean": 13, "mismatch": 0},
        "stability": {"clean": 11, "mismatch": 2},
        "nt": {"clean": 12, "mismatch": 1},
    }
    holdout_ranks = {
        "score": {"clean": 23, "mismatch": 1},
        "stability": {"clean": 23, "mismatch": 1},
        "nt": {"clean": 24, "mismatch": 0},
    }
    for contract_id, contract in by_id.items():
        require(contract.get("status") == "experimental", f"{contract_id}: invalid promotion status")
        authority = contract.get("authority_definition", {})
        require(authority.get("runtime_commit") == PAPER_RUNTIME_COMMIT, f"{contract_id}: authority epoch drift")
        datasets = contract.get("validation_datasets")
        require(datasets == [
            {"dataset_id": registry["paper_data_freeze"], "query_count": 5, "role": "development", "status": "complete", "workload_count": 13},
            {"dataset_id": FREEZE_ID, "query_count": 12, "role": "independent_holdout", "status": "complete_with_results", "workload_count": 24},
        ], f"{contract_id}: validation dataset state drift")
        counts = contract.get("clean_mismatch_counts", {})
        dev_clean, dev_mismatch = development_contract_counts[contract_id]
        holdout_clean, holdout_mismatch = holdout_contract_counts[contract_id]
        require(counts.get("development") == {"clean": dev_clean, "mismatch": dev_mismatch, "rank_counts": development_ranks}, f"{contract_id}: development counts drift")
        require(counts.get("holdout") == {"clean": holdout_clean, "mismatch": holdout_mismatch, "rank_counts": holdout_ranks}, f"{contract_id}: holdout counts drift")
        require(all(value is not None for value in (holdout_clean, holdout_mismatch)), f"{contract_id}: null holdout count")

    forbidden_keys = {"query_ids", "gene_names", "target_ids", "digests", "result_allowlist", "blacklist", "mechanism_guard"}

    def reject_unsafe_fields(value: object) -> None:
        if isinstance(value, dict):
            require(not forbidden_keys.intersection(value), "registry contains an unsafe identifier/digest/result guard")
            require(all("allowlist" not in key.lower() for key in value), "registry contains an allowlist field")
            for child in value.values():
                reject_unsafe_fields(child)
        elif isinstance(value, list):
            for child in value:
                reject_unsafe_fields(child)

    reject_unsafe_fields(registry)


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[column] for column in TFOSORTED_COLUMNS)


def _row_id(key: tuple[str, ...]) -> str:
    return hashlib.sha256("\t".join(key).encode("utf-8")).hexdigest()[:16]


def _signature(keys: tuple[tuple[str, ...], ...]) -> str:
    return hashlib.sha256(json.dumps(keys, separators=(",", ":")).encode("utf-8")).hexdigest()


def _primary(key: tuple[str, ...], rank: str) -> str:
    column = {"score": "Score", "stability": "MeanStability", "nt": "Nt(bp)"}[rank]
    return key[TFOSORTED_COLUMNS.index(column)]


def _single_tfosorted(path: Path, label: str) -> Path:
    matches = sorted(path.glob("*-TFOsorted"))
    require(len(matches) == 1, f"{label} must contain exactly one TFOsorted artifact")
    require(matches[0].is_file() and not matches[0].is_symlink(), f"{label} output is not a regular file")
    return matches[0]


def _expected_metrics(authority: object, candidate: object) -> dict[str, int]:
    missing = authority.row_keys - candidate.row_keys
    extra = candidate.row_keys - authority.row_keys
    metrics = {
        "baseline_rows": len(authority.rows),
        "candidate_rows": len(candidate.rows),
        "baseline_unique_rows": len(authority.row_keys),
        "candidate_unique_rows": len(candidate.row_keys),
        "full_missing_rows": len(missing),
        "full_extra_rows": len(extra),
        "baseline_boundary_tie_groups": len(authority.tie_groups),
        "candidate_boundary_tie_groups": len(candidate.tie_groups),
        "representative_conflict_clusters": authority.representative_conflict_clusters,
        "candidate_representative_conflict_clusters": candidate.representative_conflict_clusters,
    }
    for rank in RANKS:
        metrics[f"raw_{rank}_top5_equal"] = int(authority.raw_top[rank] == candidate.raw_top[rank])
        metrics[f"clustered_{rank}_top5_equal"] = int(authority.clustered_top[rank] == candidate.clustered_top[rank])
    metrics["all_three_top5_equal"] = int(all(metrics[f"clustered_{rank}_top5_equal"] for rank in RANKS))
    metrics["boundary_ties_equal"] = int(authority.tie_groups == candidate.tie_groups)
    return metrics


def _expected_comparator_details(authority: object, candidate: object) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for side, analysis in (("baseline", authority), ("candidate", candidate)):
        for mode in RANKS:
            for index, row in enumerate(analysis.raw_top_rows[mode], start=1):
                rows.append({"side": side, "kind": "raw", "mode": mode, "rank": str(index), "cluster_id": "NA", **row})
            for index, (cluster_id, row) in enumerate(analysis.clustered_top_rows[mode], start=1):
                rows.append({"side": side, "kind": "clustered", "mode": mode, "rank": str(index), "cluster_id": str(cluster_id), **row})
    return rows


def _validate_manifest(repo_root: Path) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    manifest_path = repo_root / "paper/bioinformatics/holdout_manifest.tsv"
    require(sha256_file(manifest_path) == MANIFEST_SHA256, "holdout manifest checksum drift")
    checksum_text = (repo_root / "paper/bioinformatics/holdout_manifest.sha256").read_text(encoding="ascii")
    require(checksum_text == f"{MANIFEST_SHA256}  holdout_manifest.tsv\n", "holdout manifest checksum file drift")
    rows = read_tsv(manifest_path, MANIFEST_FIELDS, "holdout manifest")
    require(len(rows) == 24, "holdout manifest workload count drift")
    require(len({row["workload_id"] for row in rows}) == 24, "duplicate holdout workload")
    attempts: list[dict[str, object]] = []
    repeated_queries = {"hq01", "hq05", "hq09"}
    for row in rows:
        require(row["requested_contract"] == "all-ranked-top5", f"{row['workload_id']}: contract drift")
        require(row["run_modes"] == "authority,candidate,verified", f"{row['workload_id']}: mode drift")
        require(row["status"] == "preregistered_not_run", f"{row['workload_id']}: frozen status drift")
        expected_repeats = 3 if row["query_id"] in repeated_queries else 1
        require(int(row["repeat_count"]) == expected_repeats, f"{row['workload_id']}: repeat count drift")
        for prefix in ("query", "target"):
            source = repo_root / row[f"{prefix}_path"]
            require(sha256_file(source) == row[f"{prefix}_file_sha256"], f"{row['workload_id']}: {prefix} checksum drift")
        for repeat_index in range(expected_repeats):
            attempts.append({
                "attempt_id": f"{row['workload_id']}__repeat{repeat_index:02d}",
                "workload_id": row["workload_id"],
                "repeat_index": repeat_index,
                "manifest": row,
            })
    require(len(attempts) == 36, "formal attempt plan count drift")
    return rows, attempts


def _validate_receipt(attempt_dir: Path, attempt_id: str) -> dict[str, object]:
    attempt_files = _regular_file_tree(attempt_dir, f"attempt {attempt_id} artifact tree")
    config_path = attempt_dir / "attempt-config.json"
    summary_path = attempt_dir / "attempt-summary.json"
    manifest_path = attempt_dir / "attempt-artifacts.tsv"
    receipt_path = attempt_dir / "attempt-complete.json"
    config = read_canonical_json(config_path, "attempt config")
    summary = read_canonical_json(summary_path, "attempt summary")
    receipt = read_canonical_json(receipt_path, "attempt receipt")
    config_without_digest = dict(config)
    config_digest = config_without_digest.pop("config_digest_sha256", None)
    require(config_digest == canonical_digest(config_without_digest), "attempt config digest mismatch")
    require(receipt.get("status") == "complete" and receipt.get("attempt_id") == attempt_id, "attempt receipt status/ID drift")
    require(receipt.get("config_digest_sha256") == config_digest, "attempt receipt config digest drift")
    require(receipt.get("config_sha256") == sha256_file(config_path), "attempt config checksum drift")
    require(receipt.get("summary_sha256") == sha256_file(summary_path), "attempt summary checksum drift")
    require(receipt.get("artifact_manifest_sha256") == sha256_file(manifest_path), "attempt artifact manifest checksum drift")
    require(summary.get("attempt_id") == attempt_id and config.get("attempt", {}).get("attempt_id") == attempt_id, "attempt ID join drift")
    require(receipt.get("outcome") == summary.get("outcome"), "attempt outcome join drift")
    artifact_rows = read_tsv(manifest_path, ATTEMPT_ARTIFACT_FIELDS, "attempt artifact manifest")
    require(receipt.get("artifact_count") == len(artifact_rows), "attempt artifact count drift")
    relative_paths = [row["artifact_path"] for row in artifact_rows]
    require(len(relative_paths) == len(set(relative_paths)), "duplicate attempt artifact path")
    for row in artifact_rows:
        relative = Path(row["artifact_path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe attempt artifact path")
        path = attempt_dir / relative
        require(path.is_file() and not path.is_symlink(), f"missing retained artifact: {attempt_id}/{relative}")
        require(str(path.stat().st_size) == row["size_bytes"], f"artifact size drift: {attempt_id}/{relative}")
        require(sha256_file(path) == row["sha256"], f"artifact checksum drift: {attempt_id}/{relative}")
    observed = set(attempt_files)
    expected = set(relative_paths) | {"attempt-artifacts.tsv", "attempt-complete.json"}
    require(observed == expected, f"attempt artifact set drift: {attempt_id}")
    return {
        "config": config,
        "summary": summary,
        "receipt": receipt,
        "artifacts": artifact_rows,
        "receipt_sha256": sha256_file(receipt_path),
    }


def _validate_identity_and_snapshot(config: dict[str, object], attempt_dir: Path, manifest_row: dict[str, str]) -> None:
    require(config.get("freeze_id") == FREEZE_ID, "attempt freeze ID drift")
    require(config.get("manifest_sha256") == MANIFEST_SHA256, "attempt manifest checksum binding drift")
    require(config.get("git_head") == CHECKPOINT_COMMIT, "attempt git_head/checkpoint drift")
    require(config.get("execution_identity_sha256") == EXECUTION_IDENTITY_SHA256, "common execution identity checksum drift")
    identity = config.get("execution_identity")
    require(isinstance(identity, dict), "attempt execution identity is missing")
    require(canonical_digest(identity) == EXECUTION_IDENTITY_SHA256, "attempt execution identity content drift")
    require(identity.get("git_head") == CHECKPOINT_COMMIT, "execution identity checkpoint drift")
    require(identity.get("runner", {}).get("sha256") == RUNNER_SHA256, "executed runner checksum drift")
    require(identity.get("manifest", {}).get("sha256") == MANIFEST_SHA256, "execution identity manifest drift")
    require(config.get("runner", {}).get("sha256") == RUNNER_SHA256, "attempt runner checksum drift")
    tools = identity.get("tools")
    support = identity.get("support_files")
    require(isinstance(tools, dict) and isinstance(support, dict), "execution identity tool bindings are missing")
    for name, digest in EXPECTED_TOOL_SHA256.items():
        require(tools.get(name, {}).get("sha256") == digest, f"execution tool binding drift: {name}")
        require(config.get("tools", {}).get(name, {}).get("sha256") == digest, f"attempt tool binding drift: {name}")
    for name, digest in EXPECTED_SUPPORT_SHA256.items():
        require(support.get(name, {}).get("sha256") == digest, f"execution support binding drift: {name}")
    attempt = config.get("attempt")
    require(isinstance(attempt, dict), "attempt config payload is missing")
    for field in ("workload_id", "query_id", "target_id", "query_path", "target_path", "query_file_sha256", "target_file_sha256"):
        require(str(attempt.get(field)) == manifest_row[field], f"attempt/manifest join drift: {field}")
    require(attempt.get("repeat_index") == int(str(config["attempt"]["attempt_id"]).rsplit("repeat", 1)[1]), "attempt repeat index drift")
    require(config.get("modes") == [
        {"artifact_namespace": namespace, "mode": mode, "contract": contract}
        for namespace, mode, contract, _resolved_contract, _resolved_execution in MODE_PLAN
    ], "attempt mode plan drift")
    require(config.get("rule") == 0 and config.get("top_k") == 5 and config.get("triplex_preset") == "normal", "attempt comparator parameters drift")
    require(config.get("backend_timeout_seconds") == 3600, "attempt timeout epoch drift")

    snapshot = attempt_dir / "execution-snapshot"
    snapshot_files = _regular_file_tree(snapshot, "execution snapshot")
    snapshot_manifest = read_canonical_json(snapshot / "snapshot-manifest.json", "execution snapshot manifest")
    require(snapshot_manifest.get("attempt_id") == attempt["attempt_id"], "snapshot attempt ID drift")
    require(snapshot_manifest.get("execution_identity_sha256") == EXECUTION_IDENTITY_SHA256, "snapshot identity drift")
    files = snapshot_manifest.get("files")
    require(isinstance(files, dict), "snapshot file manifest is missing")
    expected_relative = {
        "repository/scripts/gasal2_longtarget.py": EXPECTED_TOOL_SHA256["workflow"],
        "repository/scripts/compare_fasim_segmented_contract.py": EXPECTED_TOOL_SHA256["comparator"],
        "repository/scripts/capture_fasim_gasal2_paper_environment.py": EXPECTED_TOOL_SHA256["environment_capture"],
        "binaries/fasim_longtarget_x86": EXPECTED_TOOL_SHA256["authority_binary"],
        "binaries/fasim_longtarget_gasal2": EXPECTED_TOOL_SHA256["candidate_binary"],
        "inputs/query.fa": manifest_row["query_file_sha256"],
        "inputs/target.fa": manifest_row["target_file_sha256"],
        **{f"repository/{name}": digest for name, digest in EXPECTED_SUPPORT_SHA256.items()},
    }
    require(set(files) == set(expected_relative), "snapshot retained file set drift")
    observed = set(snapshot_files)
    require(observed == set(expected_relative) | {"snapshot-manifest.json"}, "snapshot filesystem set drift")
    for relative, digest in expected_relative.items():
        path = snapshot / relative
        require(files[relative].get("sha256") == digest, f"snapshot bound checksum drift: {relative}")
        require(sha256_file(path) == digest, f"snapshot checksum drift: {relative}")
        require(files[relative].get("size_bytes") == path.stat().st_size, f"snapshot size drift: {relative}")


def _validate_report(
    report: dict[str, object],
    result: dict[str, object],
    manifest_row: dict[str, str],
    attempt_dir: Path,
    expected_mode: tuple[str, str, str, str, str],
    schema: dict[str, object],
    validate_schema_value: Callable[[dict[str, object], object, str], None],
) -> None:
    namespace, mode, contract, resolved_contract, resolved_execution = expected_mode
    validate_schema_value(schema, report, "report")
    require(report.get("wrapper_commit") == CHECKPOINT_COMMIT, "report wrapper checkpoint drift")
    require(report.get("paper_runtime_commit") == PAPER_RUNTIME_COMMIT, "report runtime epoch drift")
    require(
        (result.get("artifact_namespace"), result.get("mode"), result.get("contract"))
        == (namespace, mode, contract),
        f"{namespace} mode result tuple/plan drift",
    )
    require(report.get("mode") == mode, f"{namespace} report mode binding drift")
    require(report.get("requested_contract") == contract, f"{namespace} report requested contract binding drift")
    require(report.get("resolved_contract") == resolved_contract, f"{namespace} report resolved contract binding drift")
    require(report.get("resolved_execution") == resolved_execution, f"{namespace} report resolved execution binding drift")
    require(report.get("result_status") == result["result_status"], "mode result status drift")
    require(report.get("published_source") == result["published_source"], "mode publication source drift")
    require(report.get("errors") == [], "mode report contains errors")
    require(report.get("preflight", {}).get("passed") is True, "mode preflight failed")
    require(report.get("inputs", {}).get("query", {}).get("sha256") == manifest_row["query_file_sha256"], "report query checksum drift")
    require(report.get("inputs", {}).get("target", {}).get("sha256") == manifest_row["target_file_sha256"], "report target checksum drift")
    require(
        _path_has_suffix(report.get("inputs", {}).get("query", {}).get("path"), "execution-snapshot", "inputs", "query.fa"),
        "report query path does not bind to the execution snapshot input",
    )
    require(
        _path_has_suffix(report.get("inputs", {}).get("target", {}).get("path"), "execution-snapshot", "inputs", "target.fa"),
        "report target path does not bind to the execution snapshot input",
    )
    require(
        _path_has_suffix(report.get("authority_backend"), "execution-snapshot", "binaries", "fasim_longtarget_x86"),
        "report authority backend path does not bind to the execution snapshot binary",
    )
    require(
        _path_has_suffix(report.get("candidate_backend"), "execution-snapshot", "binaries", "fasim_longtarget_gasal2"),
        "report candidate backend path does not bind to the execution snapshot binary",
    )
    counters = report.get("counters", {})
    for name in ("fallback", "guard", "oom", "timeout"):
        value = counters.get(name)
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"report {name} counter is invalid")
    require(counters.get("fallback") == result["fallback_count"], "report fallback count drift")
    require(counters.get("oom") == result["oom_count"], "report OOM count drift")
    require(counters.get("timeout") == result["reported_timeout_count"], "report timeout count drift")
    state = (report.get("result_status"), report.get("published_source"), counters.get("fallback"))
    require(state in MODE_STATES[namespace], f"{namespace} report status/source/fallback state drift")
    require(counters.get("guard") == 0, "report guard count drift")
    require(result["returncode"] == 0 and result["timed_out"] is False, "top-level mode technical failure retained")
    require(result["report_available"] is True and result["report_validation_status"] == "valid", "top-level mode report is invalid")
    require(result["time_telemetry_status"] == "available", "time telemetry failure")
    require(result["gpu_telemetry_status"] == "available", "GPU telemetry failure")
    require(result["telemetry_errors"] == [], "mode telemetry errors retained")
    _validate_published_outputs(attempt_dir, namespace, report)


def _published_record_count(path: Path) -> int:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = sum(1 for _row in csv.reader(handle, delimiter="\t"))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"published tabular output is unreadable: {path}") from exc
    require(rows >= 1, f"published tabular output has no header: {path}")
    return rows - 1


def _validate_published_outputs(attempt_dir: Path, namespace: str, report: dict[str, object]) -> None:
    output_dir = attempt_dir / namespace / "output"
    files = _regular_file_tree(output_dir, f"{namespace} published output tree")
    rows = report.get("published_outputs")
    require(isinstance(rows, list), f"{namespace} published output manifest is missing")
    relative_paths: list[str] = []
    by_relative: dict[str, dict[str, object]] = {}
    for row in rows:
        require(isinstance(row, dict), f"{namespace} published output row is invalid")
        raw_relative = row.get("relative_path")
        require(isinstance(raw_relative, str) and raw_relative, f"{namespace} published output relative path is invalid")
        relative = Path(raw_relative)
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and relative.as_posix() == raw_relative,
            f"unsafe {namespace} published output relative path: {raw_relative}",
        )
        relative_paths.append(raw_relative)
        by_relative[raw_relative] = row
    require(len(relative_paths) == len(set(relative_paths)), f"duplicate {namespace} published output relative path")
    require(set(relative_paths) == set(files), f"{namespace} published output set/tree drift")

    tfosorted = {relative for relative in files if Path(relative).name.endswith("-TFOsorted")}
    fixed = set(files) - tfosorted
    if namespace == "authority":
        require(len(tfosorted) == 1 and fixed == {"wrapper-stderr.log", "wrapper-stdout.log"}, "authority published output shape drift")
    elif namespace == "candidate":
        require(len(tfosorted) == 1 and fixed == {"contract.json", "wrapper-stderr.log", "wrapper-stdout.log"}, "candidate published output shape drift")
    elif report.get("result_status") == "candidate_clean":
        require(set(files) == {"contract.json", "gasal2-longtarget-all-ranked-top5.tsv"}, "verified candidate-clean published output shape drift")
    else:
        require(len(tfosorted) == 1 and fixed == {"wrapper-stderr.log", "wrapper-stdout.log"}, "verified fallback published output shape drift")

    for relative, path in files.items():
        row = by_relative[relative]
        require(
            _path_has_suffix(row.get("path"), namespace, "output", *Path(relative).parts),
            f"{namespace} published output absolute path/namespace drift: {relative}",
        )
        require(row.get("size_bytes") == path.lstat().st_size, f"{namespace} published output size drift: {relative}")
        require(row.get("sha256") == sha256_file(path), f"{namespace} published output checksum drift: {relative}")
        expected_record_count = (
            _published_record_count(path)
            if path.name.endswith("-TFOsorted") or path.suffix == ".tsv"
            else None
        )
        require(row.get("record_count") == expected_record_count, f"{namespace} published output record count drift: {relative}")


def _render_contract_output(analysis: object) -> str:
    fields = ["ranking", "rank", "cluster_id", *TFOSORTED_COLUMNS]
    rows: list[dict[str, object]] = []
    for mode in RANKS:
        for rank, (cluster_id, row) in enumerate(analysis.clustered_top_rows[mode], start=1):
            rows.append({"ranking": mode, "rank": rank, "cluster_id": cluster_id, **row})
    return render_tsv(fields, rows)


def _validate_verified_publication(attempt_dir: Path, report: dict[str, object], authority: object, candidate: object, metrics: dict[str, int]) -> None:
    output = attempt_dir / "verified/output"
    fallback = int(report["counters"]["fallback"])
    if fallback:
        authority_report = read_canonical_json(attempt_dir / "authority/report.json", "authority report")
        authority_relative = {row["relative_path"] for row in authority_report["published_outputs"]}
        verified_relative = {row["relative_path"] for row in report["published_outputs"]}
        require(verified_relative == authority_relative, "verified fallback published output tree is not authority-shaped")
        authority_path = _single_tfosorted(attempt_dir / "authority/output", "authority")
        verified_path = _single_tfosorted(output, "verified fallback")
        require(authority_path.read_bytes() == verified_path.read_bytes(), "verified fallback publication is not authority")
        evidence = read_canonical_json(attempt_dir / "verified-evidence/comparison.json", "verified fallback comparison")
        expected = _expected_metrics(authority, authority)
        require(evidence.get("metrics") == expected, "verified fallback comparator evidence drift")
        require(evidence.get("declared_contract_clean") is True and evidence.get("status") == "clean", "verified fallback evidence is not clean")
        return

    require(report.get("published_source") == "candidate" and report.get("result_status") == "candidate_clean", "clean verified publication status drift")
    result_path = output / "gasal2-longtarget-all-ranked-top5.tsv"
    require(result_path.read_text(encoding="utf-8") == _render_contract_output(candidate), "verified contract publication content drift")
    contract = read_canonical_json(output / "contract.json", "verified contract receipt")
    require(contract == {
        "schema_version": 1,
        "contract_id": "all-ranked-top5",
        "source": "candidate",
        "ranking_modes": ["score", "stability", "nt"],
        "top_k": 5,
        "row_count": sum(len(candidate.clustered_top_rows[rank]) for rank in RANKS),
        "full_candidate_output_published": False,
    }, "verified contract receipt drift")
    require(metrics["all_three_top5_equal"] == 1 and metrics["boundary_ties_equal"] == 1, "unsafe candidate publication")


def _result_rows_for_attempt(
    attempt: dict[str, object],
    validated: dict[str, object],
    analyze: Callable[[Path, int, int, int], object],
    report_schema: dict[str, object],
    validate_schema_value: Callable[[dict[str, object], object, str], None],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, tuple[str, str]]]:
    attempt_dir = attempt["attempt_dir"]
    manifest_row = attempt["manifest"]
    config = validated["config"]
    summary = validated["summary"]
    _validate_identity_and_snapshot(config, attempt_dir, manifest_row)
    require(summary.get("schema_version") == 1, "attempt summary schema version drift")
    require(summary.get("workload_id") == attempt["workload_id"] and summary.get("repeat_index") == attempt["repeat_index"], "attempt summary plan join drift")
    require(summary.get("failure_reasons") == [], "formal failure reasons retained")

    authority_path = _single_tfosorted(attempt_dir / "authority/output", "authority")
    candidate_path = _single_tfosorted(attempt_dir / "candidate/output", "candidate")
    authority = analyze(authority_path, 5, 15, 50)
    candidate = analyze(candidate_path, 5, 15, 50)
    metrics = _expected_metrics(authority, candidate)
    comparison = read_canonical_json(attempt_dir / "comparison.json", "direct comparison")
    require(comparison.get("metrics") == metrics, "direct comparison metric drift")
    declared_clean = bool(metrics["all_three_top5_equal"] and metrics["boundary_ties_equal"])
    expected_status = "clean" if declared_clean else "mismatch"
    require(comparison.get("status") == expected_status, "direct comparison status drift")
    require(comparison.get("declared_contract") == "all-ranked-top5", "direct comparator contract drift")
    require(comparison.get("declared_contract_clean") is declared_clean, "direct comparator decision drift")
    require(comparison.get("comparator_returncode") == (0 if all(value == 0 for value in (metrics["full_missing_rows"], metrics["full_extra_rows"])) and all(metrics[f"raw_{rank}_top5_equal"] for rank in RANKS) and declared_clean else 1), "direct comparator return code drift")
    expected_details = _expected_comparator_details(authority, candidate)
    observed_details = read_tsv(attempt_dir / "comparator/details.tsv", ["side", "kind", "mode", "rank", "cluster_id", *TFOSORTED_COLUMNS], "direct comparator details")
    require(observed_details == expected_details, "direct comparator detail drift")
    expected_outcome = "complete" if declared_clean else "scientific_mismatch"
    require(summary.get("outcome") == expected_outcome, "attempt outcome/comparator drift")
    require(summary.get("scientific_comparison_status") == expected_status, "attempt scientific status drift")

    mode_rows: list[dict[str, object]] = []
    verified_report: dict[str, object] | None = None
    mode_results = summary.get("mode_results")
    require(isinstance(mode_results, list) and len(mode_results) == 3, "attempt mode representation drift")
    observed_mode_plan = [
        (result.get("artifact_namespace"), result.get("mode"), result.get("contract"))
        for result in mode_results
        if isinstance(result, dict)
    ]
    expected_mode_plan = [(namespace, mode, contract) for namespace, mode, contract, _resolved_contract, _resolved_execution in MODE_PLAN]
    require(observed_mode_plan == expected_mode_plan, "attempt mode result tuple/order plan drift")
    for result, expected_mode in zip(mode_results, MODE_PLAN):
        namespace = expected_mode[0]
        report = read_canonical_json(attempt_dir / str(namespace) / "report.json", f"{namespace} report")
        _validate_report(report, result, manifest_row, attempt_dir, expected_mode, report_schema, validate_schema_value)
        if result["mode"] == "verified":
            verified_report = report
        mode_rows.append({
            "attempt_id": attempt["attempt_id"], "workload_id": attempt["workload_id"], "repeat_index": attempt["repeat_index"],
            "artifact_namespace": namespace, "mode": result["mode"], "contract": result["contract"],
            "report_available": int(result["report_available"]), "report_validation_status": result["report_validation_status"],
            "result_status": result["result_status"], "published_source": result["published_source"], "returncode": result["returncode"],
            "timed_out": int(result["timed_out"]), "fallback_count": result["fallback_count"], "oom_count": result["oom_count"],
            "timeout_count": result["reported_timeout_count"], "wall_seconds": result["wall_seconds"], "max_rss_kb": result["max_rss_kb"],
            "gpu_telemetry_status": result["gpu_telemetry_status"], "gpu_memory_peak_mib": result["gpu_memory_peak_mib"],
            "gpu_temperature_peak_c": result["gpu_temperature_peak_c"], "gpu_power_peak_w": result["gpu_power_peak_w"],
        })
    derived_fallback_count = sum(int(result["fallback_count"]) for result in mode_results)
    derived_oom_count = sum(int(result["oom_count"]) for result in mode_results)
    derived_timeout_count = sum(
        int(bool(result["timed_out"])) + int(result["reported_timeout_count"])
        for result in mode_results
    )
    require(summary.get("fallback_count") == derived_fallback_count, "attempt fallback counter derivation drift")
    require(summary.get("oom_count") == derived_oom_count, "attempt OOM counter derivation drift")
    require(summary.get("timeout_count") == derived_timeout_count, "attempt timeout counter derivation drift")
    require(derived_oom_count == 0 and derived_timeout_count == 0, "formal technical failure retained")
    require(verified_report is not None, "verified report is missing")
    fallback = int(verified_report["counters"]["fallback"])
    verified_status = verified_report["result_status"]
    comparator_status = verified_report["comparators"]["status"]
    expected_comparator_status = {
        "candidate_clean": {"clean"},
        "cpu_fallback_after_mismatch": {"mismatch"},
        "cpu_fallback_after_candidate_failure": {"not_run"},
        "cpu_fallback_after_comparator_failure": {"failed"},
    }[verified_status]
    require(comparator_status in expected_comparator_status, "verified fallback status/comparator status drift")
    require(summary.get("verified_result_status") == verified_status, "verified result status summary drift")
    require(summary.get("verified_published_source") == verified_report["published_source"], "verified publication summary drift")
    require(summary.get("verified_fallback_consistent") is True, "verified fallback consistency summary drift")
    if comparator_status in {"failed", "not_run"}:
        expected_nested_clean: object = "NA"
        expected_direct_consistent: object = "NA"
    else:
        expected_nested_clean = verified_report["comparators"].get("declared_contract_clean")
        require(isinstance(expected_nested_clean, bool), "verified comparator contract decision is missing")
        expected_direct_consistent = expected_nested_clean is declared_clean
        require(expected_direct_consistent, "direct and verified comparator contract decisions disagree")
    require(summary.get("verified_nested_declared_contract_clean") == expected_nested_clean, "verified nested contract summary drift")
    require(summary.get("direct_vs_verified_declared_contract_consistent") == expected_direct_consistent, "verified comparator consistency summary drift")
    if verified_report["comparators"]["status"] != "failed":
        for key, value in metrics.items():
            require(str(verified_report["comparators"]["metrics"].get(key)) == str(value), f"verified comparator metric drift: {key}")
    else:
        require(attempt["attempt_id"] == "hq12_ht02__repeat00", "unexpected verified comparator failure")
    _validate_verified_publication(attempt_dir, verified_report, authority, candidate, metrics)

    rank_rows: list[dict[str, object]] = []
    mismatch_details: list[dict[str, object]] = []
    signatures: dict[str, tuple[str, str]] = {}
    for rank in RANKS:
        baseline = authority.clustered_top[rank]
        selected = candidate.clustered_top[rank]
        positions = [str(index) for index in range(1, max(len(baseline), len(selected)) + 1) if (baseline[index - 1] if index <= len(baseline) else None) != (selected[index - 1] if index <= len(selected) else None)]
        baseline_signature = _signature(baseline)
        candidate_signature = _signature(selected)
        signatures[rank] = (baseline_signature, candidate_signature)
        rank_rows.append({
            "attempt_id": attempt["attempt_id"], "workload_id": attempt["workload_id"], "repeat_index": attempt["repeat_index"], "rank": rank,
            "rank_equal": int(not positions), "differing_position_count": len(positions), "differing_positions": ",".join(positions) or "NA",
            "baseline_top5_count": len(baseline), "candidate_top5_count": len(selected), "baseline_top5_signature": baseline_signature,
            "candidate_top5_signature": candidate_signature, "baseline_primary_values": ";".join(_primary(key, rank) for key in baseline) or "NA",
            "candidate_primary_values": ";".join(_primary(key, rank) for key in selected) or "NA",
            "baseline_row_identities": ";".join(_row_id(key) for key in baseline) or "NA", "candidate_row_identities": ";".join(_row_id(key) for key in selected) or "NA",
            "boundary_ties_equal": metrics["boundary_ties_equal"],
        })
        if positions:
            for side, analysis in (("baseline", authority), ("candidate", candidate)):
                for position, (cluster_id, row) in enumerate(analysis.clustered_top_rows[rank], start=1):
                    mismatch_details.append({
                        "attempt_id": attempt["attempt_id"], "workload_id": attempt["workload_id"], "evidence_kind": "rank_mismatch",
                        "side": side, "kind": "clustered", "mode": rank, "rank": position, "cluster_id": cluster_id, **row,
                    })
    for evidence_kind, side, keys in (
        ("full_missing", "baseline", sorted(authority.row_keys - candidate.row_keys)),
        ("full_extra", "candidate", sorted(candidate.row_keys - authority.row_keys)),
    ):
        for key in keys:
            mismatch_details.append({
                "attempt_id": attempt["attempt_id"], "workload_id": attempt["workload_id"], "evidence_kind": evidence_kind,
                "side": side, "kind": "full_row", "mode": "NA", "rank": "NA", "cluster_id": "NA",
                **dict(zip(TFOSORTED_COLUMNS, key)),
            })

    attempt_row = {
        "attempt_id": attempt["attempt_id"], "workload_id": attempt["workload_id"], "repeat_index": attempt["repeat_index"], "outcome": expected_outcome,
        "query_id": manifest_row["query_id"], "target_id": manifest_row["target_id"], "query_length_nt": manifest_row["query_length_nt"], "length_stratum": manifest_row["length_stratum"],
        "score_equal": metrics["clustered_score_top5_equal"], "stability_equal": metrics["clustered_stability_top5_equal"], "nt_equal": metrics["clustered_nt_top5_equal"],
        "all_ranked_equal": metrics["all_three_top5_equal"], "full_row_equal": int(metrics["full_missing_rows"] == 0 and metrics["full_extra_rows"] == 0),
        "baseline_rows": metrics["baseline_rows"], "candidate_rows": metrics["candidate_rows"], "full_missing_rows": metrics["full_missing_rows"], "full_extra_rows": metrics["full_extra_rows"],
        "boundary_ties_equal": metrics["boundary_ties_equal"], "verified_fallback": fallback, "verified_result_status": verified_report["result_status"],
        "verified_published_source": verified_report["published_source"], "verified_publication_contract_safe": 1,
        "fallback_count": summary["fallback_count"], "oom_count": summary["oom_count"], "timeout_count": summary["timeout_count"],
        "receipt_path": f"formal/{attempt['attempt_id']}/attempt-complete.json", "receipt_sha256": validated["receipt_sha256"],
        "config_digest_sha256": validated["receipt"]["config_digest_sha256"], "execution_identity_sha256": config["execution_identity_sha256"],
    }
    return attempt_row, rank_rows, mode_rows, mismatch_details, signatures


def _validate_root_tables(
    artifact_root: Path,
    expected_attempt_rows: list[dict[str, object]],
    expected_failure_rows: list[dict[str, object]],
    expected_artifact_rows: list[dict[str, object]],
) -> str:
    attempt_path = artifact_root / "formal-attempts.tsv"
    failure_path = artifact_root / "formal-failures.tsv"
    artifact_path = artifact_root / "formal-artifacts.tsv"
    summary_path = artifact_root / "formal-summary.json"
    observed_attempts = read_tsv(attempt_path, ROOT_ATTEMPT_FIELDS, "formal-attempts")
    observed_failures = read_tsv(failure_path, ROOT_FAILURE_FIELDS, "formal-failures")
    observed_artifacts = read_tsv(artifact_path, ROOT_ARTIFACT_FIELDS, "formal-artifacts")
    normalized_attempts = [{field: str(row[field]) for field in ROOT_ATTEMPT_FIELDS} for row in expected_attempt_rows]
    normalized_failures = [{field: str(row[field]) for field in ROOT_FAILURE_FIELDS} for row in expected_failure_rows]
    normalized_artifacts = [{field: str(row[field]) for field in ROOT_ARTIFACT_FIELDS} for row in expected_artifact_rows]
    require(observed_attempts == normalized_attempts, "formal-attempts representation drift")
    require(observed_failures == normalized_failures, "formal-failures representation drift")
    require(observed_artifacts == normalized_artifacts, "formal-artifacts representation drift")
    outcome_counts = dict(sorted(Counter(row["outcome"] for row in expected_attempt_rows).items()))
    expected_summary = {
        "schema_version": 1, "freeze_id": FREEZE_ID, "planned_attempt_count": 36,
        "represented_attempt_count": 36, "missing_attempt_count": 0, "missing_attempt_ids": [],
        "outcome_counts": outcome_counts, "complete_representation": True,
    }
    require(read_canonical_json(summary_path, "formal summary") == expected_summary, "formal summary representation drift")
    return artifact_path.read_text(encoding="utf-8")


def _collapse_workloads(
    manifest_rows: list[dict[str, str]],
    attempt_rows: list[dict[str, object]],
    signatures: dict[str, dict[str, tuple[str, str]]],
) -> list[dict[str, object]]:
    attempts_by_workload: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in attempt_rows:
        attempts_by_workload[str(row["workload_id"])].append(row)
    output: list[dict[str, object]] = []
    for manifest in manifest_rows:
        rows = attempts_by_workload[manifest["workload_id"]]
        repeat_count = int(manifest["repeat_count"])
        require(len(rows) == repeat_count, f"workload repeat representation drift: {manifest['workload_id']}")
        contract_fields = ("score_equal", "stability_equal", "nt_equal", "all_ranked_equal", "full_row_equal", "boundary_ties_equal")
        repeat_contract = all(len({int(row[field]) for row in rows}) == 1 for field in contract_fields)
        top5_consistent = True
        if repeat_count > 1:
            for rank in RANKS:
                for side in (0, 1):
                    if len({signatures[str(row["attempt_id"])][rank][side] for row in rows}) != 1:
                        top5_consistent = False
        require(repeat_contract and top5_consistent, f"repeat consistency failure: {manifest['workload_id']}")
        flags = {field: int(all(int(row[field]) == 1 for row in rows)) for field in contract_fields}
        output.append({
            "workload_id": manifest["workload_id"], "query_id": manifest["query_id"], "target_id": manifest["target_id"],
            "query_length_nt": manifest["query_length_nt"], "length_stratum": manifest["length_stratum"], "repeat_count": repeat_count,
            "repeat_basis": "all_primary_attempts" if repeat_count > 1 else "single_primary_attempt",
            "repeat_contract_consistent": int(repeat_contract), "repeat_top5_signatures_consistent": int(top5_consistent),
            "score_clean": flags["score_equal"], "score_mismatch": 1 - flags["score_equal"],
            "stability_clean": flags["stability_equal"], "stability_mismatch": 1 - flags["stability_equal"],
            "nt_clean": flags["nt_equal"], "nt_mismatch": 1 - flags["nt_equal"],
            "all_ranked_clean": flags["all_ranked_equal"], "all_ranked_mismatch": 1 - flags["all_ranked_equal"],
            "full_row_clean": flags["full_row_equal"], "full_row_mismatch": 1 - flags["full_row_equal"],
            "boundary_ties_clean": flags["boundary_ties_equal"], "verified_fallback_count": sum(int(row["verified_fallback"]) for row in rows),
            "oom_count": sum(int(row["oom_count"]) for row in rows), "timeout_count": sum(int(row["timeout_count"]) for row in rows),
        })
    return output


def _counts(rows: list[dict[str, object]], clean_field: str) -> dict[str, int]:
    clean = sum(int(row[clean_field]) for row in rows)
    return {"clean": clean, "mismatch": len(rows) - clean}


def _fallback_narrative(attempt_rows: list[dict[str, object]]) -> str:
    fallback_rows = [row for row in attempt_rows if int(row["verified_fallback"]) == 1]
    by_status: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in fallback_rows:
        by_status[str(row["verified_result_status"])].append(row)
    labels = (
        ("cpu_fallback_after_mismatch", "declared-contract mismatch", "declared-contract mismatches"),
        ("cpu_fallback_after_candidate_failure", "candidate failure", "candidate failures"),
        ("cpu_fallback_after_comparator_failure", "comparator-detail failure", "comparator-detail failures"),
    )
    require(set(by_status).issubset({status for status, _singular, _plural in labels}), "unknown verified fallback narrative state")
    number_words = {1: "one", 2: "two", 3: "three"}
    reasons: list[str] = []
    for status, singular, plural in labels:
        rows = by_status.get(status, [])
        if not rows:
            continue
        count = len(rows)
        count_text = number_words.get(count, str(count))
        article = "the " if status == "cpu_fallback_after_mismatch" and count == 2 else ""
        reason = f"{article}{count_text} {singular if count == 1 else plural}"
        if status != "cpu_fallback_after_mismatch":
            workload_ids = sorted({str(row["workload_id"]) for row in rows})
            reason += " (" + ", ".join(f"`{workload_id}`" for workload_id in workload_ids) + ")"
        reasons.append(reason)
    require(reasons and sum(len(rows) for rows in by_status.values()) == len(fallback_rows), "verified fallback narrative representation drift")
    if len(reasons) == 1:
        reason_text = reasons[0]
    elif len(reasons) == 2:
        reason_text = f"{reasons[0]} and {reasons[1]}"
    else:
        reason_text = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"
    total_text = number_words.get(len(fallback_rows), str(len(fallback_rows))).capitalize()
    return f"{total_text} verified executions published authority output: {reason_text}."


def _render_decision(summary: dict[str, object], attempt_rows: list[dict[str, object]]) -> str:
    fallback_narrative = _fallback_narrative(attempt_rows)
    return f"""# Bioinformatics Phase 2 Decision

The preregistered independent holdout is complete. All 36 primary formal attempts from 24 workloads are represented; the fixed pilot receipt was validated separately and excluded from the formal analysis basis. There were no technical failures, missing attempts, OOMs, timeouts, invalid reports, or telemetry errors.

The candidate matched score-ranked top 5 results in 35/36 attempts (23/24 workloads), stability-ranked top 5 results in 35/36 attempts (23/24 workloads), and Nt-ranked top 5 results in 36/36 attempts (24/24 workloads). Two attempts were scientific mismatches: `hq10_ht02` for stability ranking and `hq11_ht02` for score ranking. Full-row diagnostics also differed for `hq04_ht02` and `hq12_ht02`; full-output equality is 32/36 attempts and 20/24 workloads. Boundary ties matched in all 36 attempts.

{fallback_narrative} Every verified publication was independently validated as contract-safe. Repeated workload contracts and authority/candidate top-5 signatures were consistent across the preregistered three-repeat set.

No mechanism guard was inferred. GPU-only promoted coverage is 0/24 workloads, while safe verified-or-authority contract-safe coverage is 24/24 workloads.

## Decision

`{summary['decision']}`

Promotion gate P1 fails because the holdout score-ranked contract is not zero-mismatch. No GPU-only safe contract is promoted. All fast contracts remain experimental and opt-in. Safe execution continues to resolve eligible named contracts through verified comparison and otherwise routes to CPU authority; mismatch or comparator failure publishes authority. Full-output and ineligible requests remain authority-routed.

No query ID, gene name, target ID, input digest, observed result, mechanism guard, blacklist, or allowlist was used to hide or route around an unfavorable row. The negative results remain represented in the generated evidence tables.
"""


def build_outputs(repo_root: Path, artifact_root: Path) -> dict[str, str]:
    registry_schema = json.loads((repo_root / "schemas/gasal2_longtarget_contracts.schema.json").read_text(encoding="utf-8"))
    registry = json.loads((repo_root / "config/gasal2_longtarget_contracts.json").read_text(encoding="utf-8"))
    validate_contract_registry_data(registry_schema, registry)
    manifest_rows, plan = _validate_manifest(repo_root)
    require(artifact_root.is_dir() and not artifact_root.is_symlink(), "frozen artifact root is missing or symlinked")
    _regular_file_tree(artifact_root, "frozen artifact tree")
    expected_root_entries = {
        "formal", "pilot", "formal-attempts.tsv", "formal-failures.tsv",
        "formal-artifacts.tsv", "formal-summary.json",
    }
    observed_root_entries = {path.name for path in artifact_root.iterdir()}
    require(observed_root_entries == expected_root_entries, f"artifact root set drift: {sorted(observed_root_entries ^ expected_root_entries)}")
    formal_root = artifact_root / "formal"
    formal_entries = list(formal_root.iterdir())
    require(all(path.is_dir() and not path.is_symlink() for path in formal_entries), "extra artifact in formal root")
    observed_attempt_ids = {path.name for path in formal_entries}
    expected_attempt_ids = {str(row["attempt_id"]) for row in plan}
    missing = sorted(expected_attempt_ids - observed_attempt_ids)
    extra = sorted(observed_attempt_ids - expected_attempt_ids)
    require(not missing and not extra, f"attempt set drift: missing={missing}, extra={extra}")
    pilot_root = artifact_root / "pilot"
    require(
        {path.name for path in pilot_root.iterdir()} == {"pilot__hq01_ht01__repeat00"},
        "pilot artifact set drift",
    )
    pilot_receipt = artifact_root / "pilot/pilot__hq01_ht01__repeat00/attempt-complete.json"
    require(sha256_file(pilot_receipt) == PILOT_RECEIPT_SHA256, "fixed pilot receipt checksum drift")
    pilot = _validate_receipt(pilot_receipt.parent, "pilot__hq01_ht01__repeat00")
    require(pilot["receipt"]["outcome"] == "complete", "fixed pilot did not complete")

    analyze = _load_comparator(repo_root)
    report_schema, validate_schema_value = _load_report_validator(repo_root)
    attempt_rows: list[dict[str, object]] = []
    rank_rows: list[dict[str, object]] = []
    mode_rows: list[dict[str, object]] = []
    mismatch_rows: list[dict[str, object]] = []
    all_signatures: dict[str, dict[str, tuple[str, str]]] = {}
    root_attempt_rows: list[dict[str, object]] = []
    root_failure_rows: list[dict[str, object]] = []
    root_artifact_rows: list[dict[str, object]] = []
    identities: list[object] = []
    for item in plan:
        attempt_id = str(item["attempt_id"])
        attempt_dir = formal_root / attempt_id
        item["attempt_dir"] = attempt_dir
        validated = _validate_receipt(attempt_dir, attempt_id)
        identities.append(validated["config"]["execution_identity"])
        attempt_row, attempt_rank_rows, attempt_mode_rows, attempt_mismatch_rows, signatures = _result_rows_for_attempt(
            item, validated, analyze, report_schema, validate_schema_value
        )
        attempt_rows.append(attempt_row)
        rank_rows.extend(attempt_rank_rows)
        mode_rows.extend(attempt_mode_rows)
        mismatch_rows.extend(attempt_mismatch_rows)
        all_signatures[attempt_id] = signatures
        summary = validated["summary"]
        root_attempt_rows.append({
            "attempt_id": attempt_id, "workload_id": summary["workload_id"], "repeat_index": summary["repeat_index"], "outcome": summary["outcome"],
            "fallback_count": summary["fallback_count"], "oom_count": summary["oom_count"], "timeout_count": summary["timeout_count"],
            "receipt_path": f"formal/{attempt_id}/attempt-complete.json", "receipt_sha256": validated["receipt_sha256"],
            "config_digest_sha256": validated["receipt"]["config_digest_sha256"],
        })
        if summary["outcome"] != "complete":
            root_failure_rows.append({
                "attempt_id": attempt_id, "workload_id": summary["workload_id"], "failure_type": summary["outcome"],
                "failure_reasons": ";".join(summary["failure_reasons"]) or "evaluated_mismatch",
                "receipt_path": f"formal/{attempt_id}/attempt-complete.json",
            })
        for artifact in validated["artifacts"]:
            root_artifact_rows.append({
                "attempt_id": attempt_id, "artifact_path": f"formal/{attempt_id}/{artifact['artifact_path']}",
                "size_bytes": artifact["size_bytes"], "sha256": artifact["sha256"],
            })
        for name in ("attempt-artifacts.tsv", "attempt-complete.json"):
            path = attempt_dir / name
            root_artifact_rows.append({
                "attempt_id": attempt_id, "artifact_path": f"formal/{attempt_id}/{name}", "size_bytes": path.stat().st_size, "sha256": sha256_file(path),
            })
    require(all(identity == identities[0] for identity in identities), "formal attempts do not share one execution identity")
    raw_artifacts = _validate_root_tables(artifact_root, root_attempt_rows, root_failure_rows, root_artifact_rows)
    workload_rows = _collapse_workloads(manifest_rows, attempt_rows, all_signatures)

    attempt_rank_counts = {rank: _counts(attempt_rows, f"{rank}_equal") for rank in RANKS}
    workload_rank_counts = {rank: _counts(workload_rows, f"{rank}_clean") for rank in RANKS}
    summary = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "runner_checkpoint_commit": CHECKPOINT_COMMIT,
        "executed_runner_sha256": RUNNER_SHA256,
        "common_execution_identity_sha256": EXECUTION_IDENTITY_SHA256,
        "pilot_receipt_sha256": PILOT_RECEIPT_SHA256,
        "pilot_excluded_from_formal_source_data": True,
        "decision": "verified_only_contract",
        "attempt_counts": {
            "planned": 36, "represented": 36,
            "complete": sum(row["outcome"] == "complete" for row in attempt_rows),
            "scientific_mismatch": sum(row["outcome"] == "scientific_mismatch" for row in attempt_rows),
            "technical_failure": 0, "missing": 0, "oom": 0, "timeout": 0,
            "invalid_report": 0, "telemetry_error": 0,
            "verified_fallback": sum(int(row["verified_fallback"]) for row in attempt_rows),
        },
        "workload_count": 24,
        "rank_row_count": len(rank_rows),
        "mode_row_count": len(mode_rows),
        "attempt_rank_counts": attempt_rank_counts,
        "workload_rank_counts": workload_rank_counts,
        "attempt_all_ranked_counts": _counts(attempt_rows, "all_ranked_equal"),
        "workload_all_ranked_counts": _counts(workload_rows, "all_ranked_clean"),
        "attempt_full_row_counts": _counts(attempt_rows, "full_row_equal"),
        "workload_full_row_counts": _counts(workload_rows, "full_row_clean"),
        "boundary_ties": {"clean": 36, "mismatch": 0},
        "guard_coverage": {
            "mechanism_guard_inferred": False,
            "gpu_only_promoted": {
                "covered_workloads": 0,
                "total_workloads": 24,
            },
            "safe_verified_or_authority_contract_safe": {
                "covered_workloads": 24,
                "total_workloads": 24,
            },
        },
        "promotion_gates": {
            "P1_score_zero_mismatch": False,
            "gpu_only_contract_promoted": False,
            "safe_resolution": "verified_or_authority",
        },
    }
    require(summary["attempt_counts"]["complete"] == 34 and summary["attempt_counts"]["scientific_mismatch"] == 2, "formal outcome counts drift")
    require(summary["attempt_counts"]["verified_fallback"] == 3, "verified fallback count drift")
    require(attempt_rank_counts == {"score": {"clean": 35, "mismatch": 1}, "stability": {"clean": 35, "mismatch": 1}, "nt": {"clean": 36, "mismatch": 0}}, "attempt rank counts drift")
    require(workload_rank_counts == {"score": {"clean": 23, "mismatch": 1}, "stability": {"clean": 23, "mismatch": 1}, "nt": {"clean": 24, "mismatch": 0}}, "workload rank counts drift")
    require(summary["attempt_all_ranked_counts"] == {"clean": 34, "mismatch": 2}, "attempt all-ranked counts drift")
    require(summary["workload_all_ranked_counts"] == {"clean": 22, "mismatch": 2}, "workload all-ranked counts drift")
    require(summary["attempt_full_row_counts"] == {"clean": 32, "mismatch": 4}, "attempt full-row counts drift")
    require(summary["workload_full_row_counts"] == {"clean": 20, "mismatch": 4}, "workload full-row counts drift")
    require(len(rank_rows) == 108 and len(mode_rows) == 108, "derived row cardinality drift")

    outputs = {
        "holdout_attempt_results.tsv": render_tsv(ATTEMPT_FIELDS, attempt_rows),
        "holdout_workload_results.tsv": render_tsv(WORKLOAD_FIELDS, workload_rows),
        "holdout_rank_results.tsv": render_tsv(RANK_FIELDS, rank_rows),
        "holdout_mode_results.tsv": render_tsv(MODE_FIELDS, mode_rows),
        "holdout_mismatch_details.tsv": render_tsv(DETAIL_FIELDS, mismatch_rows),
        "holdout_raw_artifacts.tsv": raw_artifacts,
        "holdout_summary.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
        "phase2_decision.md": _render_decision(summary, attempt_rows),
    }
    return outputs


def generate(repo_root: Path, output_dir: Path, *, artifact_root: Path | None = None) -> dict[str, str]:
    repo_root = repo_root.resolve()
    frozen = (artifact_root or repo_root / ".paper-artifacts/bioinformatics-phase2-holdout-v1").absolute()
    resolved_frozen = frozen.resolve(strict=True)
    resolved_output = output_dir.absolute().resolve(strict=False)
    overlaps = (
        resolved_output == resolved_frozen
        or resolved_output in resolved_frozen.parents
        or resolved_frozen in resolved_output.parents
    )
    require(not overlaps, "output and frozen artifact roots must be disjoint; containment/alias overlap detected")
    outputs = build_outputs(repo_root, frozen)
    publish_outputs_transactionally(output_dir, outputs)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir or repo_root / "paper/bioinformatics"
    try:
        generate(repo_root, output_dir, artifact_root=args.artifact_root)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("bioinformatics_phase2_analysis=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
