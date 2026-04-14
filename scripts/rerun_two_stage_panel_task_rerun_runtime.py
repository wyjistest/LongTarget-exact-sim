#!/usr/bin/env python3
import argparse
import concurrent.futures
import copy
import json
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


def _selected_tasks_filename(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}_{item['selection_bucket_length_bp']}_"
        f"{item['selection_kind']}_{item['start_bp']}_{item['length_bp']}.tsv"
    )


def _tile_key(item: dict[str, object]) -> str:
    return (
        f"{item['anchor_label']}|"
        f"{int(item['selection_bucket_length_bp'])}|"
        f"{item['selection_kind']}|"
        f"{int(item['start_bp'])}|"
        f"{int(item['length_bp'])}"
    )


def _selected_tasks_by_tile(replay_summary: dict[str, object], budget: int) -> dict[str, list[dict[str, object]]]:
    for payload in replay_summary.get("budgets", []):
        if int(payload.get("budget", -1)) != budget:
            continue
        selected_by_tile: dict[str, list[dict[str, object]]] = {}
        for item in payload["aggregate"].get("selected_tasks", []):
            selected_by_tile.setdefault(str(item["tile_key"]), []).append(item)
        return selected_by_tile
    raise RuntimeError(f"budget {budget} missing from replay summary")


def _write_selected_tasks_tsv(path: Path, selected_tasks: list[dict[str, object]]) -> None:
    header = "\t".join(
        [
            "fragment_index",
            "fragment_start_in_seq",
            "fragment_end_in_seq",
            "reverse_mode",
            "parallel_mode",
            "strand",
            "rule",
        ]
    )
    lines = [header]
    for item in selected_tasks:
        task_key = item["task_key"]
        lines.append(
            "\t".join(
                [
                    str(int(task_key["fragment_index"])),
                    str(int(task_key["fragment_start_in_seq"])),
                    str(int(task_key["fragment_end_in_seq"])),
                    str(int(task_key["reverse_mode"])),
                    str(int(task_key["parallel_mode"])),
                    str(task_key["strand"]),
                    str(int(task_key["rule"])),
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_tile_command(
    *,
    panel_item: dict[str, object],
    candidate_run_label: str,
    selected_tasks_path: Path,
    longtarget: Path,
    tile_output_dir: Path,
) -> list[str]:
    original_report_path = Path(str(panel_item["report_path"])).resolve()
    original_report = _load_json(original_report_path)
    inputs = dict(original_report.get("inputs", {}))
    reject_defaults = dict(original_report.get("reject_defaults", {}))
    dna_path = _resolve_existing_path(str(panel_item["shard_path"]))
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
        "legacy",
        "--run-label",
        candidate_run_label,
        "--run-env",
        f"{candidate_run_label}:LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH={selected_tasks_path}",
    ]
    strand = str(inputs.get("strand", ""))
    if strand:
        cmd.extend(["--strand", strand])
    return cmd


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Panel Task Rerun Runtime",
        "",
        f"- source_panel_summary: {summary['source_panel_summary']}",
        f"- replay_summary: {summary['replay_summary']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- task_rerun_budget: {summary['task_rerun_budget']}",
        f"- selected_tile_count: {summary['selected_tile_count']}",
        f"- selected_task_count_total: {summary['selected_task_count_total']}",
        f"- rerun_strategy: {summary['rerun_strategy']}",
        "",
        "## Tiles",
        "",
        "| anchor | bucket_bp | selection_kind | start_bp | length_bp | selected_tasks | report_path |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for item in summary["selected_microanchors"]:
        lines.append(
            f"| {item['anchor_label']} | {item['selection_bucket_length_bp']} | {item['selection_kind']} | "
            f"{item['start_bp']} | {item['length_bp']} | {item['task_rerun_selected_task_count']} | {item['report_path']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_dry_run_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Panel Task Rerun Runtime (Dry Run)",
        "",
        f"- source_panel_summary: {report['source_panel_summary']}",
        f"- replay_summary: {report['replay_summary']}",
        f"- candidate_run_label: {report['candidate_run_label']}",
        f"- task_rerun_budget: {report['task_rerun_budget']}",
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
        description="Reuse a fixed selected-tile panel while injecting per-tile task-rerun selections from offline replay.",
    )
    parser.add_argument("--panel-summary", required=True, help="panel summary.json containing selected_microanchors")
    parser.add_argument("--replay-summary", required=True, help="task-level rerun replay summary.json")
    parser.add_argument("--budget", required=True, type=int, help="global task-rerun budget to materialize")
    parser.add_argument("--output-dir", required=True, help="output directory for rerun or dry-run reports")
    parser.add_argument("--longtarget", default=str(ROOT / "longtarget_cuda"), help="path to LongTarget binary")
    parser.add_argument(
        "--candidate-run-label",
        default="",
        help="candidate run label to rerun (defaults to deferred_exact_minimal_v3_task_rerun_budget{budget})",
    )
    parser.add_argument("--max-workers", default=2, type=int, help="parallel tile rerun workers")
    parser.add_argument("--dry-run", action="store_true", help="write command preview without executing reruns")
    args = parser.parse_args()

    panel_summary_path = Path(args.panel_summary).resolve()
    replay_summary_path = Path(args.replay_summary).resolve()
    output_dir = Path(args.output_dir).resolve()
    longtarget = Path(args.longtarget)
    if not longtarget.is_absolute():
        longtarget = (ROOT / longtarget).resolve()

    panel_summary = _load_json(panel_summary_path)
    replay_summary = _load_json(replay_summary_path)
    selected_microanchors = list(panel_summary.get("selected_microanchors", []))
    selected_by_tile = _selected_tasks_by_tile(replay_summary, int(args.budget))
    candidate_run_label = args.candidate_run_label or f"deferred_exact_minimal_v3_task_rerun_budget{int(args.budget)}"
    if args.max_workers <= 0:
        raise RuntimeError("--max-workers must be > 0")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_tasks_root = output_dir / "task_rerun_selected_tasks"
    selected_tasks_root.mkdir(parents=True, exist_ok=True)

    commands: list[list[str]] = []
    selected_task_count_total = 0
    for panel_item in selected_microanchors:
        tile_output_dir = output_dir / "tiles" / _tile_name(panel_item)
        tile_selected_tasks = selected_by_tile.get(_tile_key(panel_item), [])
        selected_task_count_total += len(tile_selected_tasks)
        selected_tasks_path = selected_tasks_root / _selected_tasks_filename(panel_item)
        _write_selected_tasks_tsv(selected_tasks_path, tile_selected_tasks)
        commands.append(
            _build_tile_command(
                panel_item=panel_item,
                candidate_run_label=candidate_run_label,
                selected_tasks_path=selected_tasks_path,
                longtarget=longtarget,
                tile_output_dir=tile_output_dir,
            )
        )

    if args.dry_run:
        dry_run_report = {
            "source_panel_summary": str(panel_summary_path),
            "replay_summary": str(replay_summary_path),
            "candidate_run_label": candidate_run_label,
            "task_rerun_budget": int(args.budget),
            "selected_tile_count": len(selected_microanchors),
            "selected_task_count_total": selected_task_count_total,
            "commands": commands,
        }
        dry_run_path = output_dir / "dry_run.json"
        dry_run_path.write_text(json.dumps(dry_run_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (output_dir / "dry_run.md").write_text(_render_dry_run_markdown(dry_run_report), encoding="utf-8")
        print(dry_run_path)
        return 0

    def run_tile(panel_item: dict[str, object]) -> dict[str, object]:
        tile_output_dir = output_dir / "tiles" / _tile_name(panel_item)
        tile_selected_tasks = selected_by_tile.get(_tile_key(panel_item), [])
        selected_tasks_path = selected_tasks_root / _selected_tasks_filename(panel_item)
        cmd = _build_tile_command(
            panel_item=panel_item,
            candidate_run_label=candidate_run_label,
            selected_tasks_path=selected_tasks_path,
            longtarget=longtarget,
            tile_output_dir=tile_output_dir,
        )
        subprocess.run(
            cmd,
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report_path = tile_output_dir / "report.json"
        report = _load_json(report_path)
        updated_item = copy.deepcopy(panel_item)
        updated_item["report_path"] = str(report_path)
        updated_item["runs"] = report["runs"]
        updated_item["comparisons_vs_legacy"] = report["comparisons_vs_legacy"]
        updated_item["task_rerun_selected_tasks_path"] = str(selected_tasks_path)
        updated_item["task_rerun_selected_task_count"] = len(tile_selected_tasks)
        return updated_item

    keyed_items = [
        (
            (
                item["anchor_label"],
                item["selection_bucket_length_bp"],
                item["selection_kind"],
                item["selection_rank"],
                item["start_bp"],
                item["length_bp"],
            ),
            item,
        )
        for item in selected_microanchors
    ]
    updated_by_key: dict[tuple[object, ...], dict[str, object]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_map = {executor.submit(run_tile, item): key for key, item in keyed_items}
        for future in concurrent.futures.as_completed(future_map):
            updated_by_key[future_map[future]] = future.result()

    summary = {
        "source_panel_summary": str(panel_summary_path),
        "replay_summary": str(replay_summary_path),
        "compare_output_mode": panel_summary.get("compare_output_mode", "lite"),
        "prefilter_backend": panel_summary.get("prefilter_backend", "prealign_cuda"),
        "gated_run_label": candidate_run_label,
        "candidate_run_label": candidate_run_label,
        "task_rerun_budget": int(args.budget),
        "heavy_anchors": panel_summary.get("heavy_anchors", []),
        "tile_specs": panel_summary.get("tile_specs", []),
        "selected_microanchors": [updated_by_key[key] for key, _ in keyed_items],
        "selection_shortfalls": panel_summary.get("selection_shortfalls", []),
        "selected_tile_count": len(selected_microanchors),
        "selected_task_count_total": selected_task_count_total,
        "rerun_strategy": "reuse_panel_selected_microanchors_with_task_rerun_selected_tasks",
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
