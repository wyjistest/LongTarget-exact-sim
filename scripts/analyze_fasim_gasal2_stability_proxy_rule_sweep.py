#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_fasta_sequence(path: Path) -> str:
    pieces: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            pieces.append(line.upper())
    return "".join(pieces)


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value == "":
        return default
    return int(float(value))


def row_key(row: dict[str, str]) -> str:
    columns = [
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "Strand",
        "Rule",
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Score",
        "Nt(bp)",
        "MeanIdentity(%)",
        "MeanStability",
    ]
    return "\t".join(row.get(column, "") for column in columns)


def stability_sort_key(row: dict[str, str]) -> tuple[float, float, float, str]:
    return (
        as_float(row, "MeanStability", float("-inf")),
        as_float(row, "Nt(bp)", float("-inf")),
        as_float(row, "Score", float("-inf")),
        row_key(row),
    )


def interval_distance(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    overlap = min(a_end, b_end) - max(a_start, b_start)
    if overlap >= 0:
        return 0
    return min(abs(a_start - b_end), abs(b_start - a_end))


def interval_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def attempt_output_interval(row: dict[str, str]) -> tuple[int, int]:
    start = as_int(row, "output_global_start", -1)
    end = as_int(row, "output_global_end", -1)
    if start >= 0 and end >= 0:
        return start, end
    return (
        as_int(row, "target_global_start", -1),
        as_int(row, "target_global_end", -1),
    )


def attempt_target_interval(row: dict[str, str], target_origin: int) -> tuple[int, int]:
    start = as_int(row, "target_global_start", -1) - target_origin
    end = as_int(row, "target_global_end", -1) - target_origin
    return start, end


def triplex_score(target_base: str, query_base: str, para_positive: bool) -> float:
    if para_positive:
        return {
            ("A", "T"): 3.7,
            ("T", "G"): 2.8,
            ("G", "G"): 2.2,
            ("G", "T"): 2.4,
            ("G", "C"): 4.5,
            ("C", "T"): 2.6,
            ("C", "C"): 2.4,
        }.get((target_base, query_base), 0.0)
    return {
        ("A", "A"): 3.0,
        ("A", "T"): 3.5,
        ("A", "C"): 1.0,
        ("T", "G"): 1.0,
        ("G", "A"): 1.0,
        ("G", "G"): 3.0,
        ("G", "C"): 3.0,
        ("C", "T"): 2.0,
        ("C", "C"): 1.0,
    }.get((target_base, query_base), 0.0)


def para_positive_from_row(row: dict[str, str]) -> bool:
    task_para = row.get("task_para", "")
    if task_para not in ("", "-1"):
        return as_int(row, "task_para") > 0
    strand = row.get("Strand", "")
    if strand.startswith("Anti"):
        return False
    if strand.startswith("Para"):
        return True
    return True


def best_target_base_scores(query: str, para_positive: bool) -> dict[str, float]:
    query_bases = sorted(set(query.upper()))
    return {
        target_base: max(
            (triplex_score(target_base, query_base, para_positive) for query_base in query_bases),
            default=0.0,
        )
        for target_base in ("A", "C", "G", "T", "N")
    }


def stability_upper_bound_fast(
    target_window: str,
    best_scores: dict[str, float],
    nt_min: int,
) -> float:
    if nt_min <= 0:
        nt_min = 1
    per_target_best = [best_scores.get(base, 0.0) for base in target_window.upper()]
    if len(per_target_best) < nt_min:
        per_target_best = per_target_best + [0.0] * (nt_min - len(per_target_best))
    if not per_target_best:
        return 0.0
    per_target_best.sort(reverse=True)
    return sum(per_target_best[:nt_min]) / float(nt_min)


@dataclass(frozen=True)
class AttemptFeature:
    index: int
    row: dict[str, str]
    decision: str
    prealign_score: int
    target_size: int
    output_start: int
    output_end: int
    max_top_overlap: int = 0
    upper_bound: float | None = None


@dataclass(frozen=True)
class Rule:
    label: str
    predicate: Callable[[AttemptFeature], bool]


def parse_proxy_attempt_token(token: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for piece in token.split(","):
        piece = piece.strip()
        if not piece or "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        fields[key] = value
    return fields


def parse_global_interval(value: str) -> tuple[int, int]:
    start, end = value.split("-", 1)
    return int(start), int(end)


def attempt_lookup_key_from_row(row: dict[str, str]) -> tuple[int, int, int, int, int, str]:
    start, end = attempt_output_interval(row)
    return (
        as_int(row, "scoreinfo_index"),
        as_int(row, "prealign_score"),
        as_int(row, "target_size"),
        start,
        end,
        row.get("decision", ""),
    )


def attempt_lookup_key_from_proxy(fields: dict[str, str]) -> tuple[int, int, int, int, int, str] | None:
    if "global" not in fields:
        return None
    start, end = parse_global_interval(fields["global"])
    return (
        int(fields.get("si", "0")),
        int(float(fields.get("score", "0"))),
        int(float(fields.get("size", "0"))),
        start,
        end,
        fields.get("decision", ""),
    )


def load_proxy_summary(
    path: Path,
    attempt_rows: list[dict[str, str]],
) -> tuple[float | None, dict[int, float], dict[int, int], dict[int, set[int]]]:
    key_to_indices: dict[tuple[int, int, int, int, int, str], list[int]] = {}
    for index, row in enumerate(attempt_rows):
        key_to_indices.setdefault(attempt_lookup_key_from_row(row), []).append(index)

    frontier: float | None = None
    upper_bound_by_attempt: dict[int, float] = {}
    overlap_by_attempt: dict[int, int] = {}
    risky_by_rank: dict[int, set[int]] = {}
    rows: list[dict[str, str]] = []

    with path.open(encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle if line.strip()]
    if lines and lines[0].startswith("frontier_stability\t"):
        frontier = float(lines[0].split("\t", 1)[1])
        lines = lines[1:]
    if lines:
        rows = list(csv.DictReader(lines, delimiter="\t"))

    for row in rows:
        rank = as_int(row, "rank", 0)
        row_frontier = as_float(row, "frontier_stability", frontier or 0.0)
        for token in row.get("attempts", "").split(";"):
            fields = parse_proxy_attempt_token(token)
            key = attempt_lookup_key_from_proxy(fields)
            if key is None:
                continue
            indices = key_to_indices.get(key, [])
            if not indices:
                continue
            upper_bound = float(fields.get("ub", "0"))
            overlap = int(float(fields.get("ov", "0")))
            for index in indices:
                upper_bound_by_attempt[index] = max(upper_bound_by_attempt.get(index, 0.0), upper_bound)
                overlap_by_attempt[index] = max(overlap_by_attempt.get(index, 0), overlap)
                if fields.get("decision") == "skip" and upper_bound >= row_frontier:
                    risky_by_rank.setdefault(rank, set()).add(index)
    return frontier, upper_bound_by_attempt, overlap_by_attempt, risky_by_rank


def build_rules(
    score_mins: list[int],
    upper_bound_mins: list[float],
    overlap_mins: list[int],
) -> list[Rule]:
    rules: list[Rule] = []
    for score_min in score_mins:
        rules.append(
            Rule(
                f"score>={score_min}",
                lambda attempt, score_min=score_min: attempt.prealign_score >= score_min,
            )
        )
    for upper_bound_min in upper_bound_mins:
        rules.append(
            Rule(
                f"ub>={upper_bound_min:.6f}",
                lambda attempt, upper_bound_min=upper_bound_min: (
                    attempt.upper_bound is not None and attempt.upper_bound >= upper_bound_min
                ),
            )
        )
    for overlap_min in overlap_mins:
        rules.append(
            Rule(
                f"overlap>={overlap_min}",
                lambda attempt, overlap_min=overlap_min: attempt.max_top_overlap >= overlap_min,
            )
        )
    for score_min in score_mins:
        for upper_bound_min in upper_bound_mins:
            rules.append(
                Rule(
                    f"score>={score_min}&ub>={upper_bound_min:.6f}",
                    lambda attempt, score_min=score_min, upper_bound_min=upper_bound_min: (
                        attempt.prealign_score >= score_min
                        and attempt.upper_bound is not None
                        and attempt.upper_bound >= upper_bound_min
                    ),
                )
            )
    for score_min in score_mins:
        for overlap_min in overlap_mins:
            rules.append(
                Rule(
                    f"score>={score_min}&overlap>={overlap_min}",
                    lambda attempt, score_min=score_min, overlap_min=overlap_min: (
                        attempt.prealign_score >= score_min and attempt.max_top_overlap >= overlap_min
                    ),
                )
            )
    for upper_bound_min in upper_bound_mins:
        for overlap_min in overlap_mins:
            rules.append(
                Rule(
                    f"ub>={upper_bound_min:.6f}&overlap>={overlap_min}",
                    lambda attempt, upper_bound_min=upper_bound_min, overlap_min=overlap_min: (
                        attempt.upper_bound is not None
                        and attempt.upper_bound >= upper_bound_min
                        and attempt.max_top_overlap >= overlap_min
                    ),
                )
            )
    for score_min in score_mins:
        for upper_bound_min in upper_bound_mins:
            for overlap_min in overlap_mins:
                rules.append(
                    Rule(
                        f"score>={score_min}&ub>={upper_bound_min:.6f}&overlap>={overlap_min}",
                        lambda attempt,
                        score_min=score_min,
                        upper_bound_min=upper_bound_min,
                        overlap_min=overlap_min: (
                            attempt.prealign_score >= score_min
                            and attempt.upper_bound is not None
                            and attempt.upper_bound >= upper_bound_min
                            and attempt.max_top_overlap >= overlap_min
                        ),
                    )
                )
    return rules


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep offline rescue rules for GASAL2 limited-traceback attempts. "
            "This estimates whether a score/proxy/overlap rule can rescue "
            "top-stability risk rows without pulling back too many tracebacks."
        )
    )
    parser.add_argument("--baseline-lite", required=True, type=Path)
    parser.add_argument("--attempt-export", required=True, type=Path)
    parser.add_argument("--proxy-summary", type=Path)
    parser.add_argument("--query-fasta", type=Path)
    parser.add_argument("--target-fasta", type=Path)
    parser.add_argument("--target-origin", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--near-bp", type=int, default=8)
    parser.add_argument("--nt-min", type=int, default=50)
    parser.add_argument("--baseline-traceback", type=int)
    parser.add_argument("--score-min", action="append", type=int, default=[])
    parser.add_argument("--upper-bound-min", action="append", type=float, default=[])
    parser.add_argument("--overlap-min", action="append", type=int, default=[])
    args = parser.parse_args()

    if bool(args.query_fasta) != bool(args.target_fasta):
        raise SystemExit("--query-fasta and --target-fasta must be provided together")

    lite_rows = read_tsv(args.baseline_lite)
    attempt_rows = read_tsv(args.attempt_export)
    top_rows = sorted(lite_rows, key=stability_sort_key, reverse=True)[: args.top_k]
    frontier = min((as_float(row, "MeanStability", 0.0) for row in top_rows), default=0.0)
    upper_bound_by_attempt: dict[int, float] = {}
    overlap_by_attempt: dict[int, int] = {}
    risky_by_rank: dict[int, set[int]] = {}

    if args.proxy_summary:
        proxy_frontier, proxy_upper_bounds, proxy_overlaps, proxy_risky = load_proxy_summary(
            args.proxy_summary,
            attempt_rows,
        )
        if proxy_frontier is not None:
            frontier = proxy_frontier
        upper_bound_by_attempt.update(proxy_upper_bounds)
        overlap_by_attempt.update(proxy_overlaps)
        for rank, indices in proxy_risky.items():
            risky_by_rank.setdefault(rank, set()).update(indices)

    if args.query_fasta and args.target_fasta:
        query = read_fasta_sequence(args.query_fasta)
        target = read_fasta_sequence(args.target_fasta)
        best_scores_by_para = {
            True: best_target_base_scores(query, True),
            False: best_target_base_scores(query, False),
        }
        for index, row in enumerate(attempt_rows):
            if row.get("decision") != "skip":
                continue
            start, end = attempt_target_interval(row, args.target_origin)
            if start < 0 or end < start or end > len(target):
                continue
            nt_min = max(args.nt_min, as_int(row, "nt_min_length", args.nt_min))
            upper_bound_by_attempt[index] = stability_upper_bound_fast(
                target[start:end],
                best_scores_by_para[para_positive_from_row(row)],
                nt_min,
            )

    matched_by_rank: dict[int, set[int]] = {}
    max_overlap_by_attempt: dict[int, int] = dict(overlap_by_attempt)
    for rank, row in enumerate(top_rows, 1):
        row_start = as_int(row, "StartInGenome")
        row_end = as_int(row, "EndInGenome")
        for index, attempt in enumerate(attempt_rows):
            attempt_start, attempt_end = attempt_output_interval(attempt)
            if attempt_start < 0 or attempt_end < 0:
                continue
            if interval_distance(row_start, row_end, attempt_start, attempt_end) > args.near_bp:
                continue
            overlap = interval_overlap(row_start, row_end, attempt_start, attempt_end)
            max_overlap_by_attempt[index] = max(max_overlap_by_attempt.get(index, 0), overlap)
            matched_by_rank.setdefault(rank, set()).add(index)
            if (
                attempt.get("decision") == "skip"
                and upper_bound_by_attempt.get(index) is not None
                and upper_bound_by_attempt[index] >= frontier
            ):
                risky_by_rank.setdefault(rank, set()).add(index)

    features: list[AttemptFeature] = []
    for index, row in enumerate(attempt_rows):
        start, end = attempt_output_interval(row)
        features.append(
            AttemptFeature(
                index=index,
                row=row,
                decision=row.get("decision", ""),
                prealign_score=as_int(row, "prealign_score"),
                target_size=as_int(row, "target_size"),
                output_start=start,
                output_end=end,
                max_top_overlap=max_overlap_by_attempt.get(index, 0),
                upper_bound=upper_bound_by_attempt.get(index),
            )
        )

    if not args.score_min and not args.upper_bound_min and not args.overlap_min:
        args.score_min = [116]
        args.upper_bound_min = [frontier]

    rules = build_rules(args.score_min, args.upper_bound_min, args.overlap_min)
    skipped_indices = {attempt.index for attempt in features if attempt.decision == "skip"}
    total_skipped = len(skipped_indices)
    baseline_traceback = args.baseline_traceback
    if baseline_traceback is None:
        baseline_traceback = sum(1 for attempt in features if attempt.decision == "keep")

    risky_indices: set[int] = set()
    for indices in risky_by_rank.values():
        risky_indices.update(index for index in indices if index in skipped_indices)
    total_risky_skipped = len(risky_indices)

    print(
        "rule\tcovered_topk_rows\ttotal_topk_rows\trisky_skipped_covered\t"
        "total_risky_skipped\trescued_skipped_attempts\ttotal_skipped_attempts\t"
        "rescue_fraction_of_all_skipped\testimated_traceback_after_rescue"
    )
    for rule in rules:
        rescued = {
            attempt.index
            for attempt in features
            if attempt.index in skipped_indices and rule.predicate(attempt)
        }
        risky_covered = risky_indices & rescued
        covered_ranks = [
            rank
            for rank, indices in risky_by_rank.items()
            if any(index in risky_covered for index in indices)
        ]
        rescue_fraction = (len(rescued) / float(total_skipped)) if total_skipped else 0.0
        print(
            "\t".join(
                [
                    rule.label,
                    str(len(covered_ranks)),
                    str(len(top_rows)),
                    str(len(risky_covered)),
                    str(total_risky_skipped),
                    str(len(rescued)),
                    str(total_skipped),
                    f"{rescue_fraction:.6f}",
                    str(baseline_traceback + len(rescued)),
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
