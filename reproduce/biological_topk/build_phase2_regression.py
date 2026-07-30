#!/usr/bin/env python3
"""Build deterministic Phase 2 historical candidate-site regression evidence."""

from __future__ import annotations

import argparse
import csv
import functools
import hashlib
import io
import json
import os
import platform
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import canonicalize_rows, compare_candidate_topk, contract
except ImportError:  # pragma: no cover
    import canonicalize_rows  # type: ignore[no-redef]
    import compare_candidate_topk  # type: ignore[no-redef]
    import contract  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
PHASE1_COMMIT = "0daed2c4e1f181d3ce67ecba52db314a1798146e"
CONTRACT_SPEC_PATH = PAPER / "contract_spec.json"
MANIFEST_PATH = PAPER / "phase2_regression_manifest.tsv"
RESULTS_PATH = PAPER / "phase2_regression_results.tsv"
DETAILS_PATH = PAPER / "phase2_regression_details.tsv"
KNOWN_CASES_PATH = PAPER / "phase2_known_cases.json"
RECEIPT_PATH = PAPER / "phase2_regression_receipt.json"
FREEZE_PATH = PAPER / "phase2_comparator_freeze.json"

MANIFEST_FIELDS = (
    "comparison_id",
    "dataset_class",
    "evidence_role",
    "workload_id",
    "repeat_id",
    "authority_output",
    "candidate_output",
    "authority_output_sha256",
    "candidate_output_sha256",
    "authority_query_fasta",
    "candidate_query_fasta",
    "authority_target_fasta",
    "candidate_target_fasta",
    "query_fasta_interval",
    "target_fasta_interval",
    "target_region_start0",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_sequence_sha256",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_sequence_sha256",
    "assembly",
    "target_coordinate_namespace",
    "query_extraction_recipe_id",
    "target_extraction_recipe_id",
    "parameter_bundle_sha256",
    "input_pair_digest",
    "authority_receipt_sha256",
    "candidate_receipt_sha256",
)
RESULT_FIELDS = (
    "comparison_id",
    "dataset_class",
    "workload_id",
    "repeat_id",
    "comparison_status",
    "technical_failure",
    "ranking_mode",
    "strict_row_diagnostic",
    "reference_candidate_count",
    "candidate_candidate_count",
    "matched_count",
    "unmatched_reference_count",
    "unmatched_candidate_count",
    "recall",
    "precision",
    "top1_retained",
    "complete_set_preserved",
    "set_membership",
    "ambiguous_matching",
    "target_overlap_minimum",
    "classifications",
    "finite_rbo_fraction",
    "binary_gate_denominator_eligible",
    "binary_success",
)
DETAIL_FIELDS = (
    "comparison_id",
    "dataset_class",
    "workload_id",
    "repeat_id",
    *compare_candidate_topk.DETAIL_FIELDS[1:],
)
COMPONENT_PATHS = (
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/biological_topk/match_candidate_sites.py",
    "reproduce/biological_topk/compare_candidate_topk.py",
    "reproduce/biological_topk/exact_binomial_bounds.py",
    "reproduce/biological_topk/rank_diagnostics.py",
)


class RegressionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@functools.lru_cache(maxsize=512)
def sha256_file(path: Path) -> str:
    return canonicalize_rows.sha256_file(path)


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise RegressionError(f"regression path escapes repository: {path}") from error


def read_json(path: Path) -> Mapping[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RegressionError(f"invalid JSON {path}: {error}") from error
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(
        reader.fieldnames is not None
        and all(None not in row and all(value is not None for value in row.values()) for row in rows),
        f"malformed TSV: {path}",
    )
    return rows


def render_tsv(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
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


def unique_output(directory: Path) -> Path:
    paths = sorted(path for path in directory.rglob("*TFOsorted") if path.is_file())
    require(len(paths) == 1, f"expected one TFOsorted output in {directory}, found {len(paths)}")
    return paths[0]


@dataclass(frozen=True)
class Fixture:
    comparison_id: str
    dataset_class: str
    workload_id: str
    repeat_id: str
    authority_output: Path
    candidate_output: Path
    authority_query_fasta: Path
    candidate_query_fasta: Path
    authority_target_fasta: Path
    candidate_target_fasta: Path
    query_fasta_interval: tuple[int, int]
    target_fasta_interval: tuple[int, int]
    query_identity_interval: tuple[int, int]
    target_identity_interval: tuple[int, int]
    target_region_start0: int
    query_namespace: str
    query_ordinal: str | int
    target_namespace: str
    target_ordinal: str | int
    target_coordinate_namespace: str
    query_recipe: str
    target_recipe: str
    chromosome_or_target_id: str


def _holdout_metadata() -> Mapping[str, dict[str, str]]:
    return {row["workload_id"]: row for row in read_tsv(ROOT / "paper/bioinformatics/holdout_manifest.tsv")}


def holdout_fixtures() -> list[Fixture]:
    stage = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1/formal"
    metadata = _holdout_metadata()
    fixtures: list[Fixture] = []
    for attempt in sorted(path for path in stage.iterdir() if path.is_dir()):
        complete = read_json(attempt / "attempt-complete.json")
        require(complete.get("status") == "complete", f"incomplete holdout attempt: {attempt.name}")
        config = read_json(attempt / "attempt-config.json")["attempt"]
        workload = str(config["workload_id"])
        row = metadata[workload]
        query = attempt / "execution-snapshot/inputs/query.fa"
        target = attempt / "execution-snapshot/inputs/target.fa"
        query_length = len(canonicalize_rows._read_single_fasta(query, "query"))
        target_length = len(canonicalize_rows._read_single_fasta(target, "target"))
        target_start0 = int(row["target_region_start"]) - 1
        fixtures.append(
            Fixture(
                comparison_id=f"phase2_holdout:{attempt.name}",
                dataset_class="phase2_holdout_36",
                workload_id=workload,
                repeat_id=str(config["repeat_index"]),
                authority_output=unique_output(attempt / "authority/output"),
                candidate_output=unique_output(attempt / "candidate/output"),
                authority_query_fasta=query,
                candidate_query_fasta=query,
                authority_target_fasta=target,
                candidate_target_fasta=target,
                query_fasta_interval=(0, query_length),
                target_fasta_interval=(0, target_length),
                query_identity_interval=(0, query_length),
                target_identity_interval=(target_start0, target_start0 + target_length),
                target_region_start0=target_start0,
                query_namespace="bioinformatics_phase2_holdout_query_v1",
                query_ordinal=str(config["query_id"]),
                target_namespace="bioinformatics_phase2_holdout_target_v1",
                target_ordinal=str(config["target_id"]),
                target_coordinate_namespace="GRCh38_0_based_half_open",
                query_recipe="historical_phase2_holdout_query_v1",
                target_recipe="historical_phase2_holdout_target_v1",
                chromosome_or_target_id=str(row["target_chromosome"]),
            )
        )
    require(len(fixtures) == 36, f"Phase 2 holdout fixture count drift: {len(fixtures)}")
    return fixtures


def hybrid_regression_fixtures() -> list[Fixture]:
    stage = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/regression"
    metadata = _holdout_metadata()
    fixtures: list[Fixture] = []
    for attempt in sorted(stage.glob("v2reg_*")):
        complete = read_json(attempt / "attempt-complete.json")
        require(complete.get("status") == "complete", f"incomplete hybrid regression: {attempt.name}")
        config = read_json(attempt / "attempt-config.json")
        workload = f"{config['query_id']}_{config['target_id']}"
        row = metadata[workload]
        query = attempt / "inputs/query.fa"
        target = attempt / "inputs/target.fa"
        query_length = len(canonicalize_rows._read_single_fasta(query, "query"))
        target_length = len(canonicalize_rows._read_single_fasta(target, "target"))
        target_start0 = int(row["target_region_start"]) - 1
        fixtures.append(
            Fixture(
                comparison_id=f"canonical_hybrid_v2_regression:{config['validation_id']}",
                dataset_class="canonical_hybrid_v2_regression_36",
                workload_id=workload,
                repeat_id=str(config["repeat_id"]),
                authority_output=attempt / "inputs/authority-reference.tfosorted",
                candidate_output=unique_output(attempt / "output"),
                authority_query_fasta=query,
                candidate_query_fasta=query,
                authority_target_fasta=target,
                candidate_target_fasta=target,
                query_fasta_interval=(0, query_length),
                target_fasta_interval=(0, target_length),
                query_identity_interval=(0, query_length),
                target_identity_interval=(target_start0, target_start0 + target_length),
                target_region_start0=target_start0,
                query_namespace="bioinformatics_phase2_holdout_query_v1",
                query_ordinal=str(config["query_id"]),
                target_namespace="bioinformatics_phase2_holdout_target_v1",
                target_ordinal=str(config["target_id"]),
                target_coordinate_namespace="GRCh38_0_based_half_open",
                query_recipe="historical_phase2_holdout_query_v1",
                target_recipe="historical_phase2_holdout_target_v1",
                chromosome_or_target_id=str(row["target_chromosome"]),
            )
        )
    require(len(fixtures) == 36, f"hybrid regression fixture count drift: {len(fixtures)}")
    return fixtures


def hybrid_holdout_fixtures() -> list[Fixture]:
    stage = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
    workloads = {
        row["workload_id"]: row
        for row in read_tsv(ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv")
    }
    fixtures: list[Fixture] = []
    for candidate_attempt in sorted(stage.glob("v2hold_*_h")):
        authority_attempt = candidate_attempt.with_name(candidate_attempt.name[:-1] + "a")
        candidate_config = read_json(candidate_attempt / "attempt-config.json")
        authority_complete = read_json(authority_attempt / "attempt-complete.json")
        candidate_complete = read_json(candidate_attempt / "attempt-complete.json")
        require(
            authority_complete.get("status") == candidate_complete.get("status") == "complete",
            f"incomplete former fresh holdout pair: {candidate_config['validation_id']}",
        )
        validation_id = str(candidate_config["validation_id"])
        workload_id = validation_id.split("__", 1)[0]
        workload = workloads[workload_id]
        authority_query = authority_attempt / "inputs/query.fa"
        candidate_query = candidate_attempt / "inputs/query.fa"
        authority_target = authority_attempt / "inputs/target.fa"
        candidate_target = candidate_attempt / "inputs/target.fa"
        query_length = len(canonicalize_rows._read_single_fasta(authority_query, "query"))
        target_length = len(canonicalize_rows._read_single_fasta(authority_target, "target"))
        fixtures.append(
            Fixture(
                comparison_id=f"canonical_hybrid_v2_former_fresh:{validation_id}",
                dataset_class="canonical_hybrid_v2_former_fresh_60_regression_only",
                workload_id=workload_id,
                repeat_id=str(candidate_config["repeat_id"]),
                authority_output=unique_output(authority_attempt / "output"),
                candidate_output=unique_output(candidate_attempt / "output"),
                authority_query_fasta=authority_query,
                candidate_query_fasta=candidate_query,
                authority_target_fasta=authority_target,
                candidate_target_fasta=candidate_target,
                query_fasta_interval=(0, query_length),
                target_fasta_interval=(0, target_length),
                query_identity_interval=(0, query_length),
                target_identity_interval=(0, target_length),
                target_region_start0=0,
                query_namespace="canonical_hybrid_v2_application_query_v1",
                query_ordinal=workload["query_source_ordinal"],
                target_namespace="canonical_hybrid_v2_application_target_v1",
                target_ordinal=workload["target_source_ordinal"],
                target_coordinate_namespace="application_target_fasta_0_based_half_open",
                query_recipe="historical_application_query_fasta_v1",
                target_recipe="historical_application_target_fasta_v1",
                chromosome_or_target_id=workload["target_id"],
            )
        )
    require(len(fixtures) == 60, f"former fresh holdout fixture count drift: {len(fixtures)}")
    return fixtures


def generalization_fixtures() -> list[Fixture]:
    stage = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
    fixtures: list[Fixture] = []
    for authority_run in sorted(stage.glob("*__baseline__0")):
        authority_outputs = sorted(authority_run.glob("output/*TFOsorted"))
        if not authority_outputs:
            continue
        require(len(authority_outputs) == 1, f"multiple direct outputs: {authority_run.name}")
        candidate_run = authority_run.with_name(authority_run.name.replace("__baseline__0", "__candidate__0"))
        candidate_output = unique_output(candidate_run / "output")
        config = read_json(authority_run / "run-config.json")
        row = config["manifest_row"]
        region = str(row["target_region"])
        match = re.fullmatch(r"slice:([0-9]+)-([0-9]+)", region)
        require(match is not None, f"generalization target region is not a slice: {region}")
        target_start, target_end = (int(value) for value in match.groups())
        authority_query = authority_run / "inputs/query.fa"
        candidate_query = candidate_run / "inputs/query.fa"
        authority_target = authority_run / "inputs/target.fa"
        candidate_target = candidate_run / "inputs/target.fa"
        query_length = len(canonicalize_rows._read_single_fasta(authority_query, "query"))
        target_length = len(canonicalize_rows._read_single_fasta(authority_target, "target"))
        require(target_length == target_end - target_start, "materialized target slice length drift")
        fixtures.append(
            Fixture(
                comparison_id=f"paper_generalization:{authority_run.name.replace('__baseline__0', '')}",
                dataset_class="historical_paper_generalization_available",
                workload_id=str(row["workload_id"]),
                repeat_id=str(config["pair_id"]),
                authority_output=authority_outputs[0],
                candidate_output=candidate_output,
                authority_query_fasta=authority_query,
                candidate_query_fasta=candidate_query,
                authority_target_fasta=authority_target,
                candidate_target_fasta=candidate_target,
                query_fasta_interval=(0, query_length),
                target_fasta_interval=(0, target_length),
                query_identity_interval=(int(row["query_start_nt"]), int(row["query_end_nt"])),
                target_identity_interval=(target_start, target_end),
                target_region_start0=target_start,
                query_namespace="historical_paper_query_fragment_v1",
                query_ordinal=f"{row['query_id']}:{row['query_start_nt']}-{row['query_end_nt']}",
                target_namespace="historical_paper_target_slice_v1",
                target_ordinal=str(row["target_id"]),
                target_coordinate_namespace="source_fasta_0_based_half_open",
                query_recipe="historical_paper_query_slice_v1",
                target_recipe="historical_paper_target_slice_v1",
                chromosome_or_target_id=str(row["target_id"]),
            )
        )
    require(len(fixtures) == 44, f"generalization available fixture count drift: {len(fixtures)}")
    return fixtures


def paper_core_fixtures() -> list[Fixture]:
    stage = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core"
    fixtures: list[Fixture] = []
    for authority_run in sorted(stage.glob("*__baseline__0")):
        authority_outputs = sorted(authority_run.glob("output/grids/*/merged-common-TFOsorted"))
        if not authority_outputs:
            continue
        candidate_run = authority_run.with_name(authority_run.name.replace("__baseline__0", "__candidate__0"))
        config = read_json(authority_run / "run-config.json")
        row = config["manifest_row"]
        authority_query = authority_run / "inputs/query.fa"
        candidate_query = candidate_run / "inputs/query.fa"
        target = (ROOT / str(row["target_path"])).resolve()
        query_length = len(canonicalize_rows._read_single_fasta(authority_query, "query"))
        target_length = len(canonicalize_rows._read_single_fasta(target, "target"))
        for authority_output in authority_outputs:
            grid = authority_output.parent.name
            candidate_output = candidate_run / "output/grids" / grid / "merged-common-TFOsorted"
            require(candidate_output.is_file(), f"missing paired core output: {candidate_output}")
            fixtures.append(
                Fixture(
                    comparison_id=(
                        "paper_core:"
                        f"{authority_run.name.replace('__baseline__0', '')}:{grid}"
                    ),
                    dataset_class="historical_paper_core_available",
                    workload_id=str(row["workload_id"]),
                    repeat_id=f"{config['pair_id']}:{grid}",
                    authority_output=authority_output,
                    candidate_output=candidate_output,
                    authority_query_fasta=authority_query,
                    candidate_query_fasta=candidate_query,
                    authority_target_fasta=target,
                    candidate_target_fasta=target,
                    query_fasta_interval=(0, query_length),
                    target_fasta_interval=(0, target_length),
                    query_identity_interval=(int(row["query_start_nt"]), int(row["query_end_nt"])),
                    target_identity_interval=(0, target_length),
                    target_region_start0=0,
                    query_namespace="historical_paper_long_query_v1",
                    query_ordinal=str(row["query_id"]),
                    target_namespace="historical_paper_full_chromosome_v1",
                    target_ordinal=str(row["target_id"]),
                    target_coordinate_namespace="full_chromosome_fasta_0_based_half_open",
                    query_recipe="historical_paper_segmented_query_v1",
                    target_recipe="historical_paper_full_target_v1",
                    chromosome_or_target_id="chr22",
                )
            )
    require(len(fixtures) == 8, f"paper core available fixture count drift: {len(fixtures)}")
    return fixtures


def all_fixtures() -> list[Fixture]:
    fixtures = [
        *holdout_fixtures(),
        *hybrid_regression_fixtures(),
        *hybrid_holdout_fixtures(),
        *paper_core_fixtures(),
        *generalization_fixtures(),
    ]
    fixtures.sort(key=lambda fixture: fixture.comparison_id)
    require(
        len({fixture.comparison_id for fixture in fixtures}) == len(fixtures),
        "duplicate regression comparison ID",
    )
    return fixtures


def _extracted_sequence(path: Path, interval: tuple[int, int], role: str) -> str:
    source = canonicalize_rows._read_single_fasta(path, role)
    start, end = interval
    require(end <= len(source), f"{role} extraction exceeds FASTA: {path}")
    return source[start:end]


def _identity(fixture: Fixture, parameter_digest: str) -> dict[str, Any]:
    authority_query = _extracted_sequence(
        fixture.authority_query_fasta,
        fixture.query_fasta_interval,
        "query",
    )
    candidate_query = _extracted_sequence(
        fixture.candidate_query_fasta,
        fixture.query_fasta_interval,
        "query",
    )
    authority_target = _extracted_sequence(
        fixture.authority_target_fasta,
        fixture.target_fasta_interval,
        "target",
    )
    candidate_target = _extracted_sequence(
        fixture.candidate_target_fasta,
        fixture.target_fasta_interval,
        "target",
    )
    require(authority_query == candidate_query, f"query identity mismatch in {fixture.comparison_id}")
    require(authority_target == candidate_target, f"target identity mismatch in {fixture.comparison_id}")
    identity: dict[str, Any] = {
        "schema_version": 1,
        "query_ordinal_namespace": fixture.query_namespace,
        "query_source_ordinal": fixture.query_ordinal,
        "query_sequence_sha256": contract.sequence_sha256(authority_query),
        "query_extracted_interval": {
            "start0": fixture.query_identity_interval[0],
            "end0": fixture.query_identity_interval[1],
        },
        "target_ordinal_namespace": fixture.target_namespace,
        "target_source_ordinal": fixture.target_ordinal,
        "target_sequence_sha256": contract.sequence_sha256(authority_target),
        "target_extracted_interval": {
            "start0": fixture.target_identity_interval[0],
            "end0": fixture.target_identity_interval[1],
        },
        "assembly": "GRCh38",
        "target_coordinate_namespace": fixture.target_coordinate_namespace,
        "query_extraction_recipe_id": fixture.query_recipe,
        "target_extraction_recipe_id": fixture.target_recipe,
        "parameter_bundle_sha256": parameter_digest,
    }
    identity["input_pair_digest"] = contract.input_pair_digest(identity)
    return identity


def _receipt_mapping(
    fixture: Fixture,
    *,
    arm: str,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    authority = arm == "A"
    output = fixture.authority_output if authority else fixture.candidate_output
    query = fixture.authority_query_fasta if authority else fixture.candidate_query_fasta
    target = fixture.authority_target_fasta if authority else fixture.candidate_target_fasta
    return {
        "schema_version": 1,
        "receipt_kind": "biological_topk_input_receipt_v1",
        "workload_id": fixture.workload_id,
        "arm": arm,
        "evidence_role": "historical_regression_only",
        "technical_success": True,
        "output_valid": True,
        "output_sha256": sha256_file(output),
        "query_fasta": relative(query),
        "query_fasta_interval": list(fixture.query_fasta_interval),
        "target_fasta": relative(target),
        "target_fasta_interval": list(fixture.target_fasta_interval),
        "target_region_start0": fixture.target_region_start0,
        "chromosome_or_target_id": fixture.chromosome_or_target_id,
        "input_identity": dict(identity),
    }


def _fraction_value(raw: str) -> Fraction:
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(raw), 1)


def build_regression_payloads() -> tuple[dict[Path, bytes], dict[str, Any]]:
    spec = compare_candidate_topk.load_contract_spec(CONTRACT_SPEC_PATH)
    fixtures = all_fixtures()
    manifest_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    comparison_results: dict[str, dict[str, Any]] = {}
    semantic_cache: dict[
        tuple[str, str, str],
        tuple[dict[str, Any], list[dict[str, Any]]],
    ] = {}
    for fixture in fixtures:
        identity = _identity(fixture, str(spec["parameter_bundle_sha256"]))
        authority_mapping = _receipt_mapping(fixture, arm="A", identity=identity)
        candidate_mapping = _receipt_mapping(fixture, arm="G", identity=identity)
        authority_receipt = canonicalize_rows.receipt_from_mapping(
            authority_mapping,
            base_directory=ROOT,
        )
        candidate_receipt = canonicalize_rows.receipt_from_mapping(
            candidate_mapping,
            base_directory=ROOT,
        )
        cache_key = (
            str(identity["input_pair_digest"]),
            str(authority_mapping["output_sha256"]),
            str(candidate_mapping["output_sha256"]),
        )
        if cache_key in semantic_cache:
            # Each copied artifact still receives checksum and FASTA validation.
            # Equal SHA-256 payloads then share the deterministic parser/matcher result.
            canonicalize_rows.validate_receipt_files(authority_receipt, fixture.authority_output)
            canonicalize_rows.validate_receipt_files(candidate_receipt, fixture.candidate_output)
            result, details = semantic_cache[cache_key]
        else:
            result, details = compare_candidate_topk.compare(
                authority_path=fixture.authority_output,
                candidate_path=fixture.candidate_output,
                authority_receipt=authority_receipt,
                candidate_receipt=candidate_receipt,
                contract_spec=spec,
            )
            semantic_cache[cache_key] = (result, details)
        require(not result["technical_failure"], f"technical failure: {fixture.comparison_id}")
        require(result["input_identity_pass"], f"identity failure: {fixture.comparison_id}")
        comparison_results[fixture.comparison_id] = result
        manifest_rows.append(
            {
                "comparison_id": fixture.comparison_id,
                "dataset_class": fixture.dataset_class,
                "evidence_role": "historical_regression_only",
                "workload_id": fixture.workload_id,
                "repeat_id": fixture.repeat_id,
                "authority_output": relative(fixture.authority_output),
                "candidate_output": relative(fixture.candidate_output),
                "authority_output_sha256": sha256_file(fixture.authority_output),
                "candidate_output_sha256": sha256_file(fixture.candidate_output),
                "authority_query_fasta": relative(fixture.authority_query_fasta),
                "candidate_query_fasta": relative(fixture.candidate_query_fasta),
                "authority_target_fasta": relative(fixture.authority_target_fasta),
                "candidate_target_fasta": relative(fixture.candidate_target_fasta),
                "query_fasta_interval": f"{fixture.query_fasta_interval[0]}:{fixture.query_fasta_interval[1]}",
                "target_fasta_interval": f"{fixture.target_fasta_interval[0]}:{fixture.target_fasta_interval[1]}",
                "target_region_start0": fixture.target_region_start0,
                "query_ordinal_namespace": fixture.query_namespace,
                "query_source_ordinal": fixture.query_ordinal,
                "query_sequence_sha256": identity["query_sequence_sha256"],
                "target_ordinal_namespace": fixture.target_namespace,
                "target_source_ordinal": fixture.target_ordinal,
                "target_sequence_sha256": identity["target_sequence_sha256"],
                "assembly": identity["assembly"],
                "target_coordinate_namespace": fixture.target_coordinate_namespace,
                "query_extraction_recipe_id": fixture.query_recipe,
                "target_extraction_recipe_id": fixture.target_recipe,
                "parameter_bundle_sha256": identity["parameter_bundle_sha256"],
                "input_pair_digest": identity["input_pair_digest"],
                "authority_receipt_sha256": sha256_bytes(compact_json_bytes(authority_mapping)),
                "candidate_receipt_sha256": sha256_bytes(compact_json_bytes(candidate_mapping)),
            }
        )
        for mode in contract.RANKING_MODES:
            mode_result = result["modes"][mode]
            overlaps = [
                detail["target_overlap"]
                for detail in details
                if detail["ranking_mode"] == mode and detail["detail_kind"] == "matched"
            ]
            minimum_overlap = (
                min(overlaps, key=_fraction_value) if overlaps else "NA"
            )
            result_rows.append(
                {
                    "comparison_id": fixture.comparison_id,
                    "dataset_class": fixture.dataset_class,
                    "workload_id": fixture.workload_id,
                    "repeat_id": fixture.repeat_id,
                    "comparison_status": result["comparison_status"],
                    "technical_failure": int(result["technical_failure"]),
                    "ranking_mode": mode,
                    "strict_row_diagnostic": mode_result["strict_row_diagnostic"],
                    "reference_candidate_count": mode_result["reference_candidate_count"],
                    "candidate_candidate_count": mode_result["candidate_candidate_count"],
                    "matched_count": mode_result["matched_count"],
                    "unmatched_reference_count": mode_result["unmatched_reference_count"],
                    "unmatched_candidate_count": mode_result["unmatched_candidate_count"],
                    "recall": "NA" if mode_result["recall"] is None else mode_result["recall"],
                    "precision": "NA" if mode_result["precision"] is None else mode_result["precision"],
                    "top1_retained": int(mode_result["top1_retained"]),
                    "complete_set_preserved": int(mode_result["complete_set_preserved"]),
                    "set_membership": mode_result["set_membership"],
                    "ambiguous_matching": int(mode_result["ambiguous_matching"]),
                    "target_overlap_minimum": minimum_overlap,
                    "classifications": ";".join(mode_result["classifications"]) or "none",
                    "finite_rbo_fraction": mode_result["rank_diagnostic"]["finite_rbo_fraction"],
                    "binary_gate_denominator_eligible": int(
                        mode_result["binary_gate_denominator_eligible"]
                    ),
                    "binary_success": (
                        "NA" if mode_result["binary_success"] is None
                        else int(mode_result["binary_success"])
                    ),
                }
            )
        for detail in details:
            detail_rows.append(
                {
                    "comparison_id": fixture.comparison_id,
                    "dataset_class": fixture.dataset_class,
                    "workload_id": fixture.workload_id,
                    "repeat_id": fixture.repeat_id,
                    **{
                        field: (
                            "NA" if detail.get(field) is None else int(detail[field])
                            if isinstance(detail.get(field), bool)
                            else detail.get(field, "NA")
                        )
                        for field in compare_candidate_topk.DETAIL_FIELDS[1:]
                    },
                }
            )

    manifest_bytes = render_tsv(MANIFEST_FIELDS, manifest_rows)
    results_bytes = render_tsv(RESULT_FIELDS, result_rows)
    details_bytes = render_tsv(DETAIL_FIELDS, detail_rows)
    known_cases = build_known_cases(comparison_results)
    known_cases_bytes = canonical_json_bytes(known_cases)
    counts = Counter(fixture.dataset_class for fixture in fixtures)
    classification_counts = Counter(
        classification
        for result in comparison_results.values()
        for mode in result["modes"].values()
        for classification in mode["classifications"]
    )
    receipt = {
        "schema_version": 1,
        "phase": 2,
        "evidence_role": "historical_regression_only",
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "comparison_count": len(fixtures),
        "ranking_result_count": len(result_rows),
        "detail_count": len(detail_rows),
        "dataset_comparison_counts": dict(sorted(counts.items())),
        "technical_failure_count": sum(result["technical_failure"] for result in comparison_results.values()),
        "input_identity_mismatch_count": sum(not result["input_identity_pass"] for result in comparison_results.values()),
        "ambiguous_matching_result_count": sum(
            mode["ambiguous_matching"]
            for result in comparison_results.values()
            for mode in result["modes"].values()
        ),
        "classification_counts": dict(sorted(classification_counts.items())),
        "strict_row_mismatch_result_count": sum(
            mode["strict_row_diagnostic"] == "mismatch"
            for result in comparison_results.values()
            for mode in result["modes"].values()
        ),
        "set_preserved_result_count": sum(
            mode["complete_set_preserved"]
            for result in comparison_results.values()
            for mode in result["modes"].values()
        ),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "results_sha256": sha256_bytes(results_bytes),
        "details_sha256": sha256_bytes(details_bytes),
        "known_cases_sha256": sha256_bytes(known_cases_bytes),
        "all_regression_deterministic": True,
        "no_parser_or_comparator_technical_failures": True,
        "independent_validation_claim": False,
        "status": "pass",
    }
    receipt_bytes = canonical_json_bytes(receipt)
    payloads = {
        MANIFEST_PATH: manifest_bytes,
        RESULTS_PATH: results_bytes,
        DETAILS_PATH: details_bytes,
        KNOWN_CASES_PATH: known_cases_bytes,
        RECEIPT_PATH: receipt_bytes,
    }
    return payloads, receipt


def build_known_cases(comparisons: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    hq10_id = "phase2_holdout:hq10_ht02__repeat00"
    hq11_id = "phase2_holdout:hq11_ht02__repeat00"
    require(hq10_id in comparisons and hq11_id in comparisons, "known mismatch comparisons are missing")
    hq10 = comparisons[hq10_id]
    hq11 = comparisons[hq11_id]
    hq11_score = hq11["modes"]["score"]
    hq11_pair = next(
        pair
        for pair in hq11_score["matched_pairs_zero_based"]
        if pair == [2, 2]
    )
    del hq11_pair
    hq11_details = hq11_score["authority_sites"], hq11_score["candidate_sites"]
    authority_site = hq11_details[0][2]
    candidate_site = hq11_details[1][2]
    overlap = contract.reciprocal_overlap(
        (
            authority_site["representative_target_start0"],
            authority_site["representative_target_end0"],
        ),
        (
            candidate_site["representative_target_start0"],
            candidate_site["representative_target_end0"],
        ),
    )
    require(overlap == Fraction(62, 65), "hq11 target overlap fixture drift")
    require(hq10["strict_row_diagnostic"] == "mismatch", "hq10 strict-row fixture drift")
    require(hq11["strict_row_diagnostic"] == "mismatch", "hq11 strict-row fixture drift")
    require(
        all(mode["set_membership"] == "preserved" for mode in hq10["modes"].values()),
        "hq10 candidate-site set is not preserved",
    )
    require(
        all(mode["set_membership"] == "preserved" for mode in hq11["modes"].values()),
        "hq11 candidate-site set is not preserved",
    )
    return {
        "schema_version": 1,
        "implementation_has_workload_id_special_cases": False,
        "hq10_ht02": {
            "comparison_id": hq10_id,
            "strict_row_diagnostic": "mismatch",
            "unique_candidate_site_match": True,
            "set_membership": "preserved",
            "stability_classifications": hq10["modes"]["stability"]["classifications"],
        },
        "hq11_ht02": {
            "comparison_id": hq11_id,
            "strict_row_diagnostic": "mismatch",
            "target_reciprocal_overlap": "62/65",
            "unique_candidate_site_match": True,
            "set_membership": "preserved",
            "score_classifications": hq11["modes"]["score"]["classifications"],
        },
    }


def freeze_payload(
    generated: Mapping[Path, bytes],
    receipt: Mapping[str, Any],
) -> bytes:
    component_hashes = {
        path: sha256_file(ROOT / path)
        for path in COMPONENT_PATHS
    }
    fixture_digest = contract.canonical_json_sha256(
        {
            "manifest_sha256": receipt["manifest_sha256"],
            "known_cases_sha256": receipt["known_cases_sha256"],
            "legacy_clustering_fixture_sha256": sha256_file(
                PAPER / "legacy_clustering_fixtures.tsv"
            ),
        }
    )
    payload = {
        "schema_version": 1,
        "contract_name": "biological_topk_candidate_site_v1",
        "source_commit": PHASE1_COMMIT,
        "source_commit_role": "phase_2_parent_and_frozen_contract_commit",
        "python_version": platform.python_version(),
        "contract_module_sha256": sha256_file(ROOT / "reproduce/biological_topk/contract.py"),
        "contract_spec_sha256": sha256_file(CONTRACT_SPEC_PATH),
        "coordinate_mapping_sha256": sha256_file(
            ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"
        ),
        "comparator_sha256": component_hashes[
            "reproduce/biological_topk/compare_candidate_topk.py"
        ],
        "component_sha256": component_hashes,
        "fixture_sha256": fixture_digest,
        "expected_regression_digest": receipt["results_sha256"],
        "regression_manifest_sha256": receipt["manifest_sha256"],
        "regression_details_sha256": receipt["details_sha256"],
        "known_cases_sha256": receipt["known_cases_sha256"],
        "regression_receipt_sha256": sha256_bytes(generated[RECEIPT_PATH]),
        "default_fail_closed": True,
        "independent_validation_claim": False,
    }
    return canonical_json_bytes(payload)


def build() -> dict[Path, bytes]:
    generated, receipt = build_regression_payloads()
    generated[FREEZE_PATH] = freeze_payload(generated, receipt)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payloads = build()
    except (RegressionError, contract.ContractError, StopIteration) as error:
        parser.exit(1, f"Phase 2 regression build failed: {error}\n")
    if args.check:
        stale = [relative(path) for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
        if stale:
            parser.exit(1, "stale Phase 2 regression artifacts: " + ", ".join(stale) + "\n")
        print("biological Top-K Phase 2 regression artifacts reproduce exactly")
        return 0
    for path, payload in payloads.items():
        atomic_write(path, payload)
    print(f"wrote {len(payloads)} deterministic Phase 2 regression artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
