#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_two_stage_coverage_attribution as coverage_attr  # noqa: E402

COUNT_VIEWS = ("overall", "top1_missing", "top5_missing", "top10_missing")
WEIGHT_VIEW = "score_weighted_missing"


def _count_template() -> dict[str, int]:
    return {name: 0 for name in coverage_attr.ATTRIBUTION_CLASSES}


def _weight_template() -> dict[str, float]:
    return {name: 0.0 for name in coverage_attr.ATTRIBUTION_CLASSES}


def _share_dict(values: dict[str, float | int], total: float | int) -> dict[str, float]:
    if not total:
        return {name: 0.0 for name in values}
    return {name: float(value) / float(total) for name, value in values.items()}


def _group_key(item: dict[str, object]) -> tuple[str, int, str]:
    return (
        str(item["anchor_label"]),
        int(item["selection_bucket_length_bp"]),
        str(item["selection_kind"]),
    )


def _tile_sort_key(item: dict[str, object]) -> tuple[object, ...]:
    return (
        str(item["anchor_label"]),
        str(item["selection_kind"]),
        int(item["selection_bucket_length_bp"]),
        int(item.get("selection_rank", 0)),
        int(item.get("start_bp", 0)),
        int(item.get("end_bp", 0)),
        str(item.get("report_path", "")),
    )


def _select_tiles(
    selected_microanchors: list[dict[str, object]],
    *,
    selection_kinds: set[str],
    max_per_group: int,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, str], list[dict[str, object]]] = {}
    for item in selected_microanchors:
        selection_kind = str(item.get("selection_kind", ""))
        if selection_kind not in selection_kinds:
            continue
        grouped.setdefault(_group_key(item), []).append(item)
    selected: list[dict[str, object]] = []
    for key in sorted(grouped):
        group = sorted(grouped[key], key=_tile_sort_key)
        selected.extend(group[:max_per_group])
    return sorted(selected, key=_tile_sort_key)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _report_debug_csv(report: dict[str, object], *, candidate_label: str) -> str:
    runs = report.get("runs", {})
    run = runs.get(candidate_label, {}) if isinstance(runs, dict) else {}
    return str(run.get("debug_windows_csv", "") or "")


def _panel_item_debug_csv(item: dict[str, object], *, candidate_label: str) -> str:
    runs = item.get("runs", {})
    run = runs.get(candidate_label, {}) if isinstance(runs, dict) else {}
    return str(run.get("debug_windows_csv", "") or "")


def _run_candidate_debug(
    *,
    tile_output_dir: Path,
    original_report: dict[str, object],
    original_report_path: Path,
    candidate_label: str,
    longtarget: Path,
) -> tuple[Path, str]:
    inputs = dict(original_report.get("inputs", {}))
    reject_defaults = dict(original_report.get("reject_defaults", {}))
    rerun_dir = tile_output_dir / "candidate_debug_rerun"
    script_path = ROOT / "scripts" / "benchmark_two_stage_threshold_modes.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--work-dir",
        str(rerun_dir),
        "--longtarget",
        str(longtarget),
        "--dna",
        str(inputs["dna_src"]),
        "--rna",
        str(inputs["rna_src"]),
        "--rule",
        str(inputs.get("rule", 0)),
        "--compare-output-mode",
        str(original_report["compare_output_mode"]),
        "--prefilter-topk",
        str(original_report.get("prefilter_topk", 64)),
        "--peak-suppress-bp",
        str(original_report.get("peak_suppress_bp", 5)),
        "--score-floor-delta",
        str(original_report.get("score_floor_delta", 0)),
        "--refine-pad-bp",
        str(original_report.get("refine_pad_bp", 64)),
        "--refine-merge-gap-bp",
        str(original_report.get("refine_merge_gap_bp", 32)),
        "--min-peak-score",
        str(reject_defaults.get("min_peak_score", 80)),
        "--min-support",
        str(reject_defaults.get("min_support", 2)),
        "--min-margin",
        str(reject_defaults.get("min_margin", 6)),
        "--strong-score-override",
        str(reject_defaults.get("strong_score_override", 100)),
        "--max-windows-per-task",
        str(reject_defaults.get("max_windows_per_task", 8)),
        "--max-bp-per-task",
        str(reject_defaults.get("max_bp_per_task", 32768)),
        "--run-label",
        candidate_label,
        "--debug-window-run-label",
        candidate_label,
    ]
    strand = str(inputs.get("strand", ""))
    if strand:
        cmd.extend(["--strand", strand])
    subprocess.run(
        cmd,
        check=True,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rerun_report_path = rerun_dir / "report.json"
    rerun_report = _load_json(rerun_report_path)
    rerun_debug_csv = _report_debug_csv(rerun_report, candidate_label=candidate_label)
    if not rerun_debug_csv:
        raise RuntimeError(f"candidate rerun did not produce debug windows CSV for {original_report_path}")

    merged_report = dict(original_report)
    merged_runs = dict(original_report["runs"])
    merged_runs[candidate_label] = rerun_report["runs"][candidate_label]
    merged_report["runs"] = merged_runs
    merged_report["coverage_attribution_source_report"] = str(original_report_path)
    merged_report["coverage_attribution_debug_rerun_report"] = str(rerun_report_path)
    merged_report_path = tile_output_dir / "report_with_debug.json"
    merged_report_path.write_text(json.dumps(merged_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return merged_report_path, rerun_debug_csv


def _ensure_debug_report(
    *,
    tile_output_dir: Path,
    panel_item: dict[str, object],
    candidate_label: str,
    force_rerun_debug: bool,
    require_existing_debug: bool,
    longtarget: Path,
) -> tuple[Path, str]:
    original_report_path = Path(str(panel_item["report_path"])).resolve()
    original_report = _load_json(original_report_path)
    if candidate_label not in original_report.get("runs", {}):
        raise RuntimeError(f"{original_report_path} is missing candidate run {candidate_label}")

    existing_debug = _panel_item_debug_csv(panel_item, candidate_label=candidate_label) or _report_debug_csv(
        original_report,
        candidate_label=candidate_label,
    )
    if existing_debug and not force_rerun_debug:
        existing_debug_path = Path(existing_debug).resolve()
        if existing_debug_path.exists():
            return original_report_path, str(existing_debug_path)
    if require_existing_debug:
        raise RuntimeError(f"missing debug windows CSV for {original_report_path}")
    return _run_candidate_debug(
        tile_output_dir=tile_output_dir,
        original_report=original_report,
        original_report_path=original_report_path,
        candidate_label=candidate_label,
        longtarget=longtarget,
    )


def _aggregate_reports(reports: list[dict[str, object]]) -> dict[str, object]:
    aggregate: dict[str, object] = {}
    for view in COUNT_VIEWS:
        counts = _count_template()
        missing_count = 0
        for report in reports:
            view_report = report["summary"][view]
            missing_count += int(view_report["missing_count"])
            for class_name in coverage_attr.ATTRIBUTION_CLASSES:
                counts[class_name] += int(view_report["count_by_class"][class_name])
        aggregate[view] = {
            "missing_count": missing_count,
            "count_by_class": counts,
            "share_by_class": _share_dict(counts, missing_count),
        }

    weights = _weight_template()
    total_missing_weight = 0.0
    total_legacy_weight = 0.0
    for report in reports:
        weight_report = report["summary"][WEIGHT_VIEW]
        total_missing_weight += float(weight_report["total_missing_weight"])
        total_legacy_weight += float(weight_report["total_legacy_weight"])
        for class_name in coverage_attr.ATTRIBUTION_CLASSES:
            weights[class_name] += float(weight_report["weight_by_class"][class_name])
    aggregate[WEIGHT_VIEW] = {
        "total_missing_weight": total_missing_weight,
        "total_legacy_weight": total_legacy_weight,
        "weight_by_class": weights,
        "share_of_missing_weight_by_class": _share_dict(weights, total_missing_weight),
        "share_of_legacy_weight_by_class": _share_dict(weights, total_legacy_weight),
    }
    return aggregate


def _format_count_view(name: str, view: dict[str, object]) -> list[str]:
    lines = [f"## {name}", "", "| class | count | share |", "| --- | ---: | ---: |"]
    for class_name in coverage_attr.ATTRIBUTION_CLASSES:
        lines.append(
            f"| {class_name} | {int(view['count_by_class'][class_name])} | {float(view['share_by_class'][class_name]):.6f} |"
        )
    lines.append(f"| total_missing | {int(view['missing_count'])} | 1.000000 |")
    lines.append("")
    return lines


def _format_weight_view(name: str, view: dict[str, object]) -> list[str]:
    lines = [f"## {name}", "", "| class | missing_weight | share_of_missing | share_of_legacy |", "| --- | ---: | ---: | ---: |"]
    for class_name in coverage_attr.ATTRIBUTION_CLASSES:
        lines.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    f"{float(view['weight_by_class'][class_name]):.6f}",
                    f"{float(view['share_of_missing_weight_by_class'][class_name]):.6f}",
                    f"{float(view['share_of_legacy_weight_by_class'][class_name]):.6f}",
                ]
            )
            + " |"
        )
    lines.append(
        f"| totals | {float(view['total_missing_weight']):.6f} | 1.000000 | {float(view['total_missing_weight']) / float(view['total_legacy_weight']) if float(view['total_legacy_weight']) else 0.0:.6f} |"
    )
    lines.append("")
    return lines


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Coverage Attribution Panel Summary",
        "",
        f"- panel_summary: {summary['panel_summary']}",
        f"- candidate_label: {summary['candidate_label']}",
        f"- selected_tile_count: {summary['selected_tile_count']}",
        f"- force_rerun_debug: {summary['force_rerun_debug']}",
        f"- require_existing_debug: {summary['require_existing_debug']}",
        "",
        "## By Selection Kind",
        "",
        "| selection_kind | selected_tiles | inside_rejected_share_overall | inside_rejected_share_weight |",
        "| --- | ---: | ---: | ---: |",
    ]
    for selection_kind, payload in summary["by_selection_kind"].items():
        overall = payload["aggregate"]["overall"]["share_by_class"]
        weighted = payload["aggregate"]["score_weighted_missing"]["share_of_missing_weight_by_class"]
        lines.append(
            f"| {selection_kind} | {int(payload['selected_tile_count'])} | {float(overall['inside_rejected_window']):.6f} | {float(weighted['inside_rejected_window']):.6f} |"
        )
    lines.append("")
    lines.extend(_format_count_view("overall", summary["aggregate"]["overall"]))
    lines.extend(_format_count_view("top5_missing", summary["aggregate"]["top5_missing"]))
    lines.extend(_format_count_view("top10_missing", summary["aggregate"]["top10_missing"]))
    lines.extend(_format_weight_view("score_weighted_missing", summary["aggregate"]["score_weighted_missing"]))
    lines.extend(
        [
            "## Selected Tiles",
            "",
            "| anchor | bucket_bp | selection_kind | selection_rank | start_bp | end_bp | missing_strict_hits | coverage_json |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for tile in summary["selected_tiles"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(tile["anchor_label"]),
                    str(tile["selection_bucket_length_bp"]),
                    str(tile["selection_kind"]),
                    str(tile["selection_rank"]),
                    str(tile["start_bp"]),
                    str(tile["end_bp"]),
                    str(tile["missing_strict_hit_count"]),
                    str(tile["coverage_path"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run representative-tile coverage attribution for a heavy micro-anchor panel summary.",
    )
    parser.add_argument("--panel-summary", required=True, help="heavy micro-anchor summary.json path")
    parser.add_argument(
        "--output-dir",
        default="",
        help="output directory for per-tile coverage JSON and panel summary (default: <panel dir>/coverage_attribution_panel)",
    )
    parser.add_argument(
        "--candidate-label",
        default="",
        help="candidate run label to analyze; defaults to panel summary gated_run_label",
    )
    parser.add_argument(
        "--selection-kind",
        action="append",
        default=None,
        help="selection kinds to include (repeatable, default: strongest_shrink and medium_shrink)",
    )
    parser.add_argument(
        "--max-per-group",
        type=int,
        default=1,
        help="maximum representative tiles to keep per anchor x bucket x selection_kind group",
    )
    parser.add_argument(
        "--longtarget",
        default=str(ROOT / "longtarget_cuda"),
        help="LongTarget binary used only when a candidate debug rerun is needed",
    )
    parser.add_argument(
        "--force-rerun-debug",
        action="store_true",
        help="ignore existing debug_windows_csv and always rerun the candidate lane with debug enabled",
    )
    parser.add_argument(
        "--require-existing-debug",
        action="store_true",
        help="fail instead of rerunning when a selected tile is missing debug_windows_csv",
    )
    parser.add_argument(
        "--max-examples-per-class",
        default=5,
        type=int,
        help="max examples retained per attribution class in each per-tile coverage JSON",
    )
    args = parser.parse_args()

    panel_summary_path = Path(args.panel_summary).resolve()
    panel_summary = _load_json(panel_summary_path)
    candidate_label = args.candidate_label or str(panel_summary.get("gated_run_label", "deferred_exact_minimal_v2"))
    selection_kinds = set(args.selection_kind or ["strongest_shrink", "medium_shrink"])
    selected_tiles = _select_tiles(
        list(panel_summary.get("selected_microanchors", [])),
        selection_kinds=selection_kinds,
        max_per_group=args.max_per_group,
    )
    if not selected_tiles:
        raise RuntimeError("no tiles selected from panel summary")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else panel_summary_path.parent / "coverage_attribution_panel"
    output_dir.mkdir(parents=True, exist_ok=True)
    per_tile_dir = output_dir / "tiles"
    per_tile_dir.mkdir(parents=True, exist_ok=True)

    selected_tile_outputs: list[dict[str, object]] = []
    for tile in selected_tiles:
        tile_name = (
            f"{tile['anchor_label']}_{tile['selection_bucket_length_bp']}_{tile['selection_kind']}_"
            f"{tile['start_bp']}_{tile['length_bp']}"
        )
        tile_output_dir = per_tile_dir / tile_name
        tile_output_dir.mkdir(parents=True, exist_ok=True)
        analysis_report_path, debug_csv = _ensure_debug_report(
            tile_output_dir=tile_output_dir,
            panel_item=tile,
            candidate_label=candidate_label,
            force_rerun_debug=args.force_rerun_debug,
            require_existing_debug=args.require_existing_debug,
            longtarget=Path(args.longtarget).resolve(),
        )
        coverage = coverage_attr.analyze_coverage_attribution(
            analysis_report_path,
            candidate_label=candidate_label,
            debug_csv=debug_csv,
            max_examples_per_class=args.max_examples_per_class,
        )
        coverage_path = tile_output_dir / "coverage.json"
        coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        selected_tile_outputs.append(
            {
                "anchor_label": str(tile["anchor_label"]),
                "selection_bucket_length_bp": int(tile["selection_bucket_length_bp"]),
                "selection_kind": str(tile["selection_kind"]),
                "selection_rank": int(tile["selection_rank"]),
                "length_bp": int(tile["length_bp"]),
                "start_bp": int(tile["start_bp"]),
                "end_bp": int(tile["end_bp"]),
                "report_path": str(tile["report_path"]),
                "analysis_report_path": str(analysis_report_path),
                "debug_csv": str(debug_csv),
                "coverage_path": str(coverage_path),
                "missing_strict_hit_count": int(coverage["missing_strict_hit_count"]),
                "summary": coverage["summary"],
            }
        )

    coverage_reports = [_load_json(Path(item["coverage_path"])) for item in selected_tile_outputs]
    by_selection_kind: dict[str, object] = {}
    for selection_kind in sorted({item["selection_kind"] for item in selected_tile_outputs}):
        reports = [
            _load_json(Path(item["coverage_path"]))
            for item in selected_tile_outputs
            if item["selection_kind"] == selection_kind
        ]
        by_selection_kind[selection_kind] = {
            "selected_tile_count": len(reports),
            "aggregate": _aggregate_reports(reports),
        }

    summary = {
        "panel_summary": str(panel_summary_path),
        "candidate_label": candidate_label,
        "selection_kinds": sorted(selection_kinds),
        "max_per_group": args.max_per_group,
        "selected_tile_count": len(selected_tile_outputs),
        "force_rerun_debug": args.force_rerun_debug,
        "require_existing_debug": args.require_existing_debug,
        "selected_tiles": selected_tile_outputs,
        "aggregate": _aggregate_reports(coverage_reports),
        "by_selection_kind": by_selection_kind,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
