#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402

CLASS_INSIDE_KEPT = "inside_kept_window"
CLASS_INSIDE_REJECTED = "inside_rejected_window"
CLASS_OUTSIDE_NEAR_KEPT = "outside_kept_but_near_kept"
CLASS_FAR_OUTSIDE = "far_outside_all_kept"
ATTRIBUTION_CLASSES = (
    CLASS_INSIDE_KEPT,
    CLASS_INSIDE_REJECTED,
    CLASS_OUTSIDE_NEAR_KEPT,
    CLASS_FAR_OUTSIDE,
)


def _strict_key_dict(key: tuple) -> dict[str, object]:
    return {
        "query_start": key[0],
        "query_end": key[1],
        "start_in_genome": key[2],
        "end_in_genome": key[3],
        "strand": key[4],
        "rule": key[5],
    }


def _load_output_rows(dir_path: Path, compare_output_mode: str) -> dict[tuple, dict[str, object]]:
    rows: dict[tuple, dict[str, object]] = {}
    for path in sorted(dir_path.glob(sample_vs_fasim._output_glob(compare_output_mode))):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            header = f.readline().rstrip("\n").split("\t")
            index = {name: i for i, name in enumerate(header)}
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                key = (
                    int(parts[index["QueryStart"]]),
                    int(parts[index["QueryEnd"]]),
                    int(parts[index["StartInGenome"]]),
                    int(parts[index["EndInGenome"]]),
                    parts[index["Strand"]],
                    int(parts[index["Rule"]]),
                )
                rows[key] = {
                    "file": path.name,
                    "chr": parts[index["Chr"]],
                    "query_start": key[0],
                    "query_end": key[1],
                    "start_in_genome": key[2],
                    "end_in_genome": key[3],
                    "strand": key[4],
                    "rule": key[5],
                    "start_in_seq": int(parts[index["StartInSeq"]]),
                    "end_in_seq": int(parts[index["EndInSeq"]]),
                    "direction": parts[index["Direction"]],
                    "score": float(parts[index["Score"]]),
                    "nt_bp": int(parts[index["Nt(bp)"]]),
                    "mean_identity": float(parts[index["MeanIdentity(%)"]]),
                    "mean_stability": float(parts[index["MeanStability"]]),
                }
    return rows


def _load_debug_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for raw in reader:
            row = dict(raw)
            for name in (
                "task_index",
                "fragment_index",
                "fragment_start_in_seq",
                "fragment_end_in_seq",
                "reverse_mode",
                "parallel_mode",
                "rule",
                "window_id",
                "window_start_in_fragment",
                "window_end_in_fragment",
                "window_start_in_seq",
                "window_end_in_seq",
                "best_seed_score",
                "support_count",
                "window_bp",
                "before_gate",
                "after_gate",
                "peak_score_ok",
                "support_ok",
                "margin_ok",
                "strong_score_ok",
            ):
                row[name] = int(row[name]) if row[name] != "" else None
            for name in ("sorted_rank", "second_best_seed_score", "margin"):
                row[name] = int(row[name]) if row[name] != "" else None
            rows.append(row)
    return rows


def _matching_windows(hit: dict[str, object], debug_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for row in debug_rows:
        if row["rule"] != hit["rule"]:
            continue
        if row["strand"] != hit["strand"]:
            continue
        start_in_seq = row.get("window_start_in_seq")
        end_in_seq = row.get("window_end_in_seq")
        if start_in_seq is None or end_in_seq is None:
            continue
        if start_in_seq <= hit["start_in_seq"] and end_in_seq >= hit["end_in_seq"]:
            matches.append(row)
    return matches


def _interval_distance(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    if a_end < b_start:
        return b_start - a_end
    if b_end < a_start:
        return a_start - b_end
    return 0


def _nearest_kept_distance(hit: dict[str, object], debug_rows: list[dict[str, object]]) -> int | None:
    distances: list[int] = []
    for row in debug_rows:
        if row["rule"] != hit["rule"]:
            continue
        if row["strand"] != hit["strand"]:
            continue
        if row["after_gate"] != 1:
            continue
        start_in_seq = row.get("window_start_in_seq")
        end_in_seq = row.get("window_end_in_seq")
        if start_in_seq is None or end_in_seq is None:
            continue
        distances.append(
            _interval_distance(
                hit["start_in_seq"],
                hit["end_in_seq"],
                start_in_seq,
                end_in_seq,
            )
        )
    return min(distances) if distances else None


def _classify_missing_hit(
    hit: dict[str, object],
    debug_rows: list[dict[str, object]],
    *,
    near_distance_bp: int,
) -> dict[str, object]:
    matches = _matching_windows(hit, debug_rows)
    kept_matches = [row for row in matches if row["after_gate"] == 1]
    rejected_matches = [row for row in matches if row["before_gate"] == 1 and row["after_gate"] == 0]
    nearest_kept_distance = _nearest_kept_distance(hit, debug_rows)
    if kept_matches:
        classification = CLASS_INSIDE_KEPT
    elif rejected_matches:
        classification = CLASS_INSIDE_REJECTED
    elif nearest_kept_distance is not None and nearest_kept_distance <= near_distance_bp:
        classification = CLASS_OUTSIDE_NEAR_KEPT
    else:
        classification = CLASS_FAR_OUTSIDE
    return {
        "classification": classification,
        "matching_kept_window_count": len(kept_matches),
        "matching_rejected_window_count": len(rejected_matches),
        "nearest_kept_distance_bp": nearest_kept_distance,
        "matching_kept_windows": kept_matches,
        "matching_rejected_windows": rejected_matches,
    }


def _count_template() -> dict[str, int]:
    return {name: 0 for name in ATTRIBUTION_CLASSES}


def _weight_template() -> dict[str, float]:
    return {name: 0.0 for name in ATTRIBUTION_CLASSES}


def _share_dict(values: dict[str, float | int], total: float | int) -> dict[str, float]:
    if total == 0:
        return {name: 0.0 for name in values}
    return {name: float(value) / float(total) for name, value in values.items()}


def _subset_summary(items: list[dict[str, object]]) -> dict[str, object]:
    counts = _count_template()
    for item in items:
        counts[item["classification"]] += 1
    total = len(items)
    return {
        "missing_count": total,
        "count_by_class": counts,
        "share_by_class": _share_dict(counts, total),
    }


def _score_weighted_summary(items: list[dict[str, object]], *, total_legacy_weight: float) -> dict[str, object]:
    weights = _weight_template()
    for item in items:
        weights[item["classification"]] += max(float(item["hit"]["score"]), 0.0)
    total_missing_weight = sum(weights.values())
    return {
        "total_missing_weight": total_missing_weight,
        "total_legacy_weight": total_legacy_weight,
        "weight_by_class": weights,
        "share_of_missing_weight_by_class": _share_dict(weights, total_missing_weight),
        "share_of_legacy_weight_by_class": _share_dict(weights, total_legacy_weight),
    }


def _ranked_strict_keys(summary: sample_vs_fasim.OutputSummary) -> list[tuple]:
    return sample_vs_fasim._sorted_strict_score_keys(summary.strict_scores)


def analyze_coverage_attribution(
    report_path: Path | str,
    *,
    candidate_label: str = "deferred_exact_minimal_v2",
    debug_csv: Path | str | None = None,
    near_distance_bp: int = -1,
    max_examples_per_class: int = 5,
) -> dict[str, object]:
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    runs = report["runs"]
    if "legacy" not in runs:
        raise RuntimeError("report is missing legacy run")
    if candidate_label not in runs:
        raise RuntimeError(f"report is missing candidate run: {candidate_label}")

    debug_csv_value = str(debug_csv) if debug_csv else runs[candidate_label].get("debug_windows_csv", "")
    if not debug_csv_value:
        raise RuntimeError("missing debug CSV path; pass --debug-csv or include debug_windows_csv in report")
    debug_csv_path = Path(debug_csv_value).resolve()
    if not debug_csv_path.exists():
        raise RuntimeError(f"missing debug CSV: {debug_csv_path}")

    compare_output_mode = report["compare_output_mode"]
    legacy_dir = Path(runs["legacy"]["output_dir"]).resolve()
    candidate_dir = Path(runs[candidate_label]["output_dir"]).resolve()
    legacy_output_map = sample_vs_fasim._load_output_map(legacy_dir, compare_output_mode)
    candidate_output_map = sample_vs_fasim._load_output_map(candidate_dir, compare_output_mode)
    legacy_summary = sample_vs_fasim._aggregate_output_summaries(list(legacy_output_map.values()))
    candidate_summary = sample_vs_fasim._aggregate_output_summaries(list(candidate_output_map.values()))
    legacy_rows = _load_output_rows(legacy_dir, compare_output_mode)
    debug_rows = _load_debug_rows(debug_csv_path)

    if near_distance_bp < 0:
        near_distance_bp = max(
            int(report.get("refine_pad_bp", 0)),
            int(report.get("refine_merge_gap_bp", 0)),
        )

    missing_keys = [key for key in _ranked_strict_keys(legacy_summary) if key not in candidate_summary.strict_keys]
    missing_items: list[dict[str, object]] = []
    for key in missing_keys:
        hit = legacy_rows[key]
        attribution = _classify_missing_hit(hit, debug_rows, near_distance_bp=near_distance_bp)
        missing_items.append(
            {
                "strict_key_tuple": key,
                "strict_key": _strict_key_dict(key),
                "hit": hit,
                **attribution,
            }
        )

    ranked_keys = _ranked_strict_keys(legacy_summary)
    top1_keys = set(ranked_keys[:1])
    top5_keys = set(ranked_keys[:5])
    top10_keys = set(ranked_keys[:10])

    examples_by_class: dict[str, list[dict[str, object]]] = {name: [] for name in ATTRIBUTION_CLASSES}
    for item in missing_items:
        class_examples = examples_by_class[item["classification"]]
        if len(class_examples) >= max_examples_per_class:
            continue
        class_examples.append(
            {
                "hit": item["hit"],
                "nearest_kept_distance_bp": item["nearest_kept_distance_bp"],
                "matching_kept_window_count": item["matching_kept_window_count"],
                "matching_rejected_window_count": item["matching_rejected_window_count"],
            }
        )

    total_legacy_weight = sum(max(score, 0.0) for score in legacy_summary.strict_scores.values())
    return {
        "report": str(report_path),
        "candidate_label": candidate_label,
        "debug_csv": str(debug_csv_path),
        "near_distance_bp": near_distance_bp,
        "legacy_strict_hit_count": len(legacy_summary.strict_keys),
        "candidate_strict_hit_count": len(candidate_summary.strict_keys),
        "missing_strict_hit_count": len(missing_items),
        "summary": {
            "overall": _subset_summary(missing_items),
            "top1_missing": _subset_summary(
                [item for item in missing_items if item["strict_key_tuple"] in top1_keys]
            ),
            "top5_missing": _subset_summary(
                [item for item in missing_items if item["strict_key_tuple"] in top5_keys]
            ),
            "top10_missing": _subset_summary(
                [item for item in missing_items if item["strict_key_tuple"] in top10_keys]
            ),
            "score_weighted_missing": _score_weighted_summary(missing_items, total_legacy_weight=total_legacy_weight),
        },
        "examples_by_class": examples_by_class,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify which layer lost legacy hits in a two-stage threshold shortlist lane.",
    )
    parser.add_argument("--report", required=True, help="threshold-mode report.json path")
    parser.add_argument(
        "--candidate-label",
        default="deferred_exact_minimal_v2",
        help="candidate run label to analyze (default: deferred_exact_minimal_v2)",
    )
    parser.add_argument(
        "--debug-csv",
        default="",
        help="optional debug windows TSV; defaults to report.runs[candidate].debug_windows_csv",
    )
    parser.add_argument(
        "--near-distance-bp",
        default=-1,
        type=int,
        help="optional override for near-kept classification distance; default uses max(refine_pad_bp, refine_merge_gap_bp)",
    )
    parser.add_argument(
        "--max-examples-per-class",
        default=5,
        type=int,
        help="max examples to retain per attribution class",
    )
    parser.add_argument("--output", default="", help="optional output JSON path")
    args = parser.parse_args()

    result = analyze_coverage_attribution(
        args.report,
        candidate_label=args.candidate_label,
        debug_csv=args.debug_csv or None,
        near_distance_bp=args.near_distance_bp,
        max_examples_per_class=args.max_examples_per_class,
    )

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(output_path)
        return 0

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
