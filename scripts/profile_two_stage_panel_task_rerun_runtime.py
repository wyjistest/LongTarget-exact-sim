#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_existing_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def _tile_name(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}_{item['selection_bucket_length_bp']}_"
        f"{item['selection_kind']}_{item['start_bp']}_{item['length_bp']}"
    )


def _tile_key(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}|"
        f"{int(item['selection_bucket_length_bp'])}|"
        f"{item['selection_kind']}|"
        f"{int(item['start_bp'])}|"
        f"{int(item['length_bp'])}"
    )


def _selected_tasks_filename(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}_{item['selection_bucket_length_bp']}_"
        f"{item['selection_kind']}_{item['start_bp']}_{item['length_bp']}.tsv"
    )


def _profile_filename(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}_{item['selection_bucket_length_bp']}_"
        f"{item['selection_kind']}_{item['start_bp']}_{item['length_bp']}.tsv"
    )


def _copy_selected_tasks(src: Path, dst: Path) -> int:
    rows = src.read_text(encoding="utf-8").splitlines()
    dst.write_text("\n".join(rows) + "\n", encoding="utf-8")
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(float(value) for value in values)
    rank = (len(ordered) - 1) * percentile
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return ordered[low]
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _summary_stats(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "p50": _percentile(values, 0.50),
        "p90": _percentile(values, 0.90),
        "p99": _percentile(values, 0.99),
    }


def _dominant_phase(phase_totals: dict[str, float]) -> str:
    best_name = "none"
    best_value = 0.0
    for name, value in phase_totals.items():
        if float(value) > best_value:
            best_name = name
            best_value = float(value)
    return best_name


def _build_tile_command(
    *,
    panel_item: dict[str, object],
    baseline_run_label: str,
    candidate_run_label: str,
    selected_tasks_path: Path,
    profile_tsv_path: Path,
    longtarget: Path,
    tile_output_dir: Path,
) -> list[str]:
    original_report_path = Path(str(panel_item["report_path"])).resolve()
    original_report = _load_json(original_report_path)
    inputs = dict(original_report.get("inputs", {}))
    reject_defaults = dict(original_report.get("reject_defaults", {}))
    dna_path = _resolve_existing_path(str(inputs.get("dna_src", ROOT / "testDNA.fa")))
    rna_path = _resolve_existing_path(str(inputs.get("rna_src", ROOT / "H19.fa")))
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "benchmark_two_stage_threshold_modes.py"),
        "--work-dir",
        str(tile_output_dir),
        "--longtarget",
        str(longtarget),
        "--dna",
        str(dna_path),
        "--rna",
        str(rna_path),
        "--rule",
        str(inputs.get("rule", 0)),
        "--compare-output-mode",
        str(original_report.get("compare_output_mode", "lite")),
        "--prefilter-topk",
        str(original_report.get("prefilter_topk", 64)),
        "--peak-suppress-bp",
        str(original_report.get("peak_suppress_bp", 5)),
        "--score-floor-delta",
        str(original_report.get("score_floor_delta", original_report.get("score_floor_deltas", 0))),
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
        baseline_run_label,
        "--run-label",
        candidate_run_label,
        "--run-env",
        f"{candidate_run_label}:LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH={selected_tasks_path}",
        "--run-env",
        f"{candidate_run_label}:LONGTARGET_TWO_STAGE_TASK_RERUN_PROFILE_TSV={profile_tsv_path}",
    ]
    strand = str(inputs.get("strand", ""))
    if strand:
        cmd.extend(["--strand", strand])
    return cmd


def _load_profile_rows(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, object]] = []
    for line in lines[1:]:
        if not line:
            continue
        values = line.split("\t")
        rows.append(dict(zip(header, values)))
    return rows


def _tile_phase_totals(run: dict[str, object]) -> dict[str, float]:
    return {
        "selected_tasks_load_seconds": float(run.get("task_rerun_selected_tasks_load_seconds", 0.0)),
        "upgrade_seconds": float(run.get("task_rerun_upgrade_seconds", 0.0)),
        "effective_threshold_seconds": float(run.get("task_rerun_effective_threshold_seconds", 0.0)),
        "effective_sim_seconds": float(run.get("task_rerun_effective_sim_seconds", 0.0)),
        "effective_post_process_seconds": float(run.get("task_rerun_effective_post_process_seconds", 0.0)),
    }


def _render_summary_markdown(summary: dict[str, object]) -> str:
    aggregate = dict(summary["aggregate"])
    lines = [
        "# Two-Stage Task Rerun Runtime Profiling",
        "",
        f"- source_panel_summary: {summary['source_panel_summary']}",
        f"- baseline_run_label: {summary['baseline_run_label']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- selected_tile_count: {summary['selected_tile_count']}",
        f"- selected_task_count_total: {summary['selected_task_count_total']}",
        f"- effective_task_count_total: {aggregate['effective_tasks']}",
        f"- added_bp_total: {aggregate['added_bp_total']}",
        f"- dominant_phase: {aggregate['dominant_phase']}",
        "",
        "## Aggregate Phase Totals",
        "",
        "| phase | seconds |",
        "| --- | ---: |",
    ]
    for phase_name, seconds in aggregate["phase_totals"].items():
        lines.append(f"| {phase_name} | {seconds:.6f} |")
    lines.extend(
        [
            "",
            "## Aggregate Rerun Seconds",
            "",
            f"- p50: {aggregate['per_task_rerun_total_seconds']['p50']:.6f}",
            f"- p90: {aggregate['per_task_rerun_total_seconds']['p90']:.6f}",
            f"- p99: {aggregate['per_task_rerun_total_seconds']['p99']:.6f}",
            "",
        ]
    )
    return "\n".join(lines)


def _render_dry_run_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Task Rerun Runtime Profiling (Dry Run)",
        "",
        f"- source_panel_summary: {report['source_panel_summary']}",
        f"- baseline_run_label: {report['baseline_run_label']}",
        f"- candidate_run_label: {report['candidate_run_label']}",
        f"- selected_tile_count: {report['selected_tile_count']}",
        "",
        "## Commands",
        "",
    ]
    for command in report["commands"]:
        lines.append(f"- `{' '.join(command)}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile fixed-panel task-rerun runtime lanes without changing shortlist or selected tasks.",
    )
    parser.add_argument("--panel-summary", required=True, help="runtime panel summary.json with selected_microanchors")
    parser.add_argument("--output-dir", required=True, help="output directory for profiling runs")
    parser.add_argument("--longtarget", default=str(ROOT / "longtarget_cuda"), help="path to LongTarget binary")
    parser.add_argument(
        "--baseline-run-label",
        default="deferred_exact_minimal_v3_scoreband_75_79",
        help="baseline run label to rerun alongside the task-rerun lane",
    )
    parser.add_argument(
        "--candidate-run-label",
        default="deferred_exact_minimal_v3_task_rerun_budget16",
        help="candidate task-rerun run label to profile",
    )
    parser.add_argument("--max-workers", default=2, type=int, help="parallel tile profiling workers")
    parser.add_argument("--dry-run", action="store_true", help="emit commands without executing benchmark runs")
    args = parser.parse_args()

    panel_summary_path = Path(args.panel_summary).resolve()
    output_dir = Path(args.output_dir).resolve()
    longtarget = Path(args.longtarget)
    if not longtarget.is_absolute():
        longtarget = (ROOT / longtarget).resolve()
    if args.max_workers <= 0:
        raise RuntimeError("--max-workers must be > 0")

    panel_summary = _load_json(panel_summary_path)
    selected_microanchors = list(panel_summary.get("selected_microanchors", []))
    baseline_run_label = str(panel_summary.get("baseline_run_label", args.baseline_run_label) or args.baseline_run_label)
    candidate_run_label = str(panel_summary.get("candidate_run_label", args.candidate_run_label) or args.candidate_run_label)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_tasks_root = output_dir / "task_rerun_selected_tasks"
    profiles_root = output_dir / "task_rerun_profiles"
    selected_tasks_root.mkdir(parents=True, exist_ok=True)
    profiles_root.mkdir(parents=True, exist_ok=True)

    commands: list[list[str]] = []
    tiles: list[dict[str, object]] = []
    selected_task_count_total = 0
    for panel_item in selected_microanchors:
        selected_tasks_src = panel_item.get("task_rerun_selected_tasks_path")
        if not selected_tasks_src:
            raise RuntimeError(f"panel item missing task_rerun_selected_tasks_path: {_tile_key(panel_item)}")
        selected_tasks_dst = selected_tasks_root / _selected_tasks_filename(panel_item)
        selected_task_count = _copy_selected_tasks(_resolve_existing_path(str(selected_tasks_src)), selected_tasks_dst)
        selected_task_count_total += selected_task_count
        profile_tsv_path = profiles_root / _profile_filename(panel_item)
        tile_output_dir = output_dir / "tiles" / _tile_name(panel_item)
        cmd = _build_tile_command(
            panel_item=panel_item,
            baseline_run_label=baseline_run_label,
            candidate_run_label=candidate_run_label,
            selected_tasks_path=selected_tasks_dst,
            profile_tsv_path=profile_tsv_path,
            longtarget=longtarget,
            tile_output_dir=tile_output_dir,
        )
        commands.append(cmd)
        item = dict(panel_item)
        item["task_rerun_selected_tasks_path"] = str(selected_tasks_dst)
        item["task_rerun_profile_tsv"] = str(profile_tsv_path)
        item["task_rerun_selected_task_count"] = selected_task_count
        item["tile_output_dir"] = str(tile_output_dir)
        tiles.append(item)

    if args.dry_run:
        dry_run_report = {
            "source_panel_summary": str(panel_summary_path),
            "baseline_run_label": baseline_run_label,
            "candidate_run_label": candidate_run_label,
            "selected_tile_count": len(selected_microanchors),
            "selected_task_count_total": selected_task_count_total,
            "commands": commands,
        }
        dry_run_path = output_dir / "dry_run.json"
        dry_run_path.write_text(json.dumps(dry_run_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (output_dir / "dry_run.md").write_text(_render_dry_run_markdown(dry_run_report), encoding="utf-8")
        print(dry_run_path)
        return 0

    def run_tile(tile_index: int) -> dict[str, object]:
        tile = tiles[tile_index]
        cmd = commands[tile_index]
        subprocess.run(
            cmd,
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report_path = Path(tile["tile_output_dir"]) / "report.json"
        report = _load_json(report_path)
        profile_path = Path(str(tile["task_rerun_profile_tsv"]))
        profile_rows = _load_profile_rows(profile_path)
        candidate_run = dict(report["runs"][candidate_run_label])
        phase_totals = _tile_phase_totals(candidate_run)
        rerun_totals = [float(row["rerun_total_seconds"]) for row in profile_rows]
        rerun_per_kbp = [
            float(row["rerun_total_seconds"]) * 1000.0 / float(row["added_bp"])
            for row in profile_rows
            if float(row["added_bp"]) > 0.0
        ]
        updated = dict(tile)
        updated["report_path"] = str(report_path)
        updated["runs"] = report["runs"]
        updated["comparisons_vs_legacy"] = report["comparisons_vs_legacy"]
        updated["profile_row_count"] = len(profile_rows)
        updated["effective_task_count"] = int(candidate_run.get("task_rerun_effective_tasks", 0))
        updated["added_bp_total"] = int(candidate_run.get("task_rerun_refine_bp_total", 0))
        updated["phase_totals"] = phase_totals
        updated["dominant_phase"] = _dominant_phase(phase_totals)
        updated["rerun_total_seconds"] = _summary_stats(rerun_totals)
        updated["rerun_seconds_per_kbp"] = _summary_stats(rerun_per_kbp)
        return updated

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        profiled_tiles = list(executor.map(run_tile, range(len(tiles))))

    phase_totals = {
        "selected_tasks_load_seconds": 0.0,
        "upgrade_seconds": 0.0,
        "effective_threshold_seconds": 0.0,
        "effective_sim_seconds": 0.0,
        "effective_post_process_seconds": 0.0,
    }
    rerun_totals: list[float] = []
    rerun_per_kbp: list[float] = []
    effective_tasks = 0
    added_bp_total = 0
    for tile in profiled_tiles:
        effective_tasks += int(tile["effective_task_count"])
        added_bp_total += int(tile["added_bp_total"])
        for phase_name, seconds in tile["phase_totals"].items():
            phase_totals[phase_name] += float(seconds)
        profile_rows = _load_profile_rows(Path(str(tile["task_rerun_profile_tsv"])))
        rerun_totals.extend(float(row["rerun_total_seconds"]) for row in profile_rows)
        rerun_per_kbp.extend(
            float(row["rerun_total_seconds"]) * 1000.0 / float(row["added_bp"])
            for row in profile_rows
            if float(row["added_bp"]) > 0.0
        )

    total_seconds = sum(phase_totals.values())
    aggregate = {
        "selected_tasks": selected_task_count_total,
        "effective_tasks": effective_tasks,
        "added_bp_total": added_bp_total,
        "phase_totals": phase_totals,
        "phase_shares": {
            name: (seconds / total_seconds if total_seconds > 0.0 else 0.0)
            for name, seconds in phase_totals.items()
        },
        "dominant_phase": _dominant_phase(phase_totals),
        "per_task_rerun_total_seconds": _summary_stats(rerun_totals),
        "per_task_rerun_seconds_per_kbp": _summary_stats(rerun_per_kbp),
    }
    summary = {
        "source_panel_summary": str(panel_summary_path),
        "baseline_run_label": baseline_run_label,
        "candidate_run_label": candidate_run_label,
        "selected_tile_count": len(profiled_tiles),
        "selected_task_count_total": selected_task_count_total,
        "selected_microanchors": profiled_tiles,
        "aggregate": aggregate,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
