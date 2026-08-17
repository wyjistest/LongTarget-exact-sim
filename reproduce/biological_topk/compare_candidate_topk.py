#!/usr/bin/env python3
"""Fail-closed clustered TFO candidate-site comparator CLI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

try:
    from . import (
        canonicalize_rows,
        contract,
        match_candidate_sites,
        recluster_candidate_sites,
    )
except ImportError:  # pragma: no cover
    import canonicalize_rows  # type: ignore[no-redef]
    import contract  # type: ignore[no-redef]
    import match_candidate_sites  # type: ignore[no-redef]
    import recluster_candidate_sites  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
DETAIL_FIELDS = (
    "workload_id",
    "ranking_mode",
    "mode_classifications",
    "detail_kind",
    "authority_index",
    "candidate_index",
    "authority_rank",
    "candidate_rank",
    "authority_site_digest",
    "candidate_site_digest",
    "target_overlap",
    "query_representative_overlap",
    "query_cluster_overlap",
    "ungapped_tfo_equal",
    "ungapped_tts_equal",
    "target_endpoint_l1",
    "query_endpoint_l1",
    "cluster_center_distance",
    "query_endpoint_shift",
    "target_endpoint_shift",
    "cluster_geometry_shift",
    "rank_displacement",
    "score_delta_candidate_minus_authority",
    "nt_delta_candidate_minus_authority",
    "stability_delta_candidate_minus_authority",
    "strict_row_equal",
)


class ComparatorError(contract.ContractError):
    """Raised for a fail-closed comparator precondition or technical error."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract_spec(path: Path) -> Mapping[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ComparatorError(f"missing or unsafe contract spec: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ComparatorError(f"invalid contract spec JSON: {error}") from error
    if not isinstance(value, dict):
        raise ComparatorError("contract spec must be a JSON object")
    required = {
        "schema_version": 2,
        "contract_name": "biological_topk_candidate_site_v1",
        "scientific_object": "clustered_TFO_query_target_candidate_site",
        "k": 5,
        "cluster_distance": 15,
        "score_representation": "integral_exact",
    }
    for field, expected in required.items():
        if value.get(field) != expected:
            raise ComparatorError(f"contract spec {field} drift")
    if value.get("ranking_mode_values") != ["score", "stability", "nt"]:
        raise ComparatorError("contract ranking modes drift")
    if value.get("row_eligibility") != {"nt_bp": 50, "nt_operator": ">"}:
        raise ComparatorError("contract row eligibility drift")
    matching = value.get("matching")
    if not isinstance(matching, dict):
        raise ComparatorError("contract matching section is missing")
    for field in (
        "query_representative_reciprocal_overlap_min",
        "query_cluster_span_reciprocal_overlap_min",
        "target_representative_reciprocal_overlap_min",
    ):
        if matching.get(field) != {"denominator": 10, "numerator": 9}:
            raise ComparatorError(f"contract {field} drift")
    coordinate_table = ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"
    if value.get("coordinate_mapping_table_sha256") != _sha256_file(coordinate_table):
        raise ComparatorError("coordinate mapping table digest drift")
    return value


def compare(
    *,
    authority_path: Path,
    candidate_path: Path,
    authority_receipt: canonicalize_rows.InputReceipt,
    candidate_receipt: canonicalize_rows.InputReceipt,
    contract_spec: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if authority_receipt.arm != "A" or candidate_receipt.arm != "G":
        raise ComparatorError("authority/candidate receipt arms must be A/G")
    mismatches = canonicalize_rows.input_identity_mismatches(
        authority_receipt,
        candidate_receipt,
    )
    if mismatches:
        return (
            {
                "schema_version": 1,
                "contract_name": contract_spec["contract_name"],
                "workload_id": authority_receipt.workload_id,
                "comparison_status": "technical_failure",
                "technical_failure": True,
                "technical_failure_reason": "input_identity_mismatch",
                "input_identity_pass": False,
                "input_identity_mismatches": list(mismatches),
                "matching_started": False,
                "contract_pass": False,
                "strict_row_diagnostic": "not_started",
                "modes": {},
            },
            [
                {
                    "workload_id": authority_receipt.workload_id,
                    "ranking_mode": "NA",
                    "mode_classifications": "input identity mismatch",
                    "detail_kind": "input_identity_mismatch",
                }
            ],
        )
    authority_validated = canonicalize_rows.validate_receipt_files(
        authority_receipt,
        authority_path,
    )
    candidate_validated = canonicalize_rows.validate_receipt_files(
        candidate_receipt,
        candidate_path,
    )
    authority_rows = canonicalize_rows.canonicalize_output(
        authority_path,
        authority_validated,
    )
    authority_row_count = len(authority_rows)
    k = int(contract_spec["k"])
    distance = int(contract_spec["cluster_distance"])
    minimum_nt = int(contract_spec["row_eligibility"]["nt_bp"])
    authority_rankings = recluster_candidate_sites.all_rankings(
        authority_rows,
        authority_receipt,
        k=k,
        distance=distance,
        minimum_nt_bp=minimum_nt,
    )
    del authority_rows
    if authority_receipt.output_sha256 == candidate_receipt.output_sha256:
        candidate_row_count = authority_row_count
        candidate_rankings = {
            mode: tuple(replace(site, arm="G") for site in sites)
            for mode, sites in authority_rankings.items()
        }
    else:
        candidate_rows = canonicalize_rows.canonicalize_output(
            candidate_path,
            candidate_validated,
        )
        candidate_row_count = len(candidate_rows)
        candidate_rankings = recluster_candidate_sites.all_rankings(
            candidate_rows,
            candidate_receipt,
            k=k,
            distance=distance,
            minimum_nt_bp=minimum_nt,
        )
        del candidate_rows
    modes: dict[str, Any] = {}
    detail_rows: list[dict[str, Any]] = []
    for mode in contract.RANKING_MODES:
        result, details = match_candidate_sites.compare_ranked_sites(
            authority_rankings[mode],
            candidate_rankings[mode],
        )
        result["authority_sites"] = [site.as_dict() for site in authority_rankings[mode]]
        result["candidate_sites"] = [site.as_dict() for site in candidate_rankings[mode]]
        modes[mode] = result
        for detail in details:
            detail_rows.append(
                {
                    "workload_id": authority_receipt.workload_id,
                    "ranking_mode": mode,
                    "mode_classifications": ";".join(result["classifications"]),
                    **detail,
                }
            )
    ambiguous = any(result["ambiguous_matching"] for result in modes.values())
    clean_double_empty = all(result["double_empty"] for result in modes.values())
    contract_pass = all(result["binary_success"] is True for result in modes.values())
    strict_equal = all(result["strict_row_equal"] for result in modes.values())
    if ambiguous:
        status = "technical_failure"
    elif clean_double_empty:
        status = "clean_double_empty_noninformative"
    elif contract_pass:
        status = "pass"
    else:
        status = "scientific_mismatch"
    result = {
        "schema_version": 1,
        "contract_name": contract_spec["contract_name"],
        "workload_id": authority_receipt.workload_id,
        "comparison_status": status,
        "technical_failure": ambiguous,
        "technical_failure_reason": "ambiguous_matching" if ambiguous else None,
        "input_identity_pass": True,
        "input_identity_mismatches": [],
        "matching_started": True,
        "authority_output_row_count": authority_row_count,
        "candidate_output_row_count": candidate_row_count,
        "contract_pass": contract_pass,
        "strict_row_diagnostic": "match" if strict_equal else "mismatch",
        "strict_row_equal": strict_equal,
        "clean_double_empty": clean_double_empty,
        "modes": modes,
    }
    return result, detail_rows


def compare_paths(
    *,
    authority_path: Path,
    candidate_path: Path,
    authority_receipt_path: Path,
    candidate_receipt_path: Path,
    contract_spec_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = load_contract_spec(contract_spec_path)
    authority_receipt = canonicalize_rows.load_receipt(authority_receipt_path)
    candidate_receipt = canonicalize_rows.load_receipt(candidate_receipt_path)
    return compare(
        authority_path=authority_path,
        candidate_path=candidate_path,
        authority_receipt=authority_receipt,
        candidate_receipt=candidate_receipt,
        contract_spec=spec,
    )


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _details_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=DETAIL_FIELDS,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare clustered TFO candidate-site Top-K outputs under v1."
    )
    parser.add_argument("--authority", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--authority-receipt", required=True, type=Path)
    parser.add_argument("--candidate-receipt", required=True, type=Path)
    parser.add_argument("--contract-spec", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--details-tsv", required=True, type=Path)
    parser.add_argument(
        "--fail-closed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="return nonzero for a scientific contract mismatch (default: enabled)",
    )
    args = parser.parse_args()
    try:
        result, details = compare_paths(
            authority_path=args.authority,
            candidate_path=args.candidate,
            authority_receipt_path=args.authority_receipt,
            candidate_receipt_path=args.candidate_receipt,
            contract_spec_path=args.contract_spec,
        )
    except Exception as error:  # Every malformed/unsupported input becomes an auditable failure.
        result = {
            "schema_version": 1,
            "contract_name": "biological_topk_candidate_site_v1",
            "workload_id": None,
            "comparison_status": "technical_failure",
            "technical_failure": True,
            "technical_failure_reason": type(error).__name__,
            "error": str(error),
            "input_identity_pass": False,
            "matching_started": False,
            "contract_pass": False,
            "strict_row_diagnostic": "not_started",
            "modes": {},
        }
        details = []
    _atomic_write(args.output_json, _json_bytes(result))
    _atomic_write(args.details_tsv, _details_bytes(details))
    if result["comparison_status"] == "technical_failure":
        print(
            f"candidate-site comparator technical failure: {result.get('technical_failure_reason')}",
            file=sys.stderr,
        )
        return 2
    if args.fail_closed and result["comparison_status"] == "scientific_mismatch":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
