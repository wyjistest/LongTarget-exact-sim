#!/usr/bin/env python3
"""Cross-arm candidate-site matching and exact workload metrics."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Any, Sequence

try:
    from . import contract, rank_diagnostics, recluster_candidate_sites
except ImportError:  # pragma: no cover
    import contract  # type: ignore[no-redef]
    import rank_diagnostics  # type: ignore[no-redef]
    import recluster_candidate_sites  # type: ignore[no-redef]


SiteRecord = recluster_candidate_sites.CandidateSiteRecord


def _fraction(value: Fraction) -> str:
    return rank_diagnostics.fraction_text(value)


def _decimal_delta(candidate: str, authority: str) -> str:
    return contract.canonical_decimal(
        contract.parse_decimal(candidate) - contract.parse_decimal(authority)
    )


def _objective(value: tuple[Any, ...]) -> list[int | str]:
    rendered: list[int | str] = []
    for component in value:
        rendered.append(_fraction(component) if isinstance(component, Fraction) else int(component))
    return rendered


def _matched_detail(
    authority: SiteRecord,
    candidate: SiteRecord,
    left_index: int,
    right_index: int,
) -> dict[str, Any]:
    quality = contract.eligible_edge(authority.matching_site(), candidate.matching_site())
    if quality is None:
        raise contract.ContractError("selected matching pair is not an eligible edge")
    strict_equal = authority.strict_row_digest_diagnostic == candidate.strict_row_digest_diagnostic
    query_shift = (
        authority.representative_query_start0 != candidate.representative_query_start0
        or authority.representative_query_end0 != candidate.representative_query_end0
    )
    target_shift = (
        authority.representative_target_start0 != candidate.representative_target_start0
        or authority.representative_target_end0 != candidate.representative_target_end0
    )
    cluster_shift = (
        authority.cluster_query_span_start0 != candidate.cluster_query_span_start0
        or authority.cluster_query_span_end0 != candidate.cluster_query_span_end0
        or authority.legacy_cluster_center != candidate.legacy_cluster_center
    )
    return {
        "detail_kind": "matched",
        "authority_index": left_index,
        "candidate_index": right_index,
        "authority_rank": authority.rank,
        "candidate_rank": candidate.rank,
        "authority_site_digest": authority.candidate_site_identity_digest,
        "candidate_site_digest": candidate.candidate_site_identity_digest,
        "target_overlap": _fraction(quality.target_overlap),
        "query_representative_overlap": _fraction(quality.query_rep_overlap),
        "query_cluster_overlap": _fraction(quality.query_cluster_overlap),
        "ungapped_tfo_equal": bool(quality.ungapped_tfo_equal),
        "ungapped_tts_equal": bool(quality.ungapped_tts_equal),
        "target_endpoint_l1": quality.target_endpoint_l1,
        "query_endpoint_l1": quality.query_endpoint_l1,
        "cluster_center_distance": quality.cluster_center_distance,
        "query_endpoint_shift": query_shift,
        "target_endpoint_shift": target_shift,
        "cluster_geometry_shift": cluster_shift,
        "rank_displacement": candidate.rank - authority.rank,
        "score_delta_candidate_minus_authority": _decimal_delta(
            candidate.score_decimal_string,
            authority.score_decimal_string,
        ),
        "nt_delta_candidate_minus_authority": candidate.nt_integer - authority.nt_integer,
        "stability_delta_candidate_minus_authority": _decimal_delta(
            candidate.mean_stability_decimal,
            authority.mean_stability_decimal,
        ),
        "strict_row_equal": strict_equal,
    }


def compare_ranked_sites(
    authority: Sequence[SiteRecord],
    candidate: Sequence[SiteRecord],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if authority and candidate and authority[0].ranking_mode != candidate[0].ranking_mode:
        raise contract.ContractError("ranking modes differ across arms")
    mode = authority[0].ranking_mode if authority else (
        candidate[0].ranking_mode if candidate else "unknown"
    )
    if any(site.ranking_mode != mode for site in (*authority, *candidate)):
        raise contract.ContractError("mixed ranking modes in a candidate-site list")
    matched = contract.match_candidate_sites(
        [site.matching_site() for site in authority],
        [site.matching_site() for site in candidate],
    )
    within_arm_ambiguity = any(
        site.within_arm_ambiguous_candidate_site for site in (*authority, *candidate)
    )
    ambiguous = matched.ambiguous or within_arm_ambiguity
    pairs = tuple(matched.pairs)
    left_matched = {left for left, _ in pairs}
    right_matched = {right for _, right in pairs}
    unmatched_authority = [index for index in range(len(authority)) if index not in left_matched]
    unmatched_candidate = [index for index in range(len(candidate)) if index not in right_matched]
    details = [
        _matched_detail(authority[left], candidate[right], left, right)
        for left, right in pairs
    ]
    for index in unmatched_authority:
        details.append(
            {
                "detail_kind": "unmatched_authority",
                "authority_index": index,
                "candidate_index": None,
                "authority_rank": authority[index].rank,
                "candidate_rank": None,
                "authority_site_digest": authority[index].candidate_site_identity_digest,
                "candidate_site_digest": None,
            }
        )
    for index in unmatched_candidate:
        details.append(
            {
                "detail_kind": "unmatched_candidate",
                "authority_index": None,
                "candidate_index": index,
                "authority_rank": None,
                "candidate_rank": candidate[index].rank,
                "authority_site_digest": None,
                "candidate_site_digest": candidate[index].candidate_site_identity_digest,
            }
        )

    reference_count = len(authority)
    candidate_count = len(candidate)
    matched_count = len(pairs)
    clean_double_empty = reference_count == 0 and candidate_count == 0
    if clean_double_empty:
        recall = None
        precision = None
    elif ambiguous:
        recall = "0"
        precision = "0"
    else:
        recall = _fraction(Fraction(matched_count, reference_count)) if reference_count else "0"
        precision = _fraction(Fraction(matched_count, candidate_count)) if candidate_count else "0"
    top1 = bool(not ambiguous and (0, 0) in pairs)
    complete_set = bool(
        not ambiguous
        and reference_count > 0
        and matched_count == reference_count
        and matched_count == candidate_count
    )
    denominator = contract.classify_denominator(
        authority_technical_success=not within_arm_ambiguity,
        candidate_technical_success=not within_arm_ambiguity,
        input_identity_pass=True,
        authority_output_valid=True,
        candidate_output_valid=True,
        authority_candidate_count=reference_count,
        candidate_candidate_count=candidate_count,
        complete_set_success=complete_set and top1,
    )
    strict_equal = bool(
        not ambiguous
        and matched_count == reference_count == candidate_count
        and all(detail.get("strict_row_equal") is True for detail in details)
    )
    endpoint_shift = any(
        detail.get("query_endpoint_shift")
        or detail.get("target_endpoint_shift")
        or detail.get("cluster_geometry_shift")
        for detail in details
        if detail["detail_kind"] == "matched"
    )
    rank_displaced = any(
        detail.get("rank_displacement") != 0
        for detail in details
        if detail["detail_kind"] == "matched"
    )
    classifications: list[str] = []
    if ambiguous:
        classifications.append("ambiguous matching")
    if unmatched_authority and unmatched_candidate:
        classifications.append("true candidate-site substitution")
    if unmatched_candidate:
        classifications.append("extra candidate site")
    if unmatched_authority:
        classifications.append("missing candidate site")
    if complete_set and rank_displaced:
        classifications.append("set-preserving rank displacement")
    if endpoint_shift:
        classifications.append("same candidate site endpoint shift")
    if not strict_equal:
        classifications.append("strict-row diagnostic mismatch")
    if complete_set and not strict_equal and not endpoint_shift and not rank_displaced:
        classifications.insert(0, "representation-only difference")

    diagnostic_pairs = () if ambiguous else pairs
    ranks = rank_diagnostics.rank_diagnostics(
        reference_count,
        candidate_count,
        diagnostic_pairs,
    )
    result = {
        "ranking_mode": mode,
        "matching_started": True,
        "reference_candidate_count": reference_count,
        "candidate_candidate_count": candidate_count,
        "matched_count": matched_count,
        "unmatched_reference_count": len(unmatched_authority),
        "unmatched_candidate_count": len(unmatched_candidate),
        "recall": recall,
        "precision": precision,
        "top1_retained": top1,
        "complete_set_preserved": complete_set,
        "set_membership": "preserved" if complete_set else "not_preserved",
        "ambiguous_matching": ambiguous,
        "within_arm_ambiguous_candidate_site": within_arm_ambiguity,
        "optimal_pair_set_count": matched.optimal_pair_set_count,
        "match_objective": _objective(matched.objective),
        "matched_pairs_zero_based": [list(pair) for pair in pairs],
        "strict_row_diagnostic": "match" if strict_equal else "mismatch",
        "strict_row_equal": strict_equal,
        "classifications": classifications,
        "double_empty": denominator.double_empty,
        "informative_for_recovery": denominator.informative_for_recovery,
        "binary_gate_denominator_eligible": denominator.binary_gate_denominator_eligible,
        "binary_success": denominator.binary_success,
        "rank_diagnostic": ranks,
    }
    return result, details


__all__ = [name for name in globals() if not name.startswith("_")]
