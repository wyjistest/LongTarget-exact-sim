#!/usr/bin/env python3
"""Exact primitives for biological_topk_candidate_site_v1.

This module contains only deterministic contract logic. It does not select a
fresh panel, invoke Fasim, or read evaluation predictions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence


DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z", re.ASCII)
INPUT_IDENTITY_FIELDS = (
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
)
RANKING_MODES = ("score", "stability", "nt")
CURRENT_REACHABLE_DIRECTIONS = frozenset({"R"})
SUPPORTED_STRANDS = frozenset({"ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus"})


class ContractError(ValueError):
    """Raised when data cannot be represented under the frozen contract."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def parse_decimal(raw: str) -> Decimal:
    if not isinstance(raw, str) or DECIMAL_PATTERN.fullmatch(raw) is None:
        raise ContractError(f"invalid exact decimal: {raw!r}")
    value = Decimal(raw)
    if not value.is_finite():
        raise ContractError("non-finite decimal")
    return value


def canonical_decimal(value: Decimal | str) -> str:
    decimal = parse_decimal(value) if isinstance(value, str) else value
    if not isinstance(decimal, Decimal) or not decimal.is_finite():
        raise ContractError("canonical decimal requires a finite Decimal")
    if decimal == 0:
        return "0"
    rendered = format(decimal, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def exact_integral(raw: str) -> bool:
    value = parse_decimal(raw)
    return value == value.to_integral_value()


def normalize_ungapped(raw: str, alphabet: frozenset[str] = frozenset("ACGTN")) -> str:
    if not isinstance(raw, str):
        raise ContractError("sequence field must be text")
    external = raw.strip(" \t\r\n")
    normalized_chars: list[str] = []
    for character in external:
        if character == "-":
            continue
        code = ord(character)
        if 97 <= code <= 122:
            character = chr(code - 32)
        if character not in alphabet:
            raise ContractError(f"unsupported sequence character: {character!r}")
        normalized_chars.append(character)
    return "".join(normalized_chars)


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


@dataclass
class LegacyRow:
    raw_query_start: int
    raw_query_end: int
    nt: int
    source_index: int
    middle: int = 0
    motif: int = 0
    center: int = 0
    neartriplex: int = 0


def legacy_query_midpoint(raw_query_start: int, raw_query_end: int) -> int:
    if raw_query_start <= 0 or raw_query_end <= 0:
        raise ContractError("legacy query coordinates must be positive")
    return (raw_query_start + raw_query_end) // 2


def cluster_legacy(
    rows: Sequence[LegacyRow],
    *,
    distance: int = 15,
    minimum_nt_bp: int = 50,
) -> list[LegacyRow]:
    """Reproduce Fasim's cluster_triplex map/operator[] behavior exactly.

    Input order is significant, as it is in the C++ vector. The rescan uses a
    dynamic map size and strict greater-than tie handling.
    """
    if distance <= 0 or minimum_nt_bp < 0:
        raise ContractError("invalid clustering parameters")
    clustered = [replace(row) for row in rows]
    axis: dict[int, list[int]] = {}
    max_near = 0
    max_pos = 0
    found = False

    def node(position: int) -> list[int]:
        return axis.setdefault(position, [0, 0])

    for row in clustered:
        if row.nt > minimum_nt_bp:
            middle = legacy_query_midpoint(row.raw_query_start, row.raw_query_end)
            if middle < distance:
                raise ContractError("legacy size_t axis would underflow")
            row.middle = middle
            row.motif = 0
            node(middle)[0] += 1
            for offset in range(-distance, distance + 1):
                current = node(middle + offset)
                if offset > 0:
                    current[1] += distance - offset
                elif offset < 0:
                    current[1] += distance + offset
                if current[1] > max_near:
                    max_near = current[1]
                    max_pos = middle + offset
                    found = True
            row.neartriplex = node(middle)[1]

    class_index = 1
    while found:
        for position in range(max_pos - distance, max_pos + distance + 1):
            for row in clustered:
                if row.middle == position and row.motif == 0:
                    row.motif = class_index
                    row.center = max_pos
            axis.pop(position, None)

        max_near = 0
        found = False
        scan_position = 0
        maximum_existing = max(axis, default=0)
        guard = maximum_existing + len(axis) + distance + 2
        while scan_position < len(axis):
            current = node(scan_position)
            if current[1] > max_near:
                max_near = current[1]
                max_pos = scan_position
                found = True
            scan_position += 1
            if scan_position > guard:
                raise ContractError("legacy dynamic map rescan did not terminate")
        class_index += 1
    return clustered


def rank_values(row: Mapping[str, str], mode: str) -> tuple[Decimal | int, ...]:
    score = parse_decimal(row["Score"])
    stability = parse_decimal(row["MeanStability"])
    nt = int(row["Nt(bp)"])
    if str(nt) != row["Nt(bp)"] or nt < 0:
        raise ContractError("Nt(bp) must be a canonical nonnegative integer")
    if mode == "score":
        return score, nt, stability
    if mode == "stability":
        return stability, nt, score
    if mode == "nt":
        return nt, score, stability
    raise ContractError(f"unknown ranking mode: {mode}")


def deterministic_rank_key(
    row: Mapping[str, str], mode: str, full_row_columns: Sequence[str]
) -> tuple[Any, ...]:
    return (*rank_values(row, mode), tuple(row[column] for column in full_row_columns))


_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def strand_transform(sequence: str, strand: str) -> str:
    if set(sequence) - set("ACGTN"):
        raise ContractError("target sequence contains unsupported bases")
    if strand == "ParaPlus":
        return sequence
    if strand == "ParaMinus":
        return sequence.translate(_COMPLEMENT)[::-1]
    if strand == "AntiMinus":
        return sequence.translate(_COMPLEMENT)
    if strand == "AntiPlus":
        return sequence[::-1]
    raise ContractError(f"unsupported Strand: {strand!r}")


@dataclass(frozen=True)
class CanonicalCoordinates:
    query_start0: int
    query_end0: int
    target_start0: int
    target_end0: int
    genome_start0: int
    genome_end0: int


def canonicalize_coordinates(
    *,
    raw_query_start: int,
    raw_query_end: int,
    raw_target_start: int,
    raw_target_end: int,
    strand: str,
    direction: str,
    target_length: int,
    target_region_start0: int,
) -> CanonicalCoordinates:
    if strand not in SUPPORTED_STRANDS:
        raise ContractError(f"unsupported Strand: {strand!r}")
    if direction not in CURRENT_REACHABLE_DIRECTIONS:
        raise ContractError(f"Direction {direction!r} is unreachable in the current fast path")
    if raw_query_start <= 0 or raw_query_end < raw_query_start:
        raise ContractError("invalid 1-based inclusive query coordinates")
    query_start0 = raw_query_start - 1
    query_end0 = raw_query_end

    if strand in {"ParaPlus", "AntiMinus"}:
        target_start0 = raw_target_start - 1
        target_end0 = raw_target_end
    else:
        target_start0 = raw_target_start
        target_end0 = raw_target_end + 1
    if not 0 <= target_start0 < target_end0 <= target_length:
        raise ContractError("normalized target interval is outside the target FASTA")
    if target_region_start0 < 0:
        raise ContractError("target region start must be nonnegative")
    return CanonicalCoordinates(
        query_start0=query_start0,
        query_end0=query_end0,
        target_start0=target_start0,
        target_end0=target_end0,
        genome_start0=target_region_start0 + target_start0,
        genome_end0=target_region_start0 + target_end0,
    )


def reconstruct_tts(target_sequence: str, coordinates: CanonicalCoordinates, strand: str) -> str:
    forward = target_sequence[coordinates.target_start0 : coordinates.target_end0]
    return strand_transform(forward, strand)


def input_identity_mismatches(
    authority: Mapping[str, Any], candidate: Mapping[str, Any]
) -> tuple[str, ...]:
    missing = [field for field in INPUT_IDENTITY_FIELDS if field not in authority or field not in candidate]
    if missing:
        raise ContractError(f"missing input identity fields: {missing}")
    return tuple(field for field in INPUT_IDENTITY_FIELDS if authority[field] != candidate[field])


def input_identity_equal(authority: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return not input_identity_mismatches(authority, candidate)


def input_pair_digest(identity: Mapping[str, Any]) -> str:
    fields = (
        "schema_version",
        "query_ordinal_namespace",
        "query_source_ordinal",
        "query_sequence_sha256",
        "query_extracted_interval",
        "target_ordinal_namespace",
        "target_source_ordinal",
        "target_sequence_sha256",
        "target_extracted_interval",
        "assembly",
        "target_coordinate_namespace",
        "query_extraction_recipe_id",
        "target_extraction_recipe_id",
        "parameter_bundle_sha256",
    )
    missing = [field for field in fields if field not in identity]
    if missing:
        raise ContractError(f"missing pair digest fields: {missing}")
    return canonical_json_sha256({field: identity[field] for field in fields})


def reciprocal_overlap(left: tuple[int, int], right: tuple[int, int]) -> Fraction:
    left_start, left_end = left
    right_start, right_end = right
    if not 0 <= left_start < left_end or not 0 <= right_start < right_end:
        raise ContractError("intervals must be nonempty 0-based half-open intervals")
    intersection = max(0, min(left_end, right_end) - max(left_start, right_start))
    return Fraction(intersection, max(left_end - left_start, right_end - right_start))


@dataclass(frozen=True)
class CandidateSite:
    input_pair_digest: str
    chromosome_or_target_id: str
    direction: str
    strand: str
    rule: int
    query_interval: tuple[int, int]
    cluster_interval: tuple[int, int]
    target_interval: tuple[int, int]
    cluster_center: int
    ungapped_tfo_sha256: str
    ungapped_tts_sha256: str
    rank: int


@dataclass(frozen=True)
class EdgeQuality:
    target_overlap: Fraction
    query_rep_overlap: Fraction
    query_cluster_overlap: Fraction
    ungapped_tfo_equal: int
    ungapped_tts_equal: int
    target_endpoint_l1: int
    query_endpoint_l1: int
    cluster_center_distance: int


@dataclass(frozen=True)
class MatchResult:
    pairs: tuple[tuple[int, int], ...]
    objective: tuple[Any, ...]
    ambiguous: bool
    optimal_pair_set_count: int


def _endpoint_l1(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def eligible_edge(
    authority: CandidateSite,
    candidate: CandidateSite,
    threshold: Fraction = Fraction(9, 10),
) -> EdgeQuality | None:
    if not 0 < threshold <= 1:
        raise ContractError("overlap threshold must be in (0, 1]")
    exact_fields = (
        "input_pair_digest",
        "chromosome_or_target_id",
        "direction",
        "strand",
        "rule",
    )
    if any(getattr(authority, field) != getattr(candidate, field) for field in exact_fields):
        return None
    target = reciprocal_overlap(authority.target_interval, candidate.target_interval)
    query = reciprocal_overlap(authority.query_interval, candidate.query_interval)
    cluster = reciprocal_overlap(authority.cluster_interval, candidate.cluster_interval)
    if target < threshold or query < threshold or cluster < threshold:
        return None
    return EdgeQuality(
        target_overlap=target,
        query_rep_overlap=query,
        query_cluster_overlap=cluster,
        ungapped_tfo_equal=int(authority.ungapped_tfo_sha256 == candidate.ungapped_tfo_sha256),
        ungapped_tts_equal=int(authority.ungapped_tts_sha256 == candidate.ungapped_tts_sha256),
        target_endpoint_l1=_endpoint_l1(authority.target_interval, candidate.target_interval),
        query_endpoint_l1=_endpoint_l1(authority.query_interval, candidate.query_interval),
        cluster_center_distance=abs(authority.cluster_center - candidate.cluster_center),
    )


def _matching_objective(qualities: Iterable[EdgeQuality]) -> tuple[Any, ...]:
    edges = tuple(qualities)
    return (
        len(edges),
        sum((edge.target_overlap for edge in edges), Fraction()),
        sum((edge.query_rep_overlap for edge in edges), Fraction()),
        sum((edge.query_cluster_overlap for edge in edges), Fraction()),
        sum(edge.ungapped_tfo_equal for edge in edges),
        sum(edge.ungapped_tts_equal for edge in edges),
        -sum(edge.target_endpoint_l1 for edge in edges),
        -sum(edge.query_endpoint_l1 for edge in edges),
        -sum(edge.cluster_center_distance for edge in edges),
    )


def match_candidate_sites(
    authority: Sequence[CandidateSite],
    candidate: Sequence[CandidateSite],
    threshold: Fraction = Fraction(9, 10),
) -> MatchResult:
    if len(authority) > 5 or len(candidate) > 5:
        raise ContractError("v1 matcher is bounded at K=5")
    qualities: dict[tuple[int, int], EdgeQuality] = {}
    for left_index, left in enumerate(authority):
        for right_index, right in enumerate(candidate):
            quality = eligible_edge(left, right, threshold)
            if quality is not None:
                qualities[(left_index, right_index)] = quality

    pair_sets: set[tuple[tuple[int, int], ...]] = set()

    def enumerate_sets(left_index: int, used_right: frozenset[int], pairs: tuple[tuple[int, int], ...]) -> None:
        if left_index == len(authority):
            pair_sets.add(pairs)
            return
        enumerate_sets(left_index + 1, used_right, pairs)
        for right_index in range(len(candidate)):
            pair = (left_index, right_index)
            if right_index not in used_right and pair in qualities:
                enumerate_sets(
                    left_index + 1,
                    used_right | {right_index},
                    (*pairs, pair),
                )

    enumerate_sets(0, frozenset(), ())
    evaluated = {
        pairs: _matching_objective(qualities[pair] for pair in pairs)
        for pairs in pair_sets
    }
    best = max(evaluated.values())
    optimal = tuple(sorted(pairs for pairs, objective in evaluated.items() if objective == best))
    return MatchResult(
        pairs=optimal[0],
        objective=best,
        ambiguous=len(optimal) > 1,
        optimal_pair_set_count=len(optimal),
    )


@dataclass(frozen=True)
class DenominatorResult:
    double_empty: bool
    informative_for_recovery: bool | None
    binary_gate_denominator_eligible: bool
    binary_success: bool | None


def classify_denominator(
    *,
    authority_technical_success: bool,
    candidate_technical_success: bool,
    input_identity_pass: bool,
    authority_output_valid: bool,
    candidate_output_valid: bool,
    authority_candidate_count: int | None,
    candidate_candidate_count: int | None,
    complete_set_success: bool = False,
) -> DenominatorResult:
    technical_valid = all(
        (
            authority_technical_success,
            candidate_technical_success,
            input_identity_pass,
            authority_output_valid,
            candidate_output_valid,
        )
    )
    if technical_valid and authority_candidate_count == 0 and candidate_candidate_count == 0:
        return DenominatorResult(True, False, False, None)
    informative: bool | None
    if authority_candidate_count is None or not authority_technical_success or not authority_output_valid:
        informative = None
    else:
        informative = authority_candidate_count > 0
    success = bool(
        technical_valid
        and authority_candidate_count is not None
        and authority_candidate_count > 0
        and complete_set_success
    )
    return DenominatorResult(False, informative, True, success)


def binomial_tail(n: int, minimum_successes: int, probability: Decimal | str) -> Decimal:
    p = parse_decimal(probability) if isinstance(probability, str) else probability
    if n < 0 or not 0 <= minimum_successes <= n + 1 or not 0 <= p <= 1:
        raise ContractError("invalid binomial arguments")
    if minimum_successes <= 0:
        return Decimal(1)
    if minimum_successes > n:
        return Decimal(0)
    with localcontext() as context:
        context.prec = 80
        q = Decimal(1) - p
        if p == 0:
            return Decimal(0)
        if p == 1:
            return Decimal(1)
        successes = minimum_successes
        term = Decimal(math.comb(n, successes)) * (p ** successes) * (q ** (n - successes))
        total = term
        while successes < n:
            term *= (
                Decimal(n - successes)
                * p
                / (Decimal(successes + 1) * q)
            )
            total += term
            successes += 1
        return +total


def clopper_pearson_lower(successes: int, n: int, alpha: Decimal | str = "0.05") -> Decimal:
    alpha_decimal = parse_decimal(alpha) if isinstance(alpha, str) else alpha
    if n <= 0 or not 0 <= successes <= n or not 0 < alpha_decimal < 1:
        raise ContractError("invalid Clopper-Pearson arguments")
    if successes == 0:
        return Decimal(0)
    with localcontext() as context:
        context.prec = 80
        low = Decimal(0)
        high = Decimal(1)
        for _ in range(200):
            midpoint = (low + high) / 2
            if binomial_tail(n, successes, midpoint) < alpha_decimal:
                low = midpoint
            else:
                high = midpoint
        return +(low + high) / 2


def minimum_passing_successes(
    n: int,
    *,
    lower_bound_threshold: Decimal | str = "0.95",
    alpha: Decimal | str = "0.05",
) -> int | None:
    threshold = (
        parse_decimal(lower_bound_threshold)
        if isinstance(lower_bound_threshold, str)
        else lower_bound_threshold
    )
    if clopper_pearson_lower(n, n, alpha) < threshold:
        return None
    for successes in range(n - 1, -1, -1):
        if clopper_pearson_lower(successes, n, alpha) < threshold:
            return successes + 1
    return 0


def exact_gate_power(
    n: int,
    *,
    p_alt: Decimal | str = "0.99",
    lower_bound_threshold: Decimal | str = "0.95",
    alpha: Decimal | str = "0.05",
) -> tuple[int | None, Decimal]:
    minimum = minimum_passing_successes(
        n,
        lower_bound_threshold=lower_bound_threshold,
        alpha=alpha,
    )
    if minimum is None:
        return None, Decimal(0)
    return minimum, binomial_tail(n, minimum, p_alt)


def required_binary_n(
    *,
    denominator_floor: int = 60,
    minimum_power: Decimal | str = "0.80",
    p_alt: Decimal | str = "0.99",
    lower_bound_threshold: Decimal | str = "0.95",
    alpha: Decimal | str = "0.05",
) -> tuple[int, int, Decimal]:
    power_target = parse_decimal(minimum_power) if isinstance(minimum_power, str) else minimum_power
    for n in range(denominator_floor, 10000):
        minimum, power = exact_gate_power(
            n,
            p_alt=p_alt,
            lower_bound_threshold=lower_bound_threshold,
            alpha=alpha,
        )
        if minimum is not None and power >= power_target:
            return n, minimum, power
    raise ContractError("binary sample-size search exceeded bound")


def required_panel_n(
    n_binary_required: int,
    *,
    p_eligible: Decimal | str = "0.75",
    minimum_probability: Decimal | str = "0.95",
) -> tuple[int, Decimal]:
    target = (
        parse_decimal(minimum_probability)
        if isinstance(minimum_probability, str)
        else minimum_probability
    )
    for panel_n in range(n_binary_required, 10000):
        probability = binomial_tail(panel_n, n_binary_required, p_eligible)
        if probability >= target:
            return panel_n, probability
    raise ContractError("panel-size search exceeded bound")


def finite_rbo(
    left: Sequence[Any],
    right: Sequence[Any],
    *,
    depth: int = 5,
    persistence: Fraction = Fraction(9, 10),
) -> Fraction:
    """Finite depth RBO_EXT with missing positions treated as absent.

    Empty/empty is zero because clean double-empty is non-informative. A
    one-sided empty comparison is also zero.
    """
    if depth <= 0 or not 0 < persistence < 1:
        raise ContractError("invalid finite RBO parameters")
    if not left or not right:
        return Fraction(0)
    left_seen: set[Any] = set()
    right_seen: set[Any] = set()
    weighted = Fraction(0)
    agreement_at_depth = Fraction(0)
    for current_depth in range(1, depth + 1):
        if current_depth <= len(left):
            left_seen.add(left[current_depth - 1])
        if current_depth <= len(right):
            right_seen.add(right[current_depth - 1])
        agreement = Fraction(len(left_seen & right_seen), current_depth)
        agreement_at_depth = agreement
        weighted += (persistence ** (current_depth - 1)) * agreement
    return (1 - persistence) * weighted + (persistence ** depth) * agreement_at_depth


__all__ = [name for name in globals() if not name.startswith("_")]
