#!/usr/bin/env python3
"""Exact legacy clustering and within-arm Top-K site construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:
    from . import canonicalize_rows, contract
except ImportError:  # pragma: no cover - direct script/import fallback
    import canonicalize_rows  # type: ignore[no-redef]
    import contract  # type: ignore[no-redef]


class ClusteringError(contract.ContractError):
    """Raised when canonical rows cannot form deterministic candidate sites."""


@dataclass(frozen=True, slots=True)
class LegacyCluster:
    local_index: int
    center: int
    members: tuple[canonicalize_rows.CanonicalRow, ...]
    member_midpoint_min: int
    member_midpoint_max: int
    query_span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class CandidateSiteRecord:
    workload_id: str
    arm: str
    ranking_mode: str
    rank: int
    query_ordinal_namespace: str
    query_source_ordinal: str | int
    query_sequence_sha256: str
    target_ordinal_namespace: str
    target_source_ordinal: str | int
    target_sequence_sha256: str
    assembly: str
    target_coordinate_namespace: str
    input_pair_digest: str
    legacy_cluster_local_index: int
    legacy_cluster_center: int
    legacy_cluster_member_count: int
    legacy_cluster_query_midpoint_min: int
    legacy_cluster_query_midpoint_max: int
    cluster_query_span_start0: int
    cluster_query_span_end0: int
    representative_query_start0: int
    representative_query_end0: int
    representative_target_start0: int
    representative_target_end0: int
    representative_genome_start0: int
    representative_genome_end0: int
    chromosome_or_target_id: str
    direction: str
    strand: str
    rule: int
    score_decimal_string: str
    score_integer: int
    score_representation: str
    nt_integer: int
    mean_stability_decimal: str
    mean_identity_decimal: str
    ungapped_tfo_sha256: str
    ungapped_tts_sha256: str
    technical_valid: bool
    strict_row_digest_diagnostic: str
    candidate_site_identity_digest: str
    within_arm_ambiguous_candidate_site: bool
    raw_row_key: tuple[str, ...]

    def matching_site(self) -> contract.CandidateSite:
        return contract.CandidateSite(
            input_pair_digest=self.input_pair_digest,
            chromosome_or_target_id=self.chromosome_or_target_id,
            direction=self.direction,
            strand=self.strand,
            rule=self.rule,
            query_interval=(
                self.representative_query_start0,
                self.representative_query_end0,
            ),
            cluster_interval=(
                self.cluster_query_span_start0,
                self.cluster_query_span_end0,
            ),
            target_interval=(
                self.representative_target_start0,
                self.representative_target_end0,
            ),
            cluster_center=self.legacy_cluster_center,
            ungapped_tfo_sha256=self.ungapped_tfo_sha256,
            ungapped_tts_sha256=self.ungapped_tts_sha256,
            rank=self.rank,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
            if field != "raw_row_key"
        }


def _rank_values(
    row: canonicalize_rows.CanonicalRow,
    mode: str,
) -> tuple[Any, ...]:
    if mode == "score":
        return row.score, row.nt, row.mean_stability
    if mode == "stability":
        return row.mean_stability, row.nt, row.score
    if mode == "nt":
        return row.nt, row.score, row.mean_stability
    raise ClusteringError(f"unknown ranking mode: {mode}")


def _rank_key(
    row: canonicalize_rows.CanonicalRow,
    mode: str,
) -> tuple[Any, ...]:
    return (*_rank_values(row, mode), row.raw_row_key)


def _cluster_rows(
    rows: Sequence[canonicalize_rows.CanonicalRow],
    *,
    distance: int,
    minimum_nt_bp: int,
) -> tuple[LegacyCluster, ...]:
    midpoint_assignment = legacy_midpoint_assignments(
        [(row.legacy_midpoint, row.nt) for row in rows],
        distance=distance,
        minimum_nt_bp=minimum_nt_bp,
    )
    grouped: dict[int, list[canonicalize_rows.CanonicalRow]] = {}
    centers: dict[int, int] = {}
    for row in rows:
        assignment = midpoint_assignment.get(row.legacy_midpoint) if row.nt > minimum_nt_bp else None
        if assignment is None:
            continue
        motif, center = assignment
        grouped.setdefault(motif, []).append(row)
        centers[motif] = center
    clusters: list[LegacyCluster] = []
    for local_index in sorted(grouped):
        members = tuple(grouped[local_index])
        midpoints = tuple(row.legacy_midpoint for row in members)
        clusters.append(
            LegacyCluster(
                local_index=local_index,
                center=centers[local_index],
                members=members,
                member_midpoint_min=min(midpoints),
                member_midpoint_max=max(midpoints),
                query_span=(
                    min(row.coordinates.query_start0 for row in members),
                    max(row.coordinates.query_end0 for row in members),
                ),
            )
        )
    return tuple(clusters)


def legacy_midpoint_assignments(
    observations: Sequence[tuple[int, int]],
    *,
    distance: int = 15,
    minimum_nt_bp: int = 50,
) -> Mapping[int, tuple[int, int]]:
    """Return midpoint -> (motif, center) with exact legacy update order.

    Rows sharing a midpoint always receive the same motif. Keeping only this
    mapping removes per-row clone overhead without changing any assignment.
    """
    if distance <= 0 or minimum_nt_bp < 0:
        raise ClusteringError("invalid clustering parameters")
    axis: dict[int, list[int]] = {}
    eligible_midpoints: set[int] = set()
    max_near = 0
    max_pos = 0
    found = False

    def node(position: int) -> list[int]:
        return axis.setdefault(position, [0, 0])

    # This is the frozen legacy update order, aggregated only after each row's
    # effects have been applied. Strict-maximum tie behavior is unchanged.
    for middle, nt in observations:
        if nt <= minimum_nt_bp:
            continue
        if middle < distance:
            raise ClusteringError("legacy size_t axis would underflow")
        eligible_midpoints.add(middle)
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

    midpoint_assignment: dict[int, tuple[int, int]] = {}
    local_index = 1
    while found:
        for position in range(max_pos - distance, max_pos + distance + 1):
            if position in eligible_midpoints and position not in midpoint_assignment:
                midpoint_assignment[position] = (local_index, max_pos)
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
                raise ClusteringError("legacy dynamic map rescan did not terminate")
        local_index += 1

    return midpoint_assignment


def _row_biological_key(
    row: canonicalize_rows.CanonicalRow,
    cluster: LegacyCluster,
    input_pair_digest: str,
) -> tuple[Any, ...]:
    coordinates = row.coordinates
    return (
        input_pair_digest,
        row.chromosome_or_target_id,
        row.direction,
        row.strand,
        row.rule,
        (coordinates.query_start0, coordinates.query_end0),
        cluster.query_span,
        (coordinates.target_start0, coordinates.target_end0),
        cluster.center,
        row.ungapped_tfo_sha256,
        row.ungapped_tts_sha256,
    )


def _site_identity_digest(
    row: canonicalize_rows.CanonicalRow,
    cluster: LegacyCluster,
    input_pair_digest: str,
) -> str:
    return contract.canonical_json_sha256(
        list(_row_biological_key(row, cluster, input_pair_digest))
    )


def _representative_ambiguous(
    cluster: LegacyCluster,
    representative: canonicalize_rows.CanonicalRow,
    mode: str,
    input_pair_digest: str,
) -> bool:
    numeric = _rank_values(representative, mode)
    tied = [row for row in cluster.members if _rank_values(row, mode) == numeric]
    by_biological_key: dict[tuple[Any, ...], set[tuple[str, ...]]] = {}
    for row in tied:
        key = _row_biological_key(row, cluster, input_pair_digest)
        by_biological_key.setdefault(key, set()).add(row.raw_row_key)
    representative_key = _row_biological_key(representative, cluster, input_pair_digest)
    return len(by_biological_key.get(representative_key, set())) > 1


def _record(
    receipt: canonicalize_rows.InputReceipt,
    cluster: LegacyCluster,
    representative: canonicalize_rows.CanonicalRow,
    mode: str,
    rank: int,
) -> CandidateSiteRecord:
    identity = receipt.input_identity
    coordinates = representative.coordinates
    pair_digest = str(identity["input_pair_digest"])
    return CandidateSiteRecord(
        workload_id=receipt.workload_id,
        arm=receipt.arm,
        ranking_mode=mode,
        rank=rank,
        query_ordinal_namespace=str(identity["query_ordinal_namespace"]),
        query_source_ordinal=identity["query_source_ordinal"],
        query_sequence_sha256=str(identity["query_sequence_sha256"]),
        target_ordinal_namespace=str(identity["target_ordinal_namespace"]),
        target_source_ordinal=identity["target_source_ordinal"],
        target_sequence_sha256=str(identity["target_sequence_sha256"]),
        assembly=str(identity["assembly"]),
        target_coordinate_namespace=str(identity["target_coordinate_namespace"]),
        input_pair_digest=pair_digest,
        legacy_cluster_local_index=cluster.local_index,
        legacy_cluster_center=cluster.center,
        legacy_cluster_member_count=len(cluster.members),
        legacy_cluster_query_midpoint_min=cluster.member_midpoint_min,
        legacy_cluster_query_midpoint_max=cluster.member_midpoint_max,
        cluster_query_span_start0=cluster.query_span[0],
        cluster_query_span_end0=cluster.query_span[1],
        representative_query_start0=coordinates.query_start0,
        representative_query_end0=coordinates.query_end0,
        representative_target_start0=coordinates.target_start0,
        representative_target_end0=coordinates.target_end0,
        representative_genome_start0=coordinates.genome_start0,
        representative_genome_end0=coordinates.genome_end0,
        chromosome_or_target_id=representative.chromosome_or_target_id,
        direction=representative.direction,
        strand=representative.strand,
        rule=representative.rule,
        score_decimal_string=representative.score_decimal_string,
        score_integer=representative.score_integer,
        score_representation="integral_exact",
        nt_integer=representative.nt,
        mean_stability_decimal=representative.mean_stability_decimal,
        mean_identity_decimal=representative.mean_identity_decimal,
        ungapped_tfo_sha256=representative.ungapped_tfo_sha256,
        ungapped_tts_sha256=representative.ungapped_tts_sha256,
        technical_valid=representative.technical_valid,
        strict_row_digest_diagnostic=representative.strict_row_digest_diagnostic,
        candidate_site_identity_digest=_site_identity_digest(
            representative,
            cluster,
            pair_digest,
        ),
        within_arm_ambiguous_candidate_site=_representative_ambiguous(
            cluster,
            representative,
            mode,
            pair_digest,
        ),
        raw_row_key=representative.raw_row_key,
    )


def ranked_candidate_sites(
    rows: Sequence[canonicalize_rows.CanonicalRow],
    receipt: canonicalize_rows.InputReceipt,
    *,
    mode: str,
    k: int = 5,
    distance: int = 15,
    minimum_nt_bp: int = 50,
) -> tuple[CandidateSiteRecord, ...]:
    if mode not in contract.RANKING_MODES:
        raise ClusteringError(f"unknown ranking mode: {mode}")
    if not 0 < k <= 5:
        raise ClusteringError("v1 requires 1 <= K <= 5")
    clusters = _cluster_rows(rows, distance=distance, minimum_nt_bp=minimum_nt_bp)
    return _rank_clusters(clusters, receipt, mode=mode, k=k)


def _rank_clusters(
    clusters: Sequence[LegacyCluster],
    receipt: canonicalize_rows.InputReceipt,
    *,
    mode: str,
    k: int,
) -> tuple[CandidateSiteRecord, ...]:
    representatives = [
        (
            cluster,
            max(
                cluster.members,
                key=lambda row: _rank_key(row, mode),
            ),
        )
        for cluster in clusters
    ]
    representatives.sort(
        key=lambda item: _rank_key(item[1], mode),
        reverse=True,
    )
    return tuple(
        _record(receipt, cluster, row, mode, rank)
        for rank, (cluster, row) in enumerate(representatives[:k], 1)
    )


def all_rankings(
    rows: Sequence[canonicalize_rows.CanonicalRow],
    receipt: canonicalize_rows.InputReceipt,
    *,
    k: int = 5,
    distance: int = 15,
    minimum_nt_bp: int = 50,
) -> Mapping[str, tuple[CandidateSiteRecord, ...]]:
    if not 0 < k <= 5:
        raise ClusteringError("v1 requires 1 <= K <= 5")
    clusters = _cluster_rows(rows, distance=distance, minimum_nt_bp=minimum_nt_bp)
    return {
        mode: _rank_clusters(clusters, receipt, mode=mode, k=k)
        for mode in contract.RANKING_MODES
    }


__all__ = [name for name in globals() if not name.startswith("_")]
