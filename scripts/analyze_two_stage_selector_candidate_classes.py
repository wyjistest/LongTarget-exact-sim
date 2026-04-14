#!/usr/bin/env python3
import argparse
import json
import statistics
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
import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


CANDIDATE_CLASSES = (
    "support1_margin_present",
    "support2",
    "support3plus_low_support_or_margin",
    "covered_by_kept",
    "score_lt_85",
    "other",
)
RECOMMENDED_CLASS_ORDER = (
    "support1_margin_present",
    "support2",
    "support3plus_low_support_or_margin",
    "other",
    "score_lt_85",
    "covered_by_kept",
)
COUNT_VIEWS = ("overall", "top5_missing", "top10_missing")
WEIGHT_VIEW = "score_weighted_missing"
SCORE_LT_85_BANDS = ("80_84", "75_79", "lt_75")
SCORE_LT_75_BANDS = ("70_74", "65_69", "lt_65")


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _share_dict(values: dict[str, int | float], total: int | float) -> dict[str, float]:
    if not total:
        return {name: 0.0 for name in values}
    return {name: float(value) / float(total) for name, value in values.items()}


def _class_count_template() -> dict[str, int]:
    return {name: 0 for name in CANDIDATE_CLASSES}


def _class_weight_template() -> dict[str, float]:
    return {name: 0.0 for name in CANDIDATE_CLASSES}


def _score_lt_85_band_count_template() -> dict[str, int]:
    return {name: 0 for name in SCORE_LT_85_BANDS}


def _score_lt_85_band_weight_template() -> dict[str, float]:
    return {name: 0.0 for name in SCORE_LT_85_BANDS}


def _score_lt_75_band_count_template() -> dict[str, int]:
    return {name: 0 for name in SCORE_LT_75_BANDS}


def _score_lt_75_band_weight_template() -> dict[str, float]:
    return {name: 0.0 for name in SCORE_LT_75_BANDS}


def _matched_count_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_count: int,
) -> dict[str, object]:
    matched_missing_count = len(items)
    return {
        "matched_missing_count": matched_missing_count,
        "total_missing_count": total_missing_count,
        "matched_missing_share": (
            float(matched_missing_count) / float(total_missing_count) if total_missing_count else 0.0
        ),
    }


def _matched_weight_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_weight: float,
) -> dict[str, object]:
    matched_missing_weight = sum(max(float(item["hit"]["score"]), 0.0) for item in items)
    return {
        "matched_missing_weight": matched_missing_weight,
        "total_missing_weight": total_missing_weight,
        "matched_missing_share": (
            float(matched_missing_weight) / float(total_missing_weight) if total_missing_weight else 0.0
        ),
    }


def _score_summary(rows: list[dict[str, object]]) -> dict[str, float | int | None]:
    if not rows:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
        }
    values = [int(row["best_seed_score"]) for row in rows]
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def _window_margin_sort_value(row: dict[str, object]) -> int:
    margin = row.get("margin")
    return int(margin) if margin is not None else -(10**18)


def _window_sort_key(row: dict[str, object]) -> tuple[int, int, int, int, int]:
    return (
        -int(row["best_seed_score"]),
        -int(row["support_count"]),
        -_window_margin_sort_value(row),
        int(row["window_start_in_seq"]),
        int(row["window_end_in_seq"]),
    )


def _window_contains(outer: dict[str, object], inner: dict[str, object]) -> bool:
    return (
        int(outer["window_start_in_seq"]) <= int(inner["window_start_in_seq"])
        and int(outer["window_end_in_seq"]) >= int(inner["window_end_in_seq"])
    )


def _covered_by_kept(candidate: dict[str, object], kept_rows: list[dict[str, object]]) -> bool:
    return any(_window_contains(kept, candidate) for kept in kept_rows)


def _is_singleton_missing_margin(row: dict[str, object]) -> bool:
    return int(row["support_count"]) == 1 and (
        row.get("second_best_seed_score") is None or row.get("margin") is None
    )


def _intrinsic_window_class(
    row: dict[str, object],
    *,
    singleton_override: int,
) -> str:
    if int(row["best_seed_score"]) < singleton_override:
        return "score_lt_85"
    if int(row["support_count"]) == 1 and row.get("margin") is not None:
        return "support1_margin_present"
    if int(row["support_count"]) == 2:
        return "support2"
    if int(row["support_count"]) >= 3 and str(row.get("reject_reason", "")) == "low_support_or_margin":
        return "support3plus_low_support_or_margin"
    return "other"


def _score_lt_85_band(row: dict[str, object]) -> str:
    score = int(row["best_seed_score"])
    if score >= 80:
        return "80_84"
    if score >= 75:
        return "75_79"
    return "lt_75"


def _score_lt_75_band(row: dict[str, object]) -> str:
    score = int(row["best_seed_score"])
    if score >= 70:
        return "70_74"
    if score >= 65:
        return "65_69"
    return "lt_65"


def _task_sort_rejected_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=_window_sort_key)


def _rule_strand_key(row: dict[str, object]) -> tuple[int, str]:
    return (int(row["rule"]), str(row["strand"]))


def _build_rule_strand_objects(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_rule_strand_key(row)].append(row)
    objects: list[dict[str, object]] = []
    for key, grouped_rows in grouped.items():
        sorted_rows = _task_sort_rejected_rows(grouped_rows)
        representative_row = sorted_rows[0]
        objects.append(
            {
                "rule": key[0],
                "strand": key[1],
                "rows": sorted_rows,
                "representative_row": representative_row,
            }
        )
    return sorted(objects, key=lambda item: _window_sort_key(item["representative_row"]))


def _classify_task(
    task_index: int,
    task_rows: list[dict[str, object]],
    *,
    max_kept_windows: int,
    non_empty_score_gap: int,
    singleton_override: int,
) -> dict[str, object]:
    kept_rows = _task_sort_rejected_rows([row for row in task_rows if int(row["after_gate"]) == 1])
    rejected_rows = _task_sort_rejected_rows(
        [row for row in task_rows if int(row["before_gate"]) == 1 and int(row["after_gate"]) == 0]
    )
    if not kept_rows:
        return {
            "task_index": task_index,
            "blocker": "empty_after_gate",
            "kept_rows": kept_rows,
            "rejected_rows": rejected_rows,
            "uncovered_rejected_rows": [],
            "task_candidate_class": "",
            "representative_window": None,
            "rule_strand_objects": [],
            "rule_strand_object_map": {},
        }

    if max_kept_windows > 0 and len(kept_rows) > max_kept_windows:
        return {
            "task_index": task_index,
            "blocker": "max_kept_windows",
            "kept_rows": kept_rows,
            "rejected_rows": rejected_rows,
            "uncovered_rejected_rows": [],
            "task_candidate_class": "",
            "representative_window": None,
            "rule_strand_objects": [],
            "rule_strand_object_map": {},
        }

    best_kept = kept_rows[0]
    found_singleton_missing_margin = False
    found_singleton_override_qualified = False
    found_uncovered_candidate = False
    selected_row = None
    uncovered_rejected_rows = [
        row for row in rejected_rows if not _covered_by_kept(row, kept_rows)
    ]
    for row in rejected_rows:
        if str(row.get("reject_reason", "")) != "singleton_missing_margin":
            continue
        if not _is_singleton_missing_margin(row):
            continue
        found_singleton_missing_margin = True
        if int(row["best_seed_score"]) < singleton_override:
            continue
        found_singleton_override_qualified = True
        if _covered_by_kept(row, kept_rows):
            continue
        found_uncovered_candidate = True
        best_score_gap = int(best_kept["best_seed_score"]) - int(row["best_seed_score"])
        if best_score_gap > non_empty_score_gap:
            continue
        if selected_row is None or _window_sort_key(row) < _window_sort_key(selected_row):
            selected_row = row

    if selected_row is not None:
        blocker = "selected"
    elif not found_singleton_missing_margin:
        blocker = "no_singleton_missing_margin"
    elif not found_singleton_override_qualified:
        blocker = "singleton_override"
    elif not found_uncovered_candidate:
        blocker = "covered_by_kept"
    else:
        blocker = "score_gap"

    representative_window = None
    task_candidate_class = ""
    rule_strand_objects = _build_rule_strand_objects(uncovered_rejected_rows)
    if blocker == "no_singleton_missing_margin":
        if uncovered_rejected_rows:
            representative_window = uncovered_rejected_rows[0]
            task_candidate_class = _intrinsic_window_class(
                representative_window,
                singleton_override=singleton_override,
            )
        elif rejected_rows:
            representative_window = rejected_rows[0]
            task_candidate_class = "covered_by_kept"
        else:
            task_candidate_class = "other"

    return {
        "task_index": task_index,
        "blocker": blocker,
        "kept_rows": kept_rows,
        "rejected_rows": rejected_rows,
        "uncovered_rejected_rows": uncovered_rejected_rows,
        "task_candidate_class": task_candidate_class,
        "representative_window": representative_window,
        "rule_strand_objects": rule_strand_objects,
        "rule_strand_object_map": {
            (int(item["rule"]), str(item["strand"])): item for item in rule_strand_objects
        },
    }


def _load_tile_context(
    panel_item: dict[str, object],
    *,
    candidate_label: str,
) -> dict[str, object]:
    report_path = Path(str(panel_item["report_path"])).resolve()
    report = _load_json(report_path)
    compare_output_mode = str(report["compare_output_mode"])
    runs = dict(report["runs"])
    legacy_dir = Path(str(runs["legacy"]["output_dir"])).resolve()
    candidate_dir = Path(str(runs[candidate_label]["output_dir"])).resolve()
    debug_csv_path = Path(str(runs[candidate_label]["debug_windows_csv"])).resolve()
    legacy_output_map = sample_vs_fasim._load_output_map(legacy_dir, compare_output_mode)
    candidate_output_map = sample_vs_fasim._load_output_map(candidate_dir, compare_output_mode)
    legacy_summary = sample_vs_fasim._aggregate_output_summaries(list(legacy_output_map.values()))
    candidate_summary = sample_vs_fasim._aggregate_output_summaries(list(candidate_output_map.values()))
    legacy_rows = coverage_attr._load_output_rows(legacy_dir, compare_output_mode)
    debug_rows = coverage_attr._load_debug_rows(debug_csv_path)
    return {
        "panel_item": panel_item,
        "report_path": report_path,
        "report": report,
        "legacy_summary": legacy_summary,
        "candidate_summary": candidate_summary,
        "legacy_rows": legacy_rows,
        "debug_rows": debug_rows,
    }


def _view_subset(
    missing_items: list[dict[str, object]],
    *,
    ranked_keys: list[tuple],
    k: int | None,
) -> list[dict[str, object]]:
    if k is None:
        return missing_items
    key_set = set(ranked_keys[: min(k, len(ranked_keys))])
    return [item for item in missing_items if item["strict_key_tuple"] in key_set]


def _count_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_count: int,
) -> dict[str, object]:
    count_by_class = _class_count_template()
    for item in items:
        count_by_class[item["candidate_class"]] += 1
    matched_missing_count = len(items)
    return {
        "matched_missing_count": matched_missing_count,
        "total_missing_count": total_missing_count,
        "count_by_class": count_by_class,
        "share_by_class": _share_dict(count_by_class, matched_missing_count),
    }


def _weight_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_weight: float,
) -> dict[str, object]:
    weight_by_class = _class_weight_template()
    for item in items:
        weight_by_class[item["candidate_class"]] += max(float(item["hit"]["score"]), 0.0)
    matched_missing_weight = sum(weight_by_class.values())
    return {
        "matched_missing_weight": matched_missing_weight,
        "total_missing_weight": total_missing_weight,
        "weight_by_class": weight_by_class,
        "share_by_class": _share_dict(weight_by_class, matched_missing_weight),
    }


def _recommended_next_candidate_class(aggregate: dict[str, object]) -> str:
    weighted = aggregate["missing_hit_contribution_by_class"][WEIGHT_VIEW]["weight_by_class"]
    counts = aggregate["missing_hit_contribution_by_class"]["overall"]["count_by_class"]
    for class_name in RECOMMENDED_CLASS_ORDER:
        if float(weighted[class_name]) > 0.0 or int(counts[class_name]) > 0:
            return class_name
    return ""


def _recommended_next_candidate_object(aggregate: dict[str, object]) -> str:
    breakdown = aggregate["rule_strand_object_breakdown"]["missing_hit_contribution"]
    if (
        int(breakdown["top10_missing"]["matched_missing_count"]) > 0
        or float(breakdown[WEIGHT_VIEW]["matched_missing_weight"]) > 0.0
    ):
        return "rule_strand_dominant"
    return ""


def _score_lt_85_band_count_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_count: int,
) -> dict[str, object]:
    count_by_band = _score_lt_85_band_count_template()
    for item in items:
        band = str(item.get("score_lt_85_band", ""))
        if band in count_by_band:
            count_by_band[band] += 1
    matched_missing_count = len(items)
    return {
        "matched_missing_count": matched_missing_count,
        "total_missing_count": total_missing_count,
        "count_by_band": count_by_band,
        "share_by_band": _share_dict(count_by_band, matched_missing_count),
    }


def _score_lt_75_band_count_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_count: int,
) -> dict[str, object]:
    count_by_band = _score_lt_75_band_count_template()
    for item in items:
        band = str(item.get("score_lt_75_band", ""))
        if band in count_by_band:
            count_by_band[band] += 1
    matched_missing_count = len(items)
    return {
        "matched_missing_count": matched_missing_count,
        "total_missing_count": total_missing_count,
        "count_by_band": count_by_band,
        "share_by_band": _share_dict(count_by_band, matched_missing_count),
    }


def _score_lt_85_band_weight_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_weight: float,
) -> dict[str, object]:
    weight_by_band = _score_lt_85_band_weight_template()
    for item in items:
        band = str(item.get("score_lt_85_band", ""))
        if band in weight_by_band:
            weight_by_band[band] += max(float(item["hit"]["score"]), 0.0)
    matched_missing_weight = sum(weight_by_band.values())
    return {
        "matched_missing_weight": matched_missing_weight,
        "total_missing_weight": total_missing_weight,
        "weight_by_band": weight_by_band,
        "share_by_band": _share_dict(weight_by_band, matched_missing_weight),
    }


def _score_lt_75_band_weight_view_summary(
    items: list[dict[str, object]],
    *,
    total_missing_weight: float,
) -> dict[str, object]:
    weight_by_band = _score_lt_75_band_weight_template()
    for item in items:
        band = str(item.get("score_lt_75_band", ""))
        if band in weight_by_band:
            weight_by_band[band] += max(float(item["hit"]["score"]), 0.0)
    matched_missing_weight = sum(weight_by_band.values())
    return {
        "matched_missing_weight": matched_missing_weight,
        "total_missing_weight": total_missing_weight,
        "weight_by_band": weight_by_band,
        "share_by_band": _share_dict(weight_by_band, matched_missing_weight),
    }


def _recommended_score_lt_85_band(aggregate: dict[str, object]) -> str:
    breakdown = aggregate["score_lt_85_band_breakdown"]
    weighted = breakdown["missing_hit_contribution_by_band"][WEIGHT_VIEW]["weight_by_band"]
    counts = breakdown["missing_hit_contribution_by_band"]["overall"]["count_by_band"]
    return max(
        SCORE_LT_85_BANDS,
        key=lambda name: (
            float(weighted[name]),
            int(counts[name]),
            -SCORE_LT_85_BANDS.index(name),
        ),
    )


def _recommended_score_lt_75_band(aggregate: dict[str, object]) -> str:
    breakdown = aggregate["score_lt_75_band_breakdown"]
    top10_counts = breakdown["missing_hit_contribution_by_band"]["top10_missing"]["count_by_band"]
    weighted = breakdown["missing_hit_contribution_by_band"][WEIGHT_VIEW]["weight_by_band"]
    task_counts = breakdown["task_count_by_band"]
    if all(
        int(top10_counts[band]) == 0 and float(weighted[band]) == 0.0 and int(task_counts[band]) == 0
        for band in SCORE_LT_75_BANDS
    ):
        return ""
    return max(
        SCORE_LT_75_BANDS,
        key=lambda name: (
            int(top10_counts[name]),
            float(weighted[name]),
            int(task_counts[name]),
            -SCORE_LT_75_BANDS.index(name),
        ),
    )


def _collect_rule_strand_missing_items(
    context: dict[str, object],
    task_infos: dict[int, dict[str, object]],
    *,
    ranked_keys: list[tuple],
    missing_keys: list[tuple],
) -> dict[str, object]:
    top5_keys = set(ranked_keys[: min(5, len(ranked_keys))])
    top10_keys = set(ranked_keys[: min(10, len(ranked_keys))])
    stats_by_task: dict[int, dict[tuple[int, str], dict[str, object]]] = {}
    for task_index, info in task_infos.items():
        if info["blocker"] != "no_singleton_missing_margin":
            continue
        stats_by_task[task_index] = {}
        for item in info.get("rule_strand_objects", []):
            object_key = (int(item["rule"]), str(item["strand"]))
            stats_by_task[task_index][object_key] = {
                "task_index": task_index,
                "rule": int(item["rule"]),
                "strand": str(item["strand"]),
                "representative_row": item["representative_row"],
                "overall_missing_count": 0,
                "top5_missing_count": 0,
                "top10_missing_count": 0,
                "score_weighted_missing": 0.0,
            }

    attributed_items: list[dict[str, object]] = []
    for key in missing_keys:
        hit = context["legacy_rows"][key]
        matching_rejected = [
            row
            for row in coverage_attr._matching_windows(hit, context["debug_rows"])
            if int(row["before_gate"]) == 1 and int(row["after_gate"]) == 0
        ]
        matched_objects: dict[tuple[int, tuple[int, str]], dict[str, object]] = {}
        for row in matching_rejected:
            task_index = int(row["task_index"])
            info = task_infos.get(task_index)
            if info is None or info["blocker"] != "no_singleton_missing_margin":
                continue
            object_key = _rule_strand_key(row)
            stats = stats_by_task.get(task_index, {}).get(object_key)
            if stats is None:
                continue
            matched_objects[(task_index, object_key)] = stats
        if not matched_objects:
            continue
        best_object = min(
            matched_objects.values(),
            key=lambda item: _window_sort_key(item["representative_row"]),
        )
        best_object["overall_missing_count"] += 1
        if key in top5_keys:
            best_object["top5_missing_count"] += 1
        if key in top10_keys:
            best_object["top10_missing_count"] += 1
        best_object["score_weighted_missing"] += max(float(hit["score"]), 0.0)
        attributed_items.append(
            {
                "strict_key_tuple": key,
                "hit": hit,
                "task_index": int(best_object["task_index"]),
                "rule": int(best_object["rule"]),
                "strand": str(best_object["strand"]),
                "representative_row": best_object["representative_row"],
            }
        )

    missing_by_view = {
        "overall": attributed_items,
        "top5_missing": [item for item in attributed_items if item["strict_key_tuple"] in top5_keys],
        "top10_missing": [item for item in attributed_items if item["strict_key_tuple"] in top10_keys],
    }
    missing_by_view[WEIGHT_VIEW] = attributed_items
    return {
        "missing_by_view": missing_by_view,
        "stats_by_task": stats_by_task,
    }


def analyze_panel_candidate_classes(
    panel_summary_path: Path | str,
    *,
    candidate_label: str,
    max_kept_windows: int,
    non_empty_score_gap: int,
    singleton_override: int,
) -> dict[str, object]:
    panel_summary_path = Path(panel_summary_path).resolve()
    panel_summary = _load_json(panel_summary_path)
    selected_microanchors = list(panel_summary.get("selected_microanchors", []))

    aggregate_task_count_by_class = _class_count_template()
    aggregate_window_count_by_class = _class_count_template()
    aggregate_representative_rows: dict[str, list[dict[str, object]]] = {
        name: [] for name in CANDIDATE_CLASSES
    }
    aggregate_score_lt_85_task_count_by_band = _score_lt_85_band_count_template()
    aggregate_score_lt_85_window_count_by_band = _score_lt_85_band_count_template()
    aggregate_score_lt_85_representative_rows: dict[str, list[dict[str, object]]] = {
        name: [] for name in SCORE_LT_85_BANDS
    }
    aggregate_score_lt_75_task_count_by_band = _score_lt_75_band_count_template()
    aggregate_score_lt_75_window_count_by_band = _score_lt_75_band_count_template()
    aggregate_score_lt_75_representative_rows: dict[str, list[dict[str, object]]] = {
        name: [] for name in SCORE_LT_75_BANDS
    }
    aggregate_rule_strand_object_task_count = 0
    aggregate_rule_strand_object_count = 0
    aggregate_rule_strand_object_representative_rows: list[dict[str, object]] = []
    aggregate_rule_strand_missing_by_view: dict[str, list[dict[str, object]]] = {
        name: [] for name in COUNT_VIEWS
    }
    aggregate_rule_strand_missing_by_view[WEIGHT_VIEW] = []
    aggregate_missing_by_view: dict[str, list[dict[str, object]]] = {
        name: [] for name in COUNT_VIEWS
    }
    aggregate_missing_by_view[WEIGHT_VIEW] = []
    aggregate_score_lt_85_missing_by_view: dict[str, list[dict[str, object]]] = {
        name: [] for name in COUNT_VIEWS
    }
    aggregate_score_lt_85_missing_by_view[WEIGHT_VIEW] = []
    aggregate_score_lt_75_missing_by_view: dict[str, list[dict[str, object]]] = {
        name: [] for name in COUNT_VIEWS
    }
    aggregate_score_lt_75_missing_by_view[WEIGHT_VIEW] = []
    total_missing_count = 0
    total_missing_weight = 0.0
    total_score_lt_85_missing_count = 0
    total_score_lt_85_missing_weight = 0.0
    total_score_lt_75_missing_count = 0
    total_score_lt_75_missing_weight = 0.0
    per_tile: list[dict[str, object]] = []

    for panel_item in selected_microanchors:
        context = _load_tile_context(panel_item, candidate_label=candidate_label)
        by_task: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in context["debug_rows"]:
            by_task[int(row["task_index"])].append(row)

        task_infos: dict[int, dict[str, object]] = {}
        task_count_by_class = _class_count_template()
        window_count_by_class = _class_count_template()
        representative_rows: dict[str, list[dict[str, object]]] = {
            name: [] for name in CANDIDATE_CLASSES
        }
        score_lt_85_task_count_by_band = _score_lt_85_band_count_template()
        score_lt_85_window_count_by_band = _score_lt_85_band_count_template()
        score_lt_85_representative_rows: dict[str, list[dict[str, object]]] = {
            name: [] for name in SCORE_LT_85_BANDS
        }
        score_lt_75_task_count_by_band = _score_lt_75_band_count_template()
        score_lt_75_window_count_by_band = _score_lt_75_band_count_template()
        score_lt_75_representative_rows: dict[str, list[dict[str, object]]] = {
            name: [] for name in SCORE_LT_75_BANDS
        }
        rule_strand_object_task_count = 0
        rule_strand_object_count = 0
        rule_strand_object_representative_rows: list[dict[str, object]] = []
        for task_index, task_rows in sorted(by_task.items()):
            info = _classify_task(
                task_index,
                task_rows,
                max_kept_windows=max_kept_windows,
                non_empty_score_gap=non_empty_score_gap,
                singleton_override=singleton_override,
            )
            task_infos[task_index] = info
            if info["blocker"] != "no_singleton_missing_margin":
                continue
            if info["rule_strand_objects"]:
                rule_strand_object_task_count += 1
                rule_strand_object_count += len(info["rule_strand_objects"])
                rule_strand_object_representative_rows.extend(
                    item["representative_row"] for item in info["rule_strand_objects"]
                )
            class_name = info["task_candidate_class"] or "other"
            task_count_by_class[class_name] += 1
            if info["representative_window"] is not None:
                representative_rows[class_name].append(info["representative_window"])
                if class_name == "score_lt_85":
                    band = _score_lt_85_band(info["representative_window"])
                    score_lt_85_task_count_by_band[band] += 1
                    score_lt_85_representative_rows[band].append(info["representative_window"])
                    if band == "lt_75":
                        lt75_band = _score_lt_75_band(info["representative_window"])
                        score_lt_75_task_count_by_band[lt75_band] += 1
                        score_lt_75_representative_rows[lt75_band].append(info["representative_window"])
            for row in info["rejected_rows"]:
                row_class = _intrinsic_window_class(row, singleton_override=singleton_override)
                window_count_by_class[row_class] += 1
                if row_class == "score_lt_85":
                    band = _score_lt_85_band(row)
                    score_lt_85_window_count_by_band[band] += 1
                    if band == "lt_75":
                        score_lt_75_window_count_by_band[_score_lt_75_band(row)] += 1

        ranked_keys = sample_vs_fasim._sorted_strict_score_keys(context["legacy_summary"].strict_scores)
        missing_keys = [
            key for key in ranked_keys if key not in context["candidate_summary"].strict_keys
        ]
        total_missing_count += len(missing_keys)
        total_missing_weight += sum(
            max(float(context["legacy_summary"].strict_scores[key]), 0.0) for key in missing_keys
        )
        attributed_missing_items: list[dict[str, object]] = []
        for key in missing_keys:
            hit = context["legacy_rows"][key]
            matching_rejected = [
                row
                for row in coverage_attr._matching_windows(hit, context["debug_rows"])
                if int(row["before_gate"]) == 1 and int(row["after_gate"]) == 0
            ]
            matches: list[tuple[dict[str, object], dict[str, object]]] = []
            for row in matching_rejected:
                info = task_infos.get(int(row["task_index"]))
                if info is None or info["blocker"] != "no_singleton_missing_margin":
                    continue
                matches.append((row, info))
            if not matches:
                continue
            best_row, best_task_info = min(matches, key=lambda item: _window_sort_key(item[0]))
            attributed_missing_items.append(
                {
                    "strict_key_tuple": key,
                    "hit": hit,
                    "candidate_class": best_task_info["task_candidate_class"] or "other",
                    "task_index": int(best_row["task_index"]),
                    "score_lt_85_band": (
                        _score_lt_85_band(best_task_info["representative_window"])
                        if best_task_info["task_candidate_class"] == "score_lt_85"
                        and best_task_info["representative_window"] is not None
                        else ""
                    ),
                    "score_lt_75_band": (
                        _score_lt_75_band(best_task_info["representative_window"])
                        if best_task_info["task_candidate_class"] == "score_lt_85"
                        and best_task_info["representative_window"] is not None
                        and _score_lt_85_band(best_task_info["representative_window"]) == "lt_75"
                        else ""
                    ),
                }
            )

        missing_by_view = {
            "overall": attributed_missing_items,
            "top5_missing": _view_subset(attributed_missing_items, ranked_keys=ranked_keys, k=5),
            "top10_missing": _view_subset(attributed_missing_items, ranked_keys=ranked_keys, k=10),
        }
        missing_by_view[WEIGHT_VIEW] = attributed_missing_items
        score_lt_85_missing_by_view = {
            view: [
                item for item in missing_by_view[view] if item["candidate_class"] == "score_lt_85"
            ]
            for view in COUNT_VIEWS
        }
        score_lt_85_missing_by_view[WEIGHT_VIEW] = [
            item for item in attributed_missing_items if item["candidate_class"] == "score_lt_85"
        ]
        score_lt_75_missing_by_view = {
            view: [
                item
                for item in score_lt_85_missing_by_view[view]
                if item.get("score_lt_75_band")
            ]
            for view in COUNT_VIEWS
        }
        score_lt_75_missing_by_view[WEIGHT_VIEW] = [
            item for item in score_lt_85_missing_by_view[WEIGHT_VIEW] if item.get("score_lt_75_band")
        ]
        rule_strand_missing_payload = _collect_rule_strand_missing_items(
            context,
            task_infos,
            ranked_keys=ranked_keys,
            missing_keys=missing_keys,
        )
        rule_strand_missing_by_view = rule_strand_missing_payload["missing_by_view"]
        tile_score_lt_85_missing_count = len(score_lt_85_missing_by_view["overall"])
        tile_score_lt_85_missing_weight = sum(
            max(float(item["hit"]["score"]), 0.0)
            for item in score_lt_85_missing_by_view[WEIGHT_VIEW]
        )
        tile_score_lt_75_missing_count = len(score_lt_75_missing_by_view["overall"])
        tile_score_lt_75_missing_weight = sum(
            max(float(item["hit"]["score"]), 0.0)
            for item in score_lt_75_missing_by_view[WEIGHT_VIEW]
        )
        total_score_lt_85_missing_count += tile_score_lt_85_missing_count
        total_score_lt_85_missing_weight += tile_score_lt_85_missing_weight
        total_score_lt_75_missing_count += tile_score_lt_75_missing_count
        total_score_lt_75_missing_weight += tile_score_lt_75_missing_weight
        for class_name in CANDIDATE_CLASSES:
            aggregate_task_count_by_class[class_name] += task_count_by_class[class_name]
            aggregate_window_count_by_class[class_name] += window_count_by_class[class_name]
            aggregate_representative_rows[class_name].extend(representative_rows[class_name])
        for band in SCORE_LT_85_BANDS:
            aggregate_score_lt_85_task_count_by_band[band] += score_lt_85_task_count_by_band[band]
            aggregate_score_lt_85_window_count_by_band[band] += score_lt_85_window_count_by_band[band]
            aggregate_score_lt_85_representative_rows[band].extend(score_lt_85_representative_rows[band])
        for band in SCORE_LT_75_BANDS:
            aggregate_score_lt_75_task_count_by_band[band] += score_lt_75_task_count_by_band[band]
            aggregate_score_lt_75_window_count_by_band[band] += score_lt_75_window_count_by_band[band]
            aggregate_score_lt_75_representative_rows[band].extend(score_lt_75_representative_rows[band])
        aggregate_rule_strand_object_task_count += rule_strand_object_task_count
        aggregate_rule_strand_object_count += rule_strand_object_count
        aggregate_rule_strand_object_representative_rows.extend(rule_strand_object_representative_rows)
        for view in COUNT_VIEWS:
            aggregate_missing_by_view[view].extend(missing_by_view[view])
            aggregate_score_lt_85_missing_by_view[view].extend(score_lt_85_missing_by_view[view])
            aggregate_score_lt_75_missing_by_view[view].extend(score_lt_75_missing_by_view[view])
            aggregate_rule_strand_missing_by_view[view].extend(rule_strand_missing_by_view[view])
        aggregate_missing_by_view[WEIGHT_VIEW].extend(missing_by_view[WEIGHT_VIEW])
        aggregate_score_lt_85_missing_by_view[WEIGHT_VIEW].extend(score_lt_85_missing_by_view[WEIGHT_VIEW])
        aggregate_score_lt_75_missing_by_view[WEIGHT_VIEW].extend(score_lt_75_missing_by_view[WEIGHT_VIEW])
        aggregate_rule_strand_missing_by_view[WEIGHT_VIEW].extend(rule_strand_missing_by_view[WEIGHT_VIEW])

        per_tile.append(
            {
                "anchor_label": panel_item.get("anchor_label", ""),
                "selection_bucket_length_bp": int(panel_item.get("selection_bucket_length_bp", 0)),
                "selection_kind": panel_item.get("selection_kind", ""),
                "selection_rank": int(panel_item.get("selection_rank", 0)),
                "start_bp": int(panel_item.get("start_bp", 0)),
                "length_bp": int(panel_item.get("length_bp", 0)),
                "report_path": str(context["report_path"]),
                "task_count_by_class": task_count_by_class,
                "window_count_by_class": window_count_by_class,
                "best_seed_score_summary_by_class": {
                    class_name: _score_summary(representative_rows[class_name])
                    for class_name in CANDIDATE_CLASSES
                },
                "score_lt_85_band_breakdown": {
                    "task_count_by_band": score_lt_85_task_count_by_band,
                    "window_count_by_band": score_lt_85_window_count_by_band,
                    "best_seed_score_summary_by_band": {
                        band: _score_summary(score_lt_85_representative_rows[band])
                        for band in SCORE_LT_85_BANDS
                    },
                    "missing_hit_contribution_by_band": {
                        "overall": _score_lt_85_band_count_view_summary(
                            score_lt_85_missing_by_view["overall"],
                            total_missing_count=tile_score_lt_85_missing_count,
                        ),
                        "top5_missing": _score_lt_85_band_count_view_summary(
                            score_lt_85_missing_by_view["top5_missing"],
                            total_missing_count=min(5, tile_score_lt_85_missing_count),
                        ),
                        "top10_missing": _score_lt_85_band_count_view_summary(
                            score_lt_85_missing_by_view["top10_missing"],
                            total_missing_count=min(10, tile_score_lt_85_missing_count),
                        ),
                        WEIGHT_VIEW: _score_lt_85_band_weight_view_summary(
                            score_lt_85_missing_by_view[WEIGHT_VIEW],
                            total_missing_weight=tile_score_lt_85_missing_weight,
                        ),
                    },
                },
                "score_lt_75_band_breakdown": {
                    "task_count_by_band": score_lt_75_task_count_by_band,
                    "window_count_by_band": score_lt_75_window_count_by_band,
                    "best_seed_score_summary_by_band": {
                        band: _score_summary(score_lt_75_representative_rows[band])
                        for band in SCORE_LT_75_BANDS
                    },
                    "missing_hit_contribution_by_band": {
                        "overall": _score_lt_75_band_count_view_summary(
                            score_lt_75_missing_by_view["overall"],
                            total_missing_count=tile_score_lt_75_missing_count,
                        ),
                        "top5_missing": _score_lt_75_band_count_view_summary(
                            score_lt_75_missing_by_view["top5_missing"],
                            total_missing_count=min(5, tile_score_lt_75_missing_count),
                        ),
                        "top10_missing": _score_lt_75_band_count_view_summary(
                            score_lt_75_missing_by_view["top10_missing"],
                            total_missing_count=min(10, tile_score_lt_75_missing_count),
                        ),
                        WEIGHT_VIEW: _score_lt_75_band_weight_view_summary(
                            score_lt_75_missing_by_view[WEIGHT_VIEW],
                            total_missing_weight=tile_score_lt_75_missing_weight,
                        ),
                    },
                },
                "rule_strand_object_breakdown": {
                    "eligible_task_count": rule_strand_object_task_count,
                    "object_count": rule_strand_object_count,
                    "best_seed_score_summary": _score_summary(rule_strand_object_representative_rows),
                    "missing_hit_contribution": {
                        "overall": _matched_count_view_summary(
                            rule_strand_missing_by_view["overall"],
                            total_missing_count=len(missing_keys),
                        ),
                        "top5_missing": _matched_count_view_summary(
                            rule_strand_missing_by_view["top5_missing"],
                            total_missing_count=min(5, len(missing_keys)),
                        ),
                        "top10_missing": _matched_count_view_summary(
                            rule_strand_missing_by_view["top10_missing"],
                            total_missing_count=min(10, len(missing_keys)),
                        ),
                        WEIGHT_VIEW: _matched_weight_view_summary(
                            rule_strand_missing_by_view[WEIGHT_VIEW],
                            total_missing_weight=sum(
                                max(float(context["legacy_summary"].strict_scores[key]), 0.0)
                                for key in missing_keys
                            ),
                        ),
                    },
                },
                "missing_hit_contribution_by_class": {
                    "overall": _count_view_summary(
                        missing_by_view["overall"],
                        total_missing_count=len(missing_keys),
                    ),
                    "top5_missing": _count_view_summary(
                        missing_by_view["top5_missing"],
                        total_missing_count=min(5, len(missing_keys)),
                    ),
                    "top10_missing": _count_view_summary(
                        missing_by_view["top10_missing"],
                        total_missing_count=min(10, len(missing_keys)),
                    ),
                    WEIGHT_VIEW: _weight_view_summary(
                        missing_by_view[WEIGHT_VIEW],
                        total_missing_weight=sum(
                            max(float(context["legacy_summary"].strict_scores[key]), 0.0)
                            for key in missing_keys
                        ),
                    ),
                },
            }
        )

    aggregate = {
        "task_count_by_class": aggregate_task_count_by_class,
        "window_count_by_class": aggregate_window_count_by_class,
        "best_seed_score_summary_by_class": {
            class_name: _score_summary(aggregate_representative_rows[class_name])
            for class_name in CANDIDATE_CLASSES
        },
        "score_lt_85_band_breakdown": {
            "task_count_by_band": aggregate_score_lt_85_task_count_by_band,
            "window_count_by_band": aggregate_score_lt_85_window_count_by_band,
            "best_seed_score_summary_by_band": {
                band: _score_summary(aggregate_score_lt_85_representative_rows[band])
                for band in SCORE_LT_85_BANDS
            },
            "missing_hit_contribution_by_band": {
                "overall": _score_lt_85_band_count_view_summary(
                    aggregate_score_lt_85_missing_by_view["overall"],
                    total_missing_count=total_score_lt_85_missing_count,
                ),
                "top5_missing": _score_lt_85_band_count_view_summary(
                    aggregate_score_lt_85_missing_by_view["top5_missing"],
                    total_missing_count=min(5, total_score_lt_85_missing_count),
                ),
                "top10_missing": _score_lt_85_band_count_view_summary(
                    aggregate_score_lt_85_missing_by_view["top10_missing"],
                    total_missing_count=min(10, total_score_lt_85_missing_count),
                ),
                WEIGHT_VIEW: _score_lt_85_band_weight_view_summary(
                    aggregate_score_lt_85_missing_by_view[WEIGHT_VIEW],
                    total_missing_weight=total_score_lt_85_missing_weight,
                ),
            },
        },
        "score_lt_75_band_breakdown": {
            "task_count_by_band": aggregate_score_lt_75_task_count_by_band,
            "window_count_by_band": aggregate_score_lt_75_window_count_by_band,
            "best_seed_score_summary_by_band": {
                band: _score_summary(aggregate_score_lt_75_representative_rows[band])
                for band in SCORE_LT_75_BANDS
            },
            "missing_hit_contribution_by_band": {
                "overall": _score_lt_75_band_count_view_summary(
                    aggregate_score_lt_75_missing_by_view["overall"],
                    total_missing_count=total_score_lt_75_missing_count,
                ),
                "top5_missing": _score_lt_75_band_count_view_summary(
                    aggregate_score_lt_75_missing_by_view["top5_missing"],
                    total_missing_count=min(5, total_score_lt_75_missing_count),
                ),
                "top10_missing": _score_lt_75_band_count_view_summary(
                    aggregate_score_lt_75_missing_by_view["top10_missing"],
                    total_missing_count=min(10, total_score_lt_75_missing_count),
                ),
                WEIGHT_VIEW: _score_lt_75_band_weight_view_summary(
                    aggregate_score_lt_75_missing_by_view[WEIGHT_VIEW],
                    total_missing_weight=total_score_lt_75_missing_weight,
                ),
            },
        },
        "rule_strand_object_breakdown": {
            "eligible_task_count": aggregate_rule_strand_object_task_count,
            "object_count": aggregate_rule_strand_object_count,
            "best_seed_score_summary": _score_summary(aggregate_rule_strand_object_representative_rows),
            "missing_hit_contribution": {
                "overall": _matched_count_view_summary(
                    aggregate_rule_strand_missing_by_view["overall"],
                    total_missing_count=total_missing_count,
                ),
                "top5_missing": _matched_count_view_summary(
                    aggregate_rule_strand_missing_by_view["top5_missing"],
                    total_missing_count=min(5, total_missing_count),
                ),
                "top10_missing": _matched_count_view_summary(
                    aggregate_rule_strand_missing_by_view["top10_missing"],
                    total_missing_count=min(10, total_missing_count),
                ),
                WEIGHT_VIEW: _matched_weight_view_summary(
                    aggregate_rule_strand_missing_by_view[WEIGHT_VIEW],
                    total_missing_weight=total_missing_weight,
                ),
            },
        },
        "missing_hit_contribution_by_class": {
            "overall": _count_view_summary(
                aggregate_missing_by_view["overall"],
                total_missing_count=total_missing_count,
            ),
            "top5_missing": _count_view_summary(
                aggregate_missing_by_view["top5_missing"],
                total_missing_count=min(5, total_missing_count),
            ),
            "top10_missing": _count_view_summary(
                aggregate_missing_by_view["top10_missing"],
                total_missing_count=min(10, total_missing_count),
            ),
            WEIGHT_VIEW: _weight_view_summary(
                aggregate_missing_by_view[WEIGHT_VIEW],
                total_missing_weight=total_missing_weight,
            ),
        },
    }

    summary = {
        "panel_summary": str(panel_summary_path),
        "candidate_label": candidate_label,
        "selector_config": {
            "max_kept_windows": max_kept_windows,
            "non_empty_score_gap": non_empty_score_gap,
            "singleton_override": singleton_override,
        },
        "tile_count": len(selected_microanchors),
        "aggregate": aggregate,
        "recommended_next_candidate_class": _recommended_next_candidate_class(aggregate),
        "recommended_next_candidate_object": _recommended_next_candidate_object(aggregate),
        "recommended_score_lt_85_band": _recommended_score_lt_85_band(aggregate),
        "recommended_score_lt_75_band": _recommended_score_lt_75_band(aggregate),
        "per_tile": per_tile,
    }
    return summary


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Selector Candidate Classes",
        "",
        f"- panel_summary: {summary['panel_summary']}",
        f"- candidate_label: {summary['candidate_label']}",
        f"- recommended_next_candidate_class: {summary['recommended_next_candidate_class'] or 'n/a'}",
        f"- recommended_next_candidate_object: {summary['recommended_next_candidate_object'] or 'n/a'}",
        f"- recommended_score_lt_85_band: {summary['recommended_score_lt_85_band'] or 'n/a'}",
        f"- recommended_score_lt_75_band: {summary['recommended_score_lt_75_band'] or 'n/a'}",
        "",
        "## Task Counts",
        "",
        "| class | tasks | windows |",
        "| --- | ---: | ---: |",
    ]
    aggregate = summary["aggregate"]
    for class_name in CANDIDATE_CLASSES:
        lines.append(
            f"| {class_name} | {aggregate['task_count_by_class'][class_name]} | {aggregate['window_count_by_class'][class_name]} |"
        )
    lines.extend(
        [
            "",
            "## score_lt_85 Band Breakdown",
            "",
            "| band | tasks | windows | overall_missing | score_weighted_missing |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    band_breakdown = aggregate["score_lt_85_band_breakdown"]
    for band in SCORE_LT_85_BANDS:
        lines.append(
            f"| {band} | {band_breakdown['task_count_by_band'][band]} | "
            f"{band_breakdown['window_count_by_band'][band]} | "
            f"{band_breakdown['missing_hit_contribution_by_band']['overall']['count_by_band'][band]} | "
            f"{band_breakdown['missing_hit_contribution_by_band'][WEIGHT_VIEW]['weight_by_band'][band]:.12g} |"
        )
    lines.extend(
        [
            "",
            "## score_lt_75 Band Breakdown",
            "",
            "| band | tasks | windows | overall_missing | score_weighted_missing |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lt75_breakdown = aggregate["score_lt_75_band_breakdown"]
    for band in SCORE_LT_75_BANDS:
        lines.append(
            f"| {band} | {lt75_breakdown['task_count_by_band'][band]} | "
            f"{lt75_breakdown['window_count_by_band'][band]} | "
            f"{lt75_breakdown['missing_hit_contribution_by_band']['overall']['count_by_band'][band]} | "
            f"{lt75_breakdown['missing_hit_contribution_by_band'][WEIGHT_VIEW]['weight_by_band'][band]:.12g} |"
        )
    object_breakdown = aggregate["rule_strand_object_breakdown"]
    lines.extend(
        [
            "",
            "## Rule/Strand Object Breakdown",
            "",
            f"- eligible_task_count: {object_breakdown['eligible_task_count']}",
            f"- object_count: {object_breakdown['object_count']}",
            f"- overall_missing: {object_breakdown['missing_hit_contribution']['overall']['matched_missing_count']}",
            f"- top10_missing: {object_breakdown['missing_hit_contribution']['top10_missing']['matched_missing_count']}",
            f"- score_weighted_missing: {object_breakdown['missing_hit_contribution'][WEIGHT_VIEW]['matched_missing_weight']:.12g}",
            "",
            "## Matched Missing Hits",
            "",
            "| class | overall | top5_missing | top10_missing | score_weighted_missing |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for class_name in CANDIDATE_CLASSES:
        lines.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    str(aggregate["missing_hit_contribution_by_class"]["overall"]["count_by_class"][class_name]),
                    str(aggregate["missing_hit_contribution_by_class"]["top5_missing"]["count_by_class"][class_name]),
                    str(aggregate["missing_hit_contribution_by_class"]["top10_missing"]["count_by_class"][class_name]),
                    f"{aggregate['missing_hit_contribution_by_class'][WEIGHT_VIEW]['weight_by_class'][class_name]:.12g}",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify the next candidate classes behind non-empty no-singleton selector blocker tasks.",
    )
    parser.add_argument("--panel-summary", required=True, help="panel summary.json with selected_microanchors")
    parser.add_argument(
        "--candidate-label",
        default="deferred_exact_minimal_v2_selective_fallback",
        help="candidate run label to analyze",
    )
    parser.add_argument("--max-kept-windows", default=2, type=int)
    parser.add_argument("--non-empty-score-gap", default=6, type=int)
    parser.add_argument("--singleton-override", default=85, type=int)
    parser.add_argument("--output-dir", required=True, help="output directory")
    args = parser.parse_args()

    summary = analyze_panel_candidate_classes(
        args.panel_summary,
        candidate_label=args.candidate_label,
        max_kept_windows=args.max_kept_windows,
        non_empty_score_gap=args.non_empty_score_gap,
        singleton_override=args.singleton_override,
    )

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
