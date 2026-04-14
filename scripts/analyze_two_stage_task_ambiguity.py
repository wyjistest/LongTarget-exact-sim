#!/usr/bin/env python3
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_two_stage_coverage_attribution as coverage_attr  # noqa: E402
import analyze_two_stage_selector_candidate_classes as selector_classes  # noqa: E402
import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tile_key(panel_item: dict[str, object]) -> str:
    return (
        f"{panel_item.get('anchor_label', '')}|"
        f"{int(panel_item.get('selection_bucket_length_bp', 0))}|"
        f"{panel_item.get('selection_kind', '')}|"
        f"{int(panel_item.get('start_bp', 0))}|"
        f"{int(panel_item.get('length_bp', 0))}"
    )


def _task_key_tuple(row: dict[str, object]) -> tuple[int, int, int, int, int, str, int]:
    return (
        int(row["fragment_index"]),
        int(row["fragment_start_in_seq"]),
        int(row["fragment_end_in_seq"]),
        int(row["reverse_mode"]),
        int(row["parallel_mode"]),
        str(row["strand"]),
        int(row["rule"]),
    )


def _task_key_dict(task_key: tuple[int, int, int, int, int, str, int]) -> dict[str, object]:
    return {
        "fragment_index": task_key[0],
        "fragment_start_in_seq": task_key[1],
        "fragment_end_in_seq": task_key[2],
        "reverse_mode": task_key[3],
        "parallel_mode": task_key[4],
        "strand": task_key[5],
        "rule": task_key[6],
    }


def _strict_key_tuple_from_payload(payload: dict[str, object]) -> tuple[int, int, int, int, str, int]:
    return (
        int(payload["query_start"]),
        int(payload["query_end"]),
        int(payload["start_in_genome"]),
        int(payload["end_in_genome"]),
        str(payload["strand"]),
        int(payload["rule"]),
    )


def _strict_key_payload(key: tuple[int, int, int, int, str, int]) -> dict[str, object]:
    return {
        "query_start": key[0],
        "query_end": key[1],
        "start_in_genome": key[2],
        "end_in_genome": key[3],
        "strand": key[4],
        "rule": key[5],
    }


def _strict_hit_payload(key: tuple[int, int, int, int, str, int], score: float) -> dict[str, object]:
    payload = _strict_key_payload(key)
    payload["score"] = float(score)
    return payload


def _covered_keys(
    legacy_rows: dict[tuple, dict[str, object]],
    windows: list[dict[str, object]],
) -> set[tuple]:
    covered: set[tuple] = set()
    if not windows:
        return covered
    for key, hit in legacy_rows.items():
        if coverage_attr._matching_windows(hit, windows):
            covered.add(key)
    return covered


def _window_identity(row: dict[str, object]) -> tuple[object, ...]:
    return (
        str(row["strand"]),
        int(row["rule"]),
        int(row["window_start_in_seq"]),
        int(row["window_end_in_seq"]),
        int(row["best_seed_score"]),
        int(row["support_count"]),
    )


def _build_task_map(debug_rows: list[dict[str, object]]) -> dict[tuple[int, int, int, int, int, str, int], dict[str, object]]:
    grouped_rows: dict[tuple[int, int, int, int, int, str, int], list[dict[str, object]]] = defaultdict(list)
    task_index_by_key: dict[tuple[int, int, int, int, int, str, int], int] = {}
    for row in debug_rows:
        task_key = _task_key_tuple(row)
        task_index = int(row["task_index"])
        prev = task_index_by_key.get(task_key)
        if prev is None:
            task_index_by_key[task_key] = task_index
        elif prev != task_index:
            raise RuntimeError(
                f"canonical task key {task_key} maps to multiple task_index values in one debug TSV: {prev} vs {task_index}"
            )
        grouped_rows[task_key].append(row)

    task_map: dict[tuple[int, int, int, int, int, str, int], dict[str, object]] = {}
    for task_key, rows in grouped_rows.items():
        sorted_rows = sorted(rows, key=selector_classes._window_sort_key)
        kept_rows = [row for row in sorted_rows if int(row["after_gate"]) == 1]
        rejected_rows = [
            row for row in sorted_rows if int(row["before_gate"]) == 1 and int(row["after_gate"]) == 0
        ]
        uncovered_rejected_rows = [
            row for row in rejected_rows if not selector_classes._covered_by_kept(row, kept_rows)
        ]
        task_map[task_key] = {
            "task_key": task_key,
            "task_index": task_index_by_key[task_key],
            "rows": sorted_rows,
            "kept_rows": kept_rows,
            "rejected_rows": rejected_rows,
            "uncovered_rejected_rows": uncovered_rejected_rows,
        }
    return task_map


def _best_score(rows: list[dict[str, object]]) -> int | None:
    if not rows:
        return None
    return int(rows[0]["best_seed_score"])


def _score_gap(kept_rows: list[dict[str, object]], rejected_rows: list[dict[str, object]]) -> int | None:
    kept = _best_score(kept_rows)
    rejected = _best_score(rejected_rows)
    if kept is None or rejected is None:
        return None
    return kept - rejected


def _rank_ambiguity(item: dict[str, object]) -> tuple[object, ...]:
    gap = item.get("best_score_gap")
    return (
        -int(item["baseline_inside_rejected_missing_count_top10"]),
        -float(item["baseline_inside_rejected_missing_weight"]),
        -int(item["baseline_uncovered_rejected_window_count"]),
        10**18 if gap is None else int(gap),
        item["tile_key"],
        (
            int(item["task_key"]["fragment_index"]),
            int(item["task_key"]["fragment_start_in_seq"]),
            int(item["task_key"]["fragment_end_in_seq"]),
            int(item["task_key"]["reverse_mode"]),
            int(item["task_key"]["parallel_mode"]),
            str(item["task_key"]["strand"]),
            int(item["task_key"]["rule"]),
        ),
    )


def _rank_rescue_gain(item: dict[str, object]) -> tuple[object, ...]:
    return (
        -int(item["rescue_top5_gain_count"]),
        -int(item["rescue_top10_gain_count"]),
        -float(item["rescue_score_weighted_gain"]),
        int(item["rescue_added_bp_total"]),
        item["tile_key"],
        (
            int(item["task_key"]["fragment_index"]),
            int(item["task_key"]["fragment_start_in_seq"]),
            int(item["task_key"]["fragment_end_in_seq"]),
            int(item["task_key"]["reverse_mode"]),
            int(item["task_key"]["parallel_mode"]),
            str(item["task_key"]["strand"]),
            int(item["task_key"]["rule"]),
        ),
    )


def _render_markdown(summary: dict[str, object]) -> str:
    aggregate = summary["aggregate"]
    lines = [
        "# Task-Level Ambiguity Analysis",
        "",
        f"- baseline_panel_summary: {summary['baseline_panel_summary']}",
        f"- rescue_panel_summary: {summary['rescue_panel_summary']}",
        f"- baseline_label: {summary['baseline_label']}",
        f"- rescue_label: {summary['rescue_label']}",
        f"- tile_count: {aggregate['tile_count']}",
        f"- eligible_task_count: {aggregate['eligible_task_count']}",
        f"- rescue_gain_task_count: {aggregate['rescue_gain_task_count']}",
        f"- false_positive_ambiguity_task_count: {aggregate['false_positive_ambiguity_task_count']}",
        "",
        "## Top Ambiguity Tasks",
        "",
        "| tile | fragment_index | fragment_start | top10_missing | score_weighted_missing | rescue_top10_gain | rescue_gain_weight |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in aggregate["top_ambiguity_tasks"]:
        task_key = item["task_key"]
        lines.append(
            f"| {item['anchor_label']} | {task_key['fragment_index']} | {task_key['fragment_start_in_seq']} | "
            f"{item['baseline_inside_rejected_missing_count_top10']} | {item['baseline_inside_rejected_missing_weight']:.12g} | "
            f"{item['rescue_top10_gain_count']} | {item['rescue_score_weighted_gain']:.12g} |"
        )
    if not aggregate["top_ambiguity_tasks"]:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 |")
    lines.extend(
        [
            "",
            "## Top Rescue-Gain Tasks",
            "",
            "| tile | fragment_index | fragment_start | rescue_top5_gain | rescue_top10_gain | rescue_gain_weight | added_bp |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in aggregate["top_rescue_gain_tasks"]:
        task_key = item["task_key"]
        lines.append(
            f"| {item['anchor_label']} | {task_key['fragment_index']} | {task_key['fragment_start_in_seq']} | "
            f"{item['rescue_top5_gain_count']} | {item['rescue_top10_gain_count']} | "
            f"{item['rescue_score_weighted_gain']:.12g} | {item['rescue_added_bp_total']} |"
        )
    if not aggregate["top_rescue_gain_tasks"]:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 |")
    lines.extend(
        [
            "",
            "## High Ambiguity Zero-Gain Tasks",
            "",
            "| tile | fragment_index | fragment_start | top10_missing | score_weighted_missing | added_bp |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in aggregate["high_ambiguity_zero_gain_tasks"]:
        task_key = item["task_key"]
        lines.append(
            f"| {item['anchor_label']} | {task_key['fragment_index']} | {task_key['fragment_start_in_seq']} | "
            f"{item['baseline_inside_rejected_missing_count_top10']} | {item['baseline_inside_rejected_missing_weight']:.12g} | "
            f"{item['rescue_added_bp_total']} |"
        )
    if not aggregate["high_ambiguity_zero_gain_tasks"]:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 |")
    lines.append("")
    return "\n".join(lines)


def analyze_task_ambiguity(
    baseline_panel_summary_path: Path | str,
    rescue_panel_summary_path: Path | str,
    *,
    baseline_label: str,
    rescue_label: str,
    top_n: int,
) -> dict[str, object]:
    baseline_panel_summary_path = Path(baseline_panel_summary_path).resolve()
    rescue_panel_summary_path = Path(rescue_panel_summary_path).resolve()
    baseline_panel_summary = _load_json(baseline_panel_summary_path)
    rescue_panel_summary = _load_json(rescue_panel_summary_path)

    baseline_items = {
        _tile_key(item): item for item in list(baseline_panel_summary.get("selected_microanchors", []))
    }
    rescue_items = {
        _tile_key(item): item for item in list(rescue_panel_summary.get("selected_microanchors", []))
    }
    if set(baseline_items) != set(rescue_items):
        raise RuntimeError("baseline and rescue panel summaries do not contain the same selected microanchors")

    tiles: list[dict[str, object]] = []
    flat_tasks: list[dict[str, object]] = []
    rescue_gain_task_count = 0
    false_positive_ambiguity_task_count = 0

    for tile_key in sorted(baseline_items):
        baseline_context = selector_classes._load_tile_context(baseline_items[tile_key], candidate_label=baseline_label)
        rescue_context = selector_classes._load_tile_context(rescue_items[tile_key], candidate_label=rescue_label)

        baseline_report_run = baseline_context["report"]["runs"][baseline_label]
        legacy_rows = baseline_context["legacy_rows"]
        ranked_keys = sample_vs_fasim._sorted_strict_score_keys(baseline_context["legacy_summary"].strict_scores)
        top5_keys = set(ranked_keys[: min(5, len(ranked_keys))])
        top10_keys = set(ranked_keys[: min(10, len(ranked_keys))])

        baseline_task_map = _build_task_map(baseline_context["debug_rows"])
        rescue_task_map = _build_task_map(rescue_context["debug_rows"])

        baseline_kept_rows = [
            row for task in baseline_task_map.values() for row in task["kept_rows"]
        ]
        baseline_covered_keys = _covered_keys(legacy_rows, baseline_kept_rows)
        missing_keys = [key for key in ranked_keys if key not in baseline_covered_keys]

        eligible_task_keys = [
            task_key
            for task_key, payload in baseline_task_map.items()
            if payload["kept_rows"] and task_key in rescue_task_map
        ]

        ambiguity_state: dict[tuple[int, int, int, int, int, str, int], dict[str, object]] = {}
        for task_key in eligible_task_keys:
            baseline_task = baseline_task_map[task_key]
            rescue_task = rescue_task_map[task_key]
            baseline_kept = list(baseline_task["kept_rows"])
            rescue_kept = list(rescue_task["kept_rows"])
            baseline_window_ids = {_window_identity(row) for row in baseline_kept}
            rescue_added_rows = [
                row for row in rescue_kept if _window_identity(row) not in baseline_window_ids
            ]
            task_payload = {
                "tile_key": tile_key,
                "anchor_label": str(baseline_items[tile_key].get("anchor_label", "")),
                "task_key": _task_key_dict(task_key),
                "baseline_task_index": int(baseline_task["task_index"]),
                "rescue_task_index": int(rescue_task["task_index"]),
                "baseline_kept_window_count": len(baseline_kept),
                "baseline_uncovered_rejected_window_count": len(baseline_task["uncovered_rejected_rows"]),
                "baseline_inside_rejected_missing_count_overall": 0,
                "baseline_inside_rejected_missing_count_top5": 0,
                "baseline_inside_rejected_missing_count_top10": 0,
                "baseline_inside_rejected_missing_weight": 0.0,
                "best_kept_score": _best_score(baseline_kept),
                "best_rejected_score": _best_score(baseline_task["uncovered_rejected_rows"]),
                "best_score_gap": _score_gap(baseline_kept, baseline_task["uncovered_rejected_rows"]),
                "rescue_kept_window_count": len(rescue_kept),
                "rescue_added_window_count": len(rescue_added_rows),
                "rescue_added_bp_total": sum(int(row["window_bp"]) for row in rescue_added_rows),
                "rescue_gain_strict_keys": [],
                "rescue_gain_strict_key_count": 0,
                "rescue_top5_gain_count": 0,
                "rescue_top10_gain_count": 0,
                "rescue_score_weighted_gain": 0.0,
            }
            ambiguity_state[task_key] = task_payload

        for key in missing_keys:
            hit = legacy_rows[key]
            matching_rejected = []
            for row in coverage_attr._matching_windows(hit, baseline_context["debug_rows"]):
                task_key = _task_key_tuple(row)
                if task_key not in ambiguity_state:
                    continue
                if int(row["before_gate"]) != 1 or int(row["after_gate"]) != 0:
                    continue
                matching_rejected.append(row)
            if not matching_rejected:
                continue
            strongest_row = min(
                matching_rejected,
                key=lambda row: (
                    selector_classes._window_sort_key(row),
                    _task_key_tuple(row),
                ),
            )
            task_payload = ambiguity_state[_task_key_tuple(strongest_row)]
            task_payload["baseline_inside_rejected_missing_count_overall"] += 1
            if key in top5_keys:
                task_payload["baseline_inside_rejected_missing_count_top5"] += 1
            if key in top10_keys:
                task_payload["baseline_inside_rejected_missing_count_top10"] += 1
            task_payload["baseline_inside_rejected_missing_weight"] += max(float(hit["score"]), 0.0)

        for task_key, task_payload in ambiguity_state.items():
            rescue_kept = rescue_task_map[task_key]["kept_rows"]
            rescue_gain_keys = [
                key for key in missing_keys if coverage_attr._matching_windows(legacy_rows[key], rescue_kept)
            ]
            task_payload["rescue_gain_strict_keys"] = [_strict_key_payload(key) for key in rescue_gain_keys]
            task_payload["rescue_gain_strict_key_count"] = len(rescue_gain_keys)
            task_payload["rescue_top5_gain_count"] = sum(1 for key in rescue_gain_keys if key in top5_keys)
            task_payload["rescue_top10_gain_count"] = sum(1 for key in rescue_gain_keys if key in top10_keys)
            task_payload["rescue_score_weighted_gain"] = sum(
                max(float(legacy_rows[key]["score"]), 0.0) for key in rescue_gain_keys
            )
            if task_payload["rescue_gain_strict_key_count"] > 0:
                rescue_gain_task_count += 1
            if (
                task_payload["baseline_inside_rejected_missing_count_overall"] > 0
                and task_payload["rescue_gain_strict_key_count"] == 0
            ):
                false_positive_ambiguity_task_count += 1

        tile_tasks = sorted(ambiguity_state.values(), key=_rank_ambiguity)
        tile_payload = {
            "tile_key": tile_key,
            "anchor_label": str(baseline_items[tile_key].get("anchor_label", "")),
            "selection_bucket_length_bp": int(baseline_items[tile_key].get("selection_bucket_length_bp", 0)),
            "selection_kind": str(baseline_items[tile_key].get("selection_kind", "")),
            "selection_rank": int(baseline_items[tile_key].get("selection_rank", 0)),
            "start_bp": int(baseline_items[tile_key].get("start_bp", 0)),
            "length_bp": int(baseline_items[tile_key].get("length_bp", 0)),
            "baseline_threshold_skipped_after_gate": int(baseline_report_run.get("threshold_skipped_after_gate", 0)),
            "baseline_windows_after_gate": int(baseline_report_run.get("windows_after_gate", len(baseline_kept_rows))),
            "baseline_refine_total_bp": int(
                baseline_report_run.get(
                    "refine_total_bp",
                    sum(int(row["window_bp"]) for row in baseline_kept_rows),
                )
            ),
            "legacy_strict_hits": [
                _strict_hit_payload(key, score)
                for key, score in sorted(
                    baseline_context["legacy_summary"].strict_scores.items(),
                    key=lambda item: (
                        -float(item[1]),
                        item[0],
                    ),
                )
            ],
            "baseline_covered_strict_keys": [
                _strict_key_payload(key) for key in sorted(baseline_covered_keys)
            ],
            "baseline_covered_key_count": len(baseline_covered_keys),
            "tasks": tile_tasks,
        }
        tiles.append(tile_payload)
        flat_tasks.extend(tile_tasks)

    top_ambiguity_tasks = [
        item for item in sorted(flat_tasks, key=_rank_ambiguity)
        if int(item["baseline_inside_rejected_missing_count_overall"]) > 0
    ][:top_n]
    top_rescue_gain_tasks = [
        item for item in sorted(flat_tasks, key=_rank_rescue_gain)
        if int(item["rescue_gain_strict_key_count"]) > 0
    ][:top_n]
    high_ambiguity_zero_gain_tasks = [
        item for item in sorted(flat_tasks, key=_rank_ambiguity)
        if int(item["baseline_inside_rejected_missing_count_overall"]) > 0
        and int(item["rescue_gain_strict_key_count"]) == 0
    ][:top_n]

    return {
        "baseline_panel_summary": str(baseline_panel_summary_path),
        "rescue_panel_summary": str(rescue_panel_summary_path),
        "baseline_label": baseline_label,
        "rescue_label": rescue_label,
        "aggregate": {
            "tile_count": len(tiles),
            "eligible_task_count": len(flat_tasks),
            "rescue_gain_task_count": rescue_gain_task_count,
            "false_positive_ambiguity_task_count": false_positive_ambiguity_task_count,
            "top_ambiguity_tasks": top_ambiguity_tasks,
            "top_rescue_gain_tasks": top_rescue_gain_tasks,
            "high_ambiguity_zero_gain_tasks": high_ambiguity_zero_gain_tasks,
        },
        "tiles": tiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze task-level ambiguity and deferred_exact rescue gain on a fixed panel tile set.",
    )
    parser.add_argument("--baseline-panel-summary", required=True, help="baseline panel summary.json")
    parser.add_argument("--rescue-panel-summary", required=True, help="rescue panel summary.json")
    parser.add_argument(
        "--baseline-label",
        default="",
        help="baseline candidate run label (defaults to baseline panel gated_run_label)",
    )
    parser.add_argument(
        "--rescue-label",
        default="",
        help="rescue candidate run label (defaults to rescue panel gated_run_label)",
    )
    parser.add_argument("--top-n", type=int, default=20, help="number of ranked tasks to surface in aggregate lists")
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json/summary.md")
    args = parser.parse_args()

    baseline_panel_summary = _load_json(Path(args.baseline_panel_summary).resolve())
    rescue_panel_summary = _load_json(Path(args.rescue_panel_summary).resolve())
    baseline_label = args.baseline_label or str(baseline_panel_summary.get("gated_run_label", ""))
    rescue_label = args.rescue_label or str(rescue_panel_summary.get("gated_run_label", ""))
    if not baseline_label:
        raise RuntimeError("missing baseline label; pass --baseline-label or set gated_run_label in baseline panel")
    if not rescue_label:
        raise RuntimeError("missing rescue label; pass --rescue-label or set gated_run_label in rescue panel")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = analyze_task_ambiguity(
        args.baseline_panel_summary,
        args.rescue_panel_summary,
        baseline_label=baseline_label,
        rescue_label=rescue_label,
        top_n=args.top_n,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
