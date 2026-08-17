#!/usr/bin/env python3
"""Create and validate gasal2_candidate_sites_tsv_v1 artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parent
CONTRACT_ROOT = (
    SCRIPT_DIR / "biological_topk"
    if (SCRIPT_DIR / "biological_topk").is_dir()
    else REPOSITORY_ROOT / "reproduce/biological_topk"
)
sys.path.insert(0, str(CONTRACT_ROOT))

import canonicalize_rows  # type: ignore[import-not-found]  # noqa: E402
import contract  # type: ignore[import-not-found]  # noqa: E402
import recluster_candidate_sites  # type: ignore[import-not-found]  # noqa: E402


SCHEMA_VERSION = "1"
OUTPUT_SCHEMA = "gasal2_candidate_sites_tsv_v1"
SCIENTIFIC_CONTRACT = "biological_topk_candidate_site_v1"
SOFTWARE_EPOCH = "submission_rc_v2_2"
PARAMETER_BUNDLE_SHA256 = "110752c4078bc2b300ad4e92e2495ea868c365486e540da7002fc3e19a18241a"
COORDINATE_SYSTEM = "0_based_half_open"
RANKING_ORDER = ("score", "stability", "nt")
RANKING_KEYS = {
    "score": ("score", "nt", "mean_stability", "native_raw_row_key"),
    "stability": ("mean_stability", "nt", "score", "native_raw_row_key"),
    "nt": ("nt", "score", "mean_stability", "native_raw_row_key"),
}
CANDIDATE_SITE_IDENTITY_PAYLOAD = (
    "input_pair_digest",
    "chromosome_or_target_id",
    "direction",
    "strand",
    "rule",
    "representative_query_interval0",
    "cluster_query_span0",
    "representative_target_interval0",
    "legacy_cluster_center",
    "ungapped_tfo_sha256",
    "ungapped_tts_sha256",
)
FIELDS = (
    "schema_version",
    "output_schema",
    "scientific_contract",
    "software_epoch",
    "coordinate_system",
    "workload_id",
    "input_pair_digest",
    "ranking_mode",
    "rank",
    "candidate_site_identity_digest",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_sequence_sha256",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_sequence_sha256",
    "assembly",
    "target_coordinate_namespace",
    "chromosome_or_target_id",
    "direction",
    "strand",
    "rule",
    "cluster_query_span_start0",
    "cluster_query_span_end0",
    "representative_query_start0",
    "representative_query_end0",
    "representative_target_start0",
    "representative_target_end0",
    "representative_genome_start0",
    "representative_genome_end0",
    "legacy_cluster_local_index",
    "legacy_cluster_center",
    "legacy_cluster_member_count",
    "score",
    "nt",
    "mean_stability",
    "mean_identity",
    "ungapped_tfo_sha256",
    "ungapped_tts_sha256",
    "within_arm_ambiguous_candidate_site",
)


class CandidateSitesError(ValueError):
    """Raised when a candidate-sites product cannot satisfy its schema."""


@dataclass(frozen=True)
class FastaRecord:
    path: Path
    header: str
    sequence: str


@dataclass(frozen=True)
class ProductIdentity:
    workload_id: str | None = None
    query_ordinal_namespace: str = "user_query_fasta_header_v1"
    query_source_ordinal: str | None = None
    target_ordinal_namespace: str = "user_target_fasta_header_v1"
    target_source_ordinal: str | None = None
    assembly: str = "unspecified"
    target_coordinate_namespace: str = "target_fasta_0_based_half_open"
    query_extraction_recipe_id: str = "full_single_record_fasta_v1"
    target_extraction_recipe_id: str = "full_single_record_fasta_v1"
    target_region_start0: int = 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_single_fasta(path: Path, role: str) -> FastaRecord:
    if not path.is_file() or path.is_symlink():
        raise CandidateSitesError(f"missing or unsafe {role} FASTA: {path}")
    header: str | None = None
    sequence: list[str] = []
    record_count = 0
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CandidateSitesError(f"non-ASCII {role} FASTA: {path}") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            record_count += 1
            if record_count > 1:
                raise CandidateSitesError(f"{role} FASTA must contain exactly one record")
            header = line[1:].strip()
            if not header:
                raise CandidateSitesError(f"empty {role} FASTA header at line {line_number}")
            continue
        if header is None:
            raise CandidateSitesError(f"{role} FASTA sequence precedes its header")
        normalized = line.upper()
        invalid = sorted(set(normalized) - set("ACGT"))
        if invalid:
            raise CandidateSitesError(
                f"{role} FASTA contains unsupported characters: {''.join(invalid)}"
            )
        sequence.append(normalized)
    if record_count != 1 or header is None or not sequence:
        raise CandidateSitesError(f"{role} FASTA must contain one nonempty record")
    return FastaRecord(path=path.resolve(), header=header, sequence="".join(sequence))


def build_receipt(
    *,
    query: FastaRecord,
    target: FastaRecord,
    tfosorted: Path,
    identity: ProductIdentity,
) -> canonicalize_rows.InputReceipt:
    if identity.target_region_start0 < 0:
        raise CandidateSitesError("target_region_start0 must be nonnegative")
    query_ordinal = identity.query_source_ordinal or query.header
    target_ordinal = identity.target_source_ordinal or target.header
    pair_identity: dict[str, Any] = {
        "schema_version": 1,
        "query_ordinal_namespace": identity.query_ordinal_namespace,
        "query_source_ordinal": query_ordinal,
        "query_sequence_sha256": contract.sequence_sha256(query.sequence),
        "query_extracted_interval": {"start0": 0, "end0": len(query.sequence)},
        "target_ordinal_namespace": identity.target_ordinal_namespace,
        "target_source_ordinal": target_ordinal,
        "target_sequence_sha256": contract.sequence_sha256(target.sequence),
        "target_extracted_interval": {
            "start0": identity.target_region_start0,
            "end0": identity.target_region_start0 + len(target.sequence),
        },
        "assembly": identity.assembly,
        "target_coordinate_namespace": identity.target_coordinate_namespace,
        "query_extraction_recipe_id": identity.query_extraction_recipe_id,
        "target_extraction_recipe_id": identity.target_extraction_recipe_id,
        "parameter_bundle_sha256": PARAMETER_BUNDLE_SHA256,
    }
    pair_identity["input_pair_digest"] = contract.input_pair_digest(pair_identity)
    workload_id = identity.workload_id or f"product_{pair_identity['input_pair_digest'][:20]}"
    return canonicalize_rows.InputReceipt(
        source_path=None,
        workload_id=workload_id,
        arm="G",
        evidence_role="gpu_screen_product",
        technical_success=True,
        output_valid=True,
        output_sha256=sha256_file(tfosorted),
        query_fasta=query.path,
        query_fasta_interval=(0, len(query.sequence)),
        target_fasta=target.path,
        target_fasta_interval=(0, len(target.sequence)),
        target_region_start0=identity.target_region_start0,
        chromosome_or_target_id=str(target_ordinal),
        input_identity=pair_identity,
    )


def _product_row(site: recluster_candidate_sites.CandidateSiteRecord) -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "output_schema": OUTPUT_SCHEMA,
        "scientific_contract": SCIENTIFIC_CONTRACT,
        "software_epoch": SOFTWARE_EPOCH,
        "coordinate_system": COORDINATE_SYSTEM,
        "workload_id": site.workload_id,
        "input_pair_digest": site.input_pair_digest,
        "ranking_mode": site.ranking_mode,
        "rank": str(site.rank),
        "candidate_site_identity_digest": site.candidate_site_identity_digest,
        "query_ordinal_namespace": site.query_ordinal_namespace,
        "query_source_ordinal": str(site.query_source_ordinal),
        "query_sequence_sha256": site.query_sequence_sha256,
        "target_ordinal_namespace": site.target_ordinal_namespace,
        "target_source_ordinal": str(site.target_source_ordinal),
        "target_sequence_sha256": site.target_sequence_sha256,
        "assembly": site.assembly,
        "target_coordinate_namespace": site.target_coordinate_namespace,
        "chromosome_or_target_id": site.chromosome_or_target_id,
        "direction": site.direction,
        "strand": site.strand,
        "rule": str(site.rule),
        "cluster_query_span_start0": str(site.cluster_query_span_start0),
        "cluster_query_span_end0": str(site.cluster_query_span_end0),
        "representative_query_start0": str(site.representative_query_start0),
        "representative_query_end0": str(site.representative_query_end0),
        "representative_target_start0": str(site.representative_target_start0),
        "representative_target_end0": str(site.representative_target_end0),
        "representative_genome_start0": str(site.representative_genome_start0),
        "representative_genome_end0": str(site.representative_genome_end0),
        "legacy_cluster_local_index": str(site.legacy_cluster_local_index),
        "legacy_cluster_center": str(site.legacy_cluster_center),
        "legacy_cluster_member_count": str(site.legacy_cluster_member_count),
        "score": site.score_decimal_string,
        "nt": str(site.nt_integer),
        "mean_stability": site.mean_stability_decimal,
        "mean_identity": site.mean_identity_decimal,
        "ungapped_tfo_sha256": site.ungapped_tfo_sha256,
        "ungapped_tts_sha256": site.ungapped_tts_sha256,
        "within_arm_ambiguous_candidate_site": (
            "1" if site.within_arm_ambiguous_candidate_site else "0"
        ),
    }


def write_candidate_sites(
    *,
    query_fasta: Path,
    target_fasta: Path,
    tfosorted: Path,
    destination: Path,
    identity: ProductIdentity,
    top_k: int = 5,
) -> dict[str, Any]:
    if top_k != 5:
        raise CandidateSitesError("gasal2_candidate_sites_tsv_v1 requires Top-K=5")
    query = read_single_fasta(query_fasta, "query")
    target = read_single_fasta(target_fasta, "target")
    receipt = build_receipt(query=query, target=target, tfosorted=tfosorted, identity=identity)
    try:
        validated = canonicalize_rows.validate_receipt_files(receipt, tfosorted)
        rows = canonicalize_rows.canonicalize_output(tfosorted, validated)
        rankings = recluster_candidate_sites.all_rankings(
            rows,
            receipt,
            k=top_k,
            distance=15,
            minimum_nt_bp=50,
        )
    except contract.ContractError as error:
        raise CandidateSitesError(f"candidate output violates scientific contract: {error}") from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for mode in RANKING_ORDER:
            for site in rankings[mode]:
                writer.writerow(_product_row(site))
    summary = validate_candidate_sites(destination)
    summary.update(
        {
            "input_pair_digest": receipt.input_identity["input_pair_digest"],
            "workload_id": receipt.workload_id,
            "native_output_sha256": receipt.output_sha256,
        }
    )
    return summary


def _canonical_nonnegative(raw: str, label: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise CandidateSitesError(f"{label} must be an integer") from error
    if value < 0 or str(value) != raw:
        raise CandidateSitesError(f"{label} must be a canonical nonnegative integer")
    return value


def _candidate_site_identity_payload(row: Mapping[str, str]) -> list[Any]:
    return [
        row["input_pair_digest"],
        row["chromosome_or_target_id"],
        row["direction"],
        row["strand"],
        _canonical_nonnegative(row["rule"], "rule"),
        [
            _canonical_nonnegative(row["representative_query_start0"], "representative_query_start0"),
            _canonical_nonnegative(row["representative_query_end0"], "representative_query_end0"),
        ],
        [
            _canonical_nonnegative(row["cluster_query_span_start0"], "cluster_query_span_start0"),
            _canonical_nonnegative(row["cluster_query_span_end0"], "cluster_query_span_end0"),
        ],
        [
            _canonical_nonnegative(row["representative_target_start0"], "representative_target_start0"),
            _canonical_nonnegative(row["representative_target_end0"], "representative_target_end0"),
        ],
        _canonical_nonnegative(row["legacy_cluster_center"], "legacy_cluster_center"),
        row["ungapped_tfo_sha256"],
        row["ungapped_tts_sha256"],
    ]


def validate_candidate_sites(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise CandidateSitesError(f"missing or unsafe candidate-sites TSV: {path}")
    with path.open(newline="", encoding="utf-8", errors="strict") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise CandidateSitesError(f"candidate-sites columns drift: {reader.fieldnames}")
        rows = list(reader)
    expected_order: list[tuple[int, int]] = []
    observed_order: list[tuple[int, int]] = []
    grouped: dict[str, list[int]] = {mode: [] for mode in RANKING_ORDER}
    pair_digests: set[str] = set()
    workload_ids: set[str] = set()
    for row_number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise CandidateSitesError(f"malformed candidate-sites row {row_number}")
        constants = {
            "schema_version": SCHEMA_VERSION,
            "output_schema": OUTPUT_SCHEMA,
            "scientific_contract": SCIENTIFIC_CONTRACT,
            "software_epoch": SOFTWARE_EPOCH,
            "coordinate_system": COORDINATE_SYSTEM,
        }
        for field, expected in constants.items():
            if row[field] != expected:
                raise CandidateSitesError(f"{field} drift at row {row_number}")
        mode = row["ranking_mode"]
        if mode not in RANKING_ORDER:
            raise CandidateSitesError(f"invalid ranking mode at row {row_number}")
        rank = _canonical_nonnegative(row["rank"], "rank")
        if not 1 <= rank <= 5:
            raise CandidateSitesError(f"rank outside 1..5 at row {row_number}")
        grouped[mode].append(rank)
        observed_order.append((RANKING_ORDER.index(mode), rank))
        for field in (
            "rule",
            "cluster_query_span_start0",
            "cluster_query_span_end0",
            "representative_query_start0",
            "representative_query_end0",
            "representative_target_start0",
            "representative_target_end0",
            "representative_genome_start0",
            "representative_genome_end0",
            "legacy_cluster_local_index",
            "legacy_cluster_center",
            "legacy_cluster_member_count",
            "nt",
        ):
            _canonical_nonnegative(row[field], field)
        for field in ("score", "mean_stability", "mean_identity"):
            contract.parse_decimal(row[field])
        for field in (
            "candidate_site_identity_digest",
            "query_sequence_sha256",
            "target_sequence_sha256",
            "ungapped_tfo_sha256",
            "ungapped_tts_sha256",
            "input_pair_digest",
        ):
            if len(row[field]) != 64 or any(char not in "0123456789abcdef" for char in row[field]):
                raise CandidateSitesError(f"invalid SHA-256 field {field} at row {row_number}")
        for field in (
            "workload_id",
            "query_ordinal_namespace",
            "query_source_ordinal",
            "target_ordinal_namespace",
            "target_source_ordinal",
            "assembly",
            "target_coordinate_namespace",
            "chromosome_or_target_id",
        ):
            if not row[field]:
                raise CandidateSitesError(f"empty identity field {field} at row {row_number}")
        if row["direction"] not in contract.CURRENT_REACHABLE_DIRECTIONS:
            raise CandidateSitesError(f"invalid direction at row {row_number}")
        if row["strand"] not in contract.SUPPORTED_STRANDS:
            raise CandidateSitesError(f"invalid strand at row {row_number}")
        intervals = {
            "cluster query span": (
                int(row["cluster_query_span_start0"]),
                int(row["cluster_query_span_end0"]),
            ),
            "representative query": (
                int(row["representative_query_start0"]),
                int(row["representative_query_end0"]),
            ),
            "representative target": (
                int(row["representative_target_start0"]),
                int(row["representative_target_end0"]),
            ),
            "representative genome": (
                int(row["representative_genome_start0"]),
                int(row["representative_genome_end0"]),
            ),
        }
        for label, (start0, end0) in intervals.items():
            if start0 >= end0:
                raise CandidateSitesError(f"empty or reversed {label} at row {row_number}")
        query = intervals["representative query"]
        cluster = intervals["cluster query span"]
        if not cluster[0] <= query[0] < query[1] <= cluster[1]:
            raise CandidateSitesError(f"representative query leaves cluster span at row {row_number}")
        target = intervals["representative target"]
        genome = intervals["representative genome"]
        if target[1] - target[0] != genome[1] - genome[0] or genome[0] < target[0]:
            raise CandidateSitesError(f"target/genome coordinate mapping drift at row {row_number}")
        observed_site_digest = contract.canonical_json_sha256(
            _candidate_site_identity_payload(row)
        )
        if row["candidate_site_identity_digest"] != observed_site_digest:
            raise CandidateSitesError(f"candidate-site identity digest drift at row {row_number}")
        if row["within_arm_ambiguous_candidate_site"] not in {"0", "1"}:
            raise CandidateSitesError(f"invalid ambiguity flag at row {row_number}")
        pair_digests.add(row["input_pair_digest"])
        workload_ids.add(row["workload_id"])
    for mode, ranks in grouped.items():
        if ranks != list(range(1, len(ranks) + 1)):
            raise CandidateSitesError(f"non-contiguous {mode} ranks")
    expected_order = sorted(observed_order)
    if observed_order != expected_order:
        raise CandidateSitesError("candidate-sites rows are not deterministically ordered")
    if len(pair_digests) > 1 or len(workload_ids) > 1:
        raise CandidateSitesError("candidate-sites rows contain multiple input identities")
    return {
        "schema_version": SCHEMA_VERSION,
        "output_schema": OUTPUT_SCHEMA,
        "scientific_contract": SCIENTIFIC_CONTRACT,
        "software_epoch": SOFTWARE_EPOCH,
        "coordinate_system": COORDINATE_SYSTEM,
        "row_count": len(rows),
        "header_only": not rows,
        "ranking_row_counts": {mode: len(grouped[mode]) for mode in RANKING_ORDER},
        "sha256": sha256_file(path),
    }


def schema_descriptor() -> Mapping[str, Any]:
    return {
        "schema_version": 1,
        "schema_id": OUTPUT_SCHEMA,
        "format": "UTF-8 TSV with LF line endings",
        "scientific_contract": SCIENTIFIC_CONTRACT,
        "software_epoch": SOFTWARE_EPOCH,
        "coordinate_system": COORDINATE_SYSTEM,
        "columns": list(FIELDS),
        "primary_order": ["ranking_mode(score,stability,nt)", "rank_ascending"],
        "ranking_keys_descending": {
            mode: list(RANKING_KEYS[mode]) for mode in RANKING_ORDER
        },
        "tie_breaking": "native_raw_row_key_reverse_lexicographic",
        "top_k": 5,
        "top_k_stage": "after_legacy_clustering_and_per_mode_representative_selection",
        "empty_result": "header_only",
        "local_cluster_id_role": "arm_local_provenance_only",
        "cross_arm_equality_key": "frozen biological_topk_candidate_site_v1 matcher",
        "candidate_site_identity_payload": list(CANDIDATE_SITE_IDENTITY_PAYLOAD),
    }


if __name__ == "__main__":
    print(json.dumps(schema_descriptor(), indent=2, sort_keys=True))
