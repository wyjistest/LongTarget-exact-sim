#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


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


def attempt_output_interval(row: dict[str, str]) -> tuple[int, int]:
    start = as_int(row, "output_global_start", -1)
    end = as_int(row, "output_global_end", -1)
    if start >= 0 and end >= 0:
        return start, end
    return (
        as_int(row, "target_global_start", -1),
        as_int(row, "target_global_end", -1),
    )


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


def stability_upper_bound(
    target_window: str,
    query: str,
    para_positive: bool,
    nt_min: int,
) -> float:
    if nt_min <= 0:
        nt_min = 1
    if not query:
        return 0.0
    per_target_best = [
        max(triplex_score(target_base, query_base, para_positive) for query_base in query)
        for target_base in target_window
    ]
    if not per_target_best:
        return 0.0
    per_target_best.sort(reverse=True)
    if len(per_target_best) < nt_min:
        per_target_best = per_target_best + [0.0] * (nt_min - len(per_target_best))
    return sum(per_target_best[:nt_min]) / float(nt_min)


def target_window_for_attempt(
    row: dict[str, str],
    target: str,
    target_origin: int,
) -> str:
    start = as_int(row, "target_global_start", -1) - target_origin
    end = as_int(row, "target_global_end", -1) - target_origin
    if start < 0 or end < start or end > len(target):
        return ""
    return target[start:end]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate pre-traceback stability-risk proxy values for "
            "GASAL2 limited-traceback attempt exports. The proxy is not a "
            "safety certificate unless the attempt export carries enough task "
            "semantics to reconstruct the transformed source/target contract."
        )
    )
    parser.add_argument("--baseline-lite", required=True, type=Path)
    parser.add_argument("--attempt-export", required=True, type=Path)
    parser.add_argument("--query-fasta", required=True, type=Path)
    parser.add_argument("--target-fasta", required=True, type=Path)
    parser.add_argument("--target-origin", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--near-bp", type=int, default=8)
    parser.add_argument("--nt-min", type=int, default=50)
    parser.add_argument("--max-attempts-per-row", type=int, default=8)
    args = parser.parse_args()

    lite_rows = read_tsv(args.baseline_lite)
    attempts = read_tsv(args.attempt_export)
    query = read_fasta_sequence(args.query_fasta)
    target = read_fasta_sequence(args.target_fasta)
    top_rows = sorted(lite_rows, key=stability_sort_key, reverse=True)[: args.top_k]
    frontier = min(
        (as_float(row, "MeanStability", 0.0) for row in top_rows),
        default=0.0,
    )

    print(f"frontier_stability\t{frontier:.6f}")
    print(
        "rank\trow_start\trow_end\trow_score\trow_nt\trow_stability\t"
        "frontier_stability\tmatched_attempts\tkept_attempts\tskipped_attempts\t"
        "risky_skipped_attempts\tbest_upper_bound\tbest_skipped_upper_bound\t"
        "best_risky_skipped_prealign_score\tattempts"
    )
    for rank, row in enumerate(top_rows, 1):
        row_start = as_int(row, "StartInGenome")
        row_end = as_int(row, "EndInGenome")
        matched: list[tuple[int, int, int, int, float, dict[str, str]]] = []
        for attempt in attempts:
            attempt_start, attempt_end = attempt_output_interval(attempt)
            if attempt_start < 0 or attempt_end < 0:
                continue
            distance = interval_distance(row_start, row_end, attempt_start, attempt_end)
            if distance > args.near_bp:
                continue
            overlap = max(0, min(row_end, attempt_end) - max(row_start, attempt_start))
            para_positive = para_positive_from_row(attempt)
            bound = stability_upper_bound(
                target_window_for_attempt(attempt, target, args.target_origin),
                query,
                para_positive,
                max(args.nt_min, as_int(attempt, "nt_min_length", args.nt_min)),
            )
            matched.append((distance, -overlap, attempt_start, attempt_end, bound, attempt))
        matched.sort(
            key=lambda item: (
                item[0],
                item[1],
                -item[4],
                -as_int(item[5], "prealign_score"),
                as_int(item[5], "scoreinfo_index"),
                as_int(item[5], "position"),
            )
        )
        kept = [item for item in matched if item[5].get("decision") == "keep"]
        skipped = [item for item in matched if item[5].get("decision") == "skip"]
        risky_skipped = [item for item in skipped if item[4] >= frontier]
        best_bound = max((item[4] for item in matched), default=0.0)
        best_skipped_bound = max((item[4] for item in skipped), default=0.0)
        best_risky_score = max(
            (as_int(item[5], "prealign_score") for item in risky_skipped),
            default=0,
        )
        attempt_text: list[str] = []
        for distance, neg_overlap, attempt_start, attempt_end, bound, attempt in matched[: args.max_attempts_per_row]:
            attempt_text.append(
                ",".join(
                    [
                        f"d={distance}",
                        f"ov={-neg_overlap}",
                        f"decision={attempt.get('decision', '')}",
                        f"score={attempt.get('prealign_score', '')}",
                        f"size={attempt.get('target_size', '')}",
                        f"ub={bound:.6f}",
                        f"global={attempt_start}-{attempt_end}",
                        f"si={attempt.get('scoreinfo_index', '')}",
                    ]
                )
            )
        print(
            "\t".join(
                [
                    str(rank),
                    str(row_start),
                    str(row_end),
                    row.get("Score", ""),
                    row.get("Nt(bp)", ""),
                    row.get("MeanStability", ""),
                    f"{frontier:.6f}",
                    str(len(matched)),
                    str(len(kept)),
                    str(len(skipped)),
                    str(len(risky_skipped)),
                    f"{best_bound:.6f}",
                    f"{best_skipped_bound:.6f}",
                    str(best_risky_score),
                    "; ".join(attempt_text),
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
