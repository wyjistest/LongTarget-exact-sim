#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from compare_fasim_lite_offline_cluster_topk import TriplexRow, _cluster_triplex, _strand_flags
from fasim_tfo_archive import TFOSORTED_COLUMNS


RANKING_MODES = ("score", "stability", "nt")


@dataclass(frozen=True)
class ContractSide:
    rows: list[dict[str, str]]
    row_keys: set[tuple[str, ...]]
    raw_top: dict[str, tuple[tuple[str, ...], ...]]
    clustered_top: dict[str, tuple[tuple[str, ...], ...]]
    tie_groups: set[tuple[str, tuple[tuple[str, ...], ...]]]
    representative_conflict_clusters: int


def _full_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[column] for column in TFOSORTED_COLUMNS)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != list(TFOSORTED_COLUMNS):
            raise ValueError(f"unsupported TFOsorted columns in {path}: {reader.fieldnames or []}")
        rows = []
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"malformed row {row_number} in {path}")
            rows.append(dict(row))
    return rows


def _number(row: dict[str, str], column: str) -> float:
    return float(row[column])


def _rank_values(row: dict[str, str], mode: str) -> tuple[float, float, float]:
    if mode == "score":
        return (_number(row, "Score"), _number(row, "Nt(bp)"), _number(row, "MeanStability"))
    if mode == "stability":
        return (_number(row, "MeanStability"), _number(row, "Nt(bp)"), _number(row, "Score"))
    if mode == "nt":
        return (_number(row, "Nt(bp)"), _number(row, "Score"), _number(row, "MeanStability"))
    raise ValueError(f"unknown ranking mode: {mode}")


def _rank_key(row: dict[str, str], mode: str) -> tuple[object, ...]:
    return (*_rank_values(row, mode), _full_key(row))


def _triplex_rows(rows: Iterable[dict[str, str]]) -> list[TriplexRow]:
    stable_rows = sorted(rows, key=_full_key)
    triplex: list[TriplexRow] = []
    for index, row in enumerate(stable_rows):
        reverse, strand = _strand_flags(row["Strand"])
        triplex.append(
            TriplexRow(
                row=row,
                index=index,
                stari=int(row["QueryStart"]),
                endi=int(row["QueryEnd"]),
                starj=int(row["StartInSeq"]),
                endj=int(row["EndInSeq"]),
                reverse=reverse,
                strand=strand,
                rule=int(row["Rule"]),
                score=float(row["Score"]),
                nt=int(row["Nt(bp)"]),
                identity=float(row["MeanIdentity(%)"]),
                tri_score=float(row["MeanStability"]),
            )
        )
    return triplex


def _analyze(path: Path, k: int, cluster_distance: int, cluster_length: int) -> ContractSide:
    input_rows = _read_rows(path)
    unique_by_key = {_full_key(row): row for row in input_rows}
    rows = [unique_by_key[key] for key in sorted(unique_by_key)]
    raw_top = {
        mode: tuple(
            _full_key(row)
            for row in sorted(rows, key=lambda row: _rank_key(row, mode), reverse=True)[:k]
        )
        for mode in RANKING_MODES
    }

    triplex = _triplex_rows(rows)
    _cluster_triplex(triplex, dd=cluster_distance, length=cluster_length)
    clusters: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in triplex:
        if row.motif != 0:
            clusters[row.motif].append(row.row)

    representatives: dict[str, dict[int, dict[str, str]]] = {
        mode: {
            cluster_id: max(cluster_rows, key=lambda row: _rank_key(row, mode))
            for cluster_id, cluster_rows in clusters.items()
        }
        for mode in RANKING_MODES
    }
    clustered_top = {
        mode: tuple(
            _full_key(row)
            for row in sorted(
                representatives[mode].values(),
                key=lambda row: _rank_key(row, mode),
                reverse=True,
            )[:k]
        )
        for mode in RANKING_MODES
    }

    tie_groups: set[tuple[str, tuple[tuple[str, ...], ...]]] = set()
    for mode in RANKING_MODES:
        tied: dict[tuple[float, float, float], list[tuple[str, ...]]] = defaultdict(list)
        for row in representatives[mode].values():
            tied[_rank_values(row, mode)].append(_full_key(row))
        for keys in tied.values():
            if len(keys) > 1:
                tie_groups.add((mode, tuple(sorted(keys))))

    representative_conflicts = 0
    for cluster_id in clusters:
        keys = {
            _full_key(representatives[mode][cluster_id])
            for mode in RANKING_MODES
        }
        if len(keys) > 1:
            representative_conflicts += 1

    return ContractSide(
        rows=input_rows,
        row_keys=set(unique_by_key),
        raw_top=raw_top,
        clustered_top=clustered_top,
        tie_groups=tie_groups,
        representative_conflict_clusters=representative_conflicts,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare full and clustered tri-ranking contracts for segmented Fasim output."
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--cluster-distance", type=int, default=15)
    parser.add_argument("--cluster-length", type=int, default=50)
    args = parser.parse_args()
    if args.k <= 0:
        parser.error("--k must be positive")

    baseline = _analyze(args.baseline, args.k, args.cluster_distance, args.cluster_length)
    candidate = _analyze(args.candidate, args.k, args.cluster_distance, args.cluster_length)
    missing = baseline.row_keys - candidate.row_keys
    extra = candidate.row_keys - baseline.row_keys

    print(f"baseline={args.baseline}")
    print(f"candidate={args.candidate}")
    print(f"baseline_rows={len(baseline.rows)}")
    print(f"candidate_rows={len(candidate.rows)}")
    print(f"baseline_unique_rows={len(baseline.row_keys)}")
    print(f"candidate_unique_rows={len(candidate.row_keys)}")
    print(f"full_missing_rows={len(missing)}")
    print(f"full_extra_rows={len(extra)}")

    raw_equal: dict[str, bool] = {}
    clustered_equal: dict[str, bool] = {}
    for mode in RANKING_MODES:
        raw_equal[mode] = baseline.raw_top[mode] == candidate.raw_top[mode]
        clustered_equal[mode] = baseline.clustered_top[mode] == candidate.clustered_top[mode]
        print(f"raw_{mode}_top{args.k}_equal={int(raw_equal[mode])}")
        print(f"clustered_{mode}_top{args.k}_equal={int(clustered_equal[mode])}")
    all_three = all(clustered_equal.values())
    boundary_ties_equal = baseline.tie_groups == candidate.tie_groups
    print(f"all_three_top5_equal={int(all_three)}")
    print(f"boundary_ties_equal={int(boundary_ties_equal)}")
    print(f"baseline_boundary_tie_groups={len(baseline.tie_groups)}")
    print(f"candidate_boundary_tie_groups={len(candidate.tie_groups)}")
    print(
        "representative_conflict_clusters="
        f"{baseline.representative_conflict_clusters}"
    )
    print(
        "candidate_representative_conflict_clusters="
        f"{candidate.representative_conflict_clusters}"
    )

    clean = not missing and not extra and all(raw_equal.values()) and all_three and boundary_ties_equal
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
