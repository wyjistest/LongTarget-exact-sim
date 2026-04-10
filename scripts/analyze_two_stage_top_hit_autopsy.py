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
                    "query_start": int(parts[index["QueryStart"]]),
                    "query_end": int(parts[index["QueryEnd"]]),
                    "start_in_genome": int(parts[index["StartInGenome"]]),
                    "end_in_genome": int(parts[index["EndInGenome"]]),
                    "strand": parts[index["Strand"]],
                    "rule": int(parts[index["Rule"]]),
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


def _matching_debug_rows(top_hit: dict[str, object], debug_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for row in debug_rows:
        if row["rule"] != top_hit["rule"]:
            continue
        if row["strand"] != top_hit["strand"]:
            continue
        if row["window_start_in_seq"] is None or row["window_end_in_seq"] is None:
            continue
        if row["window_start_in_seq"] <= top_hit["start_in_seq"] and row["window_end_in_seq"] >= top_hit["end_in_seq"]:
            matches.append(row)
    return sorted(
        matches,
        key=lambda row: (
            row["after_gate"] == 1,
            -(row["best_seed_score"] or -10**18),
            row["window_start_in_seq"] or 10**18,
            row["window_end_in_seq"] or 10**18,
        ),
        reverse=True,
    )


def _classify_matches(matches: list[dict[str, object]]) -> str:
    if not matches:
        return "no_matching_window_trace"
    if any(row["after_gate"] == 1 for row in matches):
        return "survived_gate_missing_downstream"
    return "rejected_by_gate"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze which gated window killed a legacy top hit in a two-stage threshold benchmark.",
    )
    parser.add_argument("--report", required=True, help="threshold-mode report.json path")
    parser.add_argument("--debug-csv", required=True, help="LONGTARGET_TWO_STAGE_DEBUG_WINDOWS_CSV output")
    parser.add_argument(
        "--candidate-label",
        default="deferred_exact_minimal_v1",
        help="candidate run label to autopsy (default: deferred_exact_minimal_v1)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="optional output JSON path (default: print to stdout)",
    )
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    debug_csv_path = Path(args.debug_csv).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    runs = report["runs"]
    if "legacy" not in runs:
        raise RuntimeError("report is missing legacy run")
    if args.candidate_label not in runs:
        raise RuntimeError(f"report is missing candidate run: {args.candidate_label}")

    compare_output_mode = report["compare_output_mode"]
    legacy_dir = Path(runs["legacy"]["output_dir"]).resolve()
    candidate_dir = Path(runs[args.candidate_label]["output_dir"]).resolve()

    legacy_summary = sample_vs_fasim._aggregate_output_summaries(
        list(sample_vs_fasim._load_output_map(legacy_dir, compare_output_mode).values())
    )
    candidate_summary = sample_vs_fasim._aggregate_output_summaries(
        list(sample_vs_fasim._load_output_map(candidate_dir, compare_output_mode).values())
    )
    legacy_rows = _load_output_rows(legacy_dir, compare_output_mode)
    debug_rows = _load_debug_rows(debug_csv_path)

    missing_top_hit_keys = sorted(legacy_summary.top_hit_keys - candidate_summary.strict_keys)
    autopsy_items: list[dict[str, object]] = []
    for key in missing_top_hit_keys:
        top_hit = legacy_rows[key]
        matches = _matching_debug_rows(top_hit, debug_rows)
        autopsy_items.append(
            {
                "top_hit": top_hit,
                "classification": _classify_matches(matches),
                "matching_window_count": len(matches),
                "matching_windows": matches,
            }
        )

    result = {
        "report": str(report_path),
        "debug_csv": str(debug_csv_path),
        "candidate_label": args.candidate_label,
        "legacy_top_hit_count": len(legacy_summary.top_hit_keys),
        "missing_top_hit_count": len(missing_top_hit_keys),
        "autopsy": autopsy_items,
        "comparison_vs_legacy": report.get("comparisons_vs_legacy", {}).get(args.candidate_label, {}),
    }

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
