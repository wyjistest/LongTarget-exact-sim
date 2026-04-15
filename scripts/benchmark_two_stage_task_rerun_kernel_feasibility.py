#!/usr/bin/env python3
import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


SCORE_TOLERANCE = 1e-6


@dataclasses.dataclass(frozen=True)
class TaskOutputSummary:
    strict_keys: set[tuple]
    strict_scores: dict[tuple, float]
    row_count: int
    raw_sha256: str
    normalized_sha256: str


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
    return _selected_tasks_filename(item)


def _task_output_filename(item: dict[str, object]) -> str:
    return _selected_tasks_filename(item)


def _copy_selected_tasks(src: Path, dst: Path) -> int:
    rows = src.read_text(encoding="utf-8").splitlines()
    dst.write_text("\n".join(rows) + "\n", encoding="utf-8")
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def _build_tile_command(
    *,
    panel_item: dict[str, object],
    baseline_run_label: str,
    candidate_run_label: str,
    selected_tasks_path: Path,
    profile_tsv_path: Path,
    task_output_tsv_path: Path,
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
        "--run-env",
        f"{candidate_run_label}:LONGTARGET_TWO_STAGE_TASK_RERUN_TASK_OUTPUT_TSV={task_output_tsv_path}",
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


def _task_output_key(row: dict[str, str]) -> tuple[int, int, int, int, str, int]:
    return (
        int(row["QueryStart"]),
        int(row["QueryEnd"]),
        int(row["StartInGenome"]),
        int(row["EndInGenome"]),
        str(row["Strand"]),
        int(row["Rule"]),
    )


def _load_task_output_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if not line:
            continue
        values = line.split("\t")
        rows.append(dict(zip(header, values)))
    return rows


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _summarize_task_outputs(path: Path) -> dict[str, TaskOutputSummary]:
    rows = _load_task_output_rows(path)
    per_task: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        per_task.setdefault(str(row["task_key"]), []).append(row)

    summaries: dict[str, TaskOutputSummary] = {}
    for task_key, task_rows in per_task.items():
        strict_keys: set[tuple] = set()
        strict_scores: dict[tuple, float] = {}
        raw_lines: list[str] = []
        normalized_lines: list[str] = []
        for row in task_rows:
            key = _task_output_key(row)
            strict_keys.add(key)
            score = float(row["Score"])
            prev_score = strict_scores.get(key)
            if prev_score is None or score > prev_score:
                strict_scores[key] = score
            ordered = [
                row["task_key"],
                row.get("selected", ""),
                row.get("effective", ""),
                row.get("Chr", ""),
                row["StartInGenome"],
                row["EndInGenome"],
                row["Strand"],
                row["Rule"],
                row["QueryStart"],
                row["QueryEnd"],
                row["StartInSeq"],
                row["EndInSeq"],
                row["Direction"],
                row["Score"],
                row["Nt(bp)"],
                row["MeanIdentity(%)"],
                row["MeanStability"],
            ]
            raw_lines.append("\t".join(ordered))
            normalized_lines.append("\t".join(sorted(ordered[:1]) + ordered[1:]))
        summaries[task_key] = TaskOutputSummary(
            strict_keys=strict_keys,
            strict_scores=strict_scores,
            row_count=len(task_rows),
            raw_sha256=_sha256_text("\n".join(raw_lines)),
            normalized_sha256=_sha256_text("\n".join(sorted(normalized_lines))),
        )
    return summaries


def _task_output_diff_examples(
    baseline: TaskOutputSummary,
    candidate: TaskOutputSummary,
    *,
    max_examples: int = 5,
) -> dict[str, list[dict[str, object]]]:
    missing_in_candidate = []
    for key in sorted(baseline.strict_keys - candidate.strict_keys)[:max_examples]:
        missing_in_candidate.append(
            {
                "QueryStart": key[0],
                "QueryEnd": key[1],
                "StartInGenome": key[2],
                "EndInGenome": key[3],
                "Strand": key[4],
                "Rule": key[5],
            }
        )
    missing_in_baseline = []
    for key in sorted(candidate.strict_keys - baseline.strict_keys)[:max_examples]:
        missing_in_baseline.append(
            {
                "QueryStart": key[0],
                "QueryEnd": key[1],
                "StartInGenome": key[2],
                "EndInGenome": key[3],
                "Strand": key[4],
                "Rule": key[5],
            }
        )
    score_changed = []
    for key in sorted(baseline.strict_keys & candidate.strict_keys):
        baseline_score = baseline.strict_scores.get(key)
        candidate_score = candidate.strict_scores.get(key)
        if baseline_score is None or candidate_score is None:
            continue
        if abs(candidate_score - baseline_score) <= SCORE_TOLERANCE:
            continue
        score_changed.append(
            {
                "QueryStart": key[0],
                "QueryEnd": key[1],
                "StartInGenome": key[2],
                "EndInGenome": key[3],
                "Strand": key[4],
                "Rule": key[5],
                "baseline_score": baseline_score,
                "candidate_score": candidate_score,
            }
        )
        if len(score_changed) >= max_examples:
            break
    return {
        "missing_in_candidate": missing_in_candidate,
        "missing_in_baseline": missing_in_baseline,
        "score_changed": score_changed,
    }


def _task_outputs_equal(baseline: TaskOutputSummary, candidate: TaskOutputSummary) -> bool:
    if baseline.strict_keys != candidate.strict_keys:
        return False
    for key in baseline.strict_keys:
        baseline_score = baseline.strict_scores.get(key)
        candidate_score = candidate.strict_scores.get(key)
        if baseline_score is None or candidate_score is None:
            return False
        if abs(candidate_score - baseline_score) > SCORE_TOLERANCE:
            return False
    return True


def _compare_task_output_files(baseline_path: Path, candidate_path: Path) -> dict[str, object]:
    baseline = _summarize_task_outputs(baseline_path)
    candidate = _summarize_task_outputs(candidate_path)
    task_keys = sorted(set(baseline) | set(candidate))
    mismatches: list[dict[str, object]] = []
    semantic_equal_tasks = 0
    for task_key in task_keys:
        baseline_summary = baseline.get(task_key, TaskOutputSummary(set(), {}, 0, "", ""))
        candidate_summary = candidate.get(task_key, TaskOutputSummary(set(), {}, 0, "", ""))
        if _task_outputs_equal(baseline_summary, candidate_summary):
            semantic_equal_tasks += 1
            continue
        mismatches.append(
            {
                "task_key": task_key,
                "baseline_row_count": baseline_summary.row_count,
                "candidate_row_count": candidate_summary.row_count,
                "diff_examples": _task_output_diff_examples(baseline_summary, candidate_summary),
            }
        )
    return {
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "baseline_task_count": len(baseline),
        "candidate_task_count": len(candidate),
        "semantic_equal_task_count": semantic_equal_tasks,
        "semantic_mismatch_task_count": len(mismatches),
        "semantic_equivalent": len(mismatches) == 0,
        "mismatches": mismatches[:10],
    }


def _render_dry_run_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Task Rerun Kernel Feasibility (Dry Run)",
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


def _render_summary_markdown(summary: dict[str, object]) -> str:
    aggregate = dict(summary["aggregate"])
    lines = [
        "# Two-Stage Task Rerun Kernel Feasibility",
        "",
        f"- source_panel_summary: {summary['source_panel_summary']}",
        f"- baseline_run_label: {summary['baseline_run_label']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- selected_tile_count: {summary['selected_tile_count']}",
        f"- selected_task_count_total: {summary['selected_task_count_total']}",
        f"- effective_task_count_total: {aggregate['effective_task_count_total']}",
        f"- task_output_row_count_total: {aggregate['task_output_row_count_total']}",
        f"- task_output_task_count_total: {aggregate['task_output_task_count_total']}",
        "",
        "## Aggregate",
        "",
        f"- task_rerun_effective_sim_seconds_total: {aggregate['task_rerun_effective_sim_seconds_total']:.6f}",
        f"- task_rerun_refine_bp_total: {aggregate['task_rerun_refine_bp_total']}",
        "",
    ]
    comparison = summary.get("candidate_task_output_comparison")
    if isinstance(comparison, dict):
        lines.extend(
            [
                "## Candidate Comparison",
                "",
                f"- semantic_equivalent: {comparison['semantic_equivalent']}",
                f"- compared_tile_count: {comparison['compared_tile_count']}",
                f"- mismatched_tile_count: {comparison['mismatched_tile_count']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export fixed-panel task-rerun benchmark corpus and optional semantic "
            "comparison inputs for rerun exact-SIM kernel feasibility."
        ),
    )
    parser.add_argument("--panel-summary", required=True, help="runtime panel summary.json with selected_microanchors")
    parser.add_argument("--output-dir", required=True, help="output directory for feasibility export")
    parser.add_argument("--longtarget", default=str(ROOT / "longtarget_cuda"), help="path to LongTarget binary")
    parser.add_argument(
        "--baseline-run-label",
        default="deferred_exact_minimal_v3_scoreband_75_79",
        help="baseline run label to rerun alongside the task-rerun lane",
    )
    parser.add_argument(
        "--candidate-run-label",
        default="deferred_exact_minimal_v3_task_rerun_budget16",
        help="candidate task-rerun run label to export",
    )
    parser.add_argument("--max-workers", default=2, type=int, help="parallel tile workers")
    parser.add_argument("--dry-run", action="store_true", help="emit commands without executing runs")
    parser.add_argument(
        "--compare-task-output-root",
        default="",
        help="optional prototype task-output root to compare against exported CPU goldens",
    )
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
    task_outputs_root = output_dir / "task_rerun_task_outputs"
    selected_tasks_root.mkdir(parents=True, exist_ok=True)
    profiles_root.mkdir(parents=True, exist_ok=True)
    task_outputs_root.mkdir(parents=True, exist_ok=True)

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
        task_output_tsv_path = task_outputs_root / _task_output_filename(panel_item)
        tile_output_dir = output_dir / "tiles" / _tile_name(panel_item)
        cmd = _build_tile_command(
            panel_item=panel_item,
            baseline_run_label=baseline_run_label,
            candidate_run_label=candidate_run_label,
            selected_tasks_path=selected_tasks_dst,
            profile_tsv_path=profile_tsv_path,
            task_output_tsv_path=task_output_tsv_path,
            longtarget=longtarget,
            tile_output_dir=tile_output_dir,
        )
        commands.append(cmd)
        item = dict(panel_item)
        item["task_rerun_selected_tasks_path"] = str(selected_tasks_dst)
        item["task_rerun_profile_tsv"] = str(profile_tsv_path)
        item["task_rerun_task_output_tsv"] = str(task_output_tsv_path)
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
        candidate_run = dict(report["runs"][candidate_run_label])
        profile_rows = _load_profile_rows(Path(str(tile["task_rerun_profile_tsv"])))
        task_output_tsv_path = Path(str(tile["task_rerun_task_output_tsv"]))
        task_output_rows = _load_task_output_rows(task_output_tsv_path)
        task_output_summaries = _summarize_task_outputs(task_output_tsv_path)
        updated = dict(tile)
        updated["report_path"] = str(report_path)
        updated["runs"] = report["runs"]
        updated["comparisons_vs_legacy"] = report["comparisons_vs_legacy"]
        updated["profile_row_count"] = len(profile_rows)
        updated["effective_task_count"] = int(candidate_run.get("task_rerun_effective_tasks", 0))
        updated["task_rerun_refine_bp_total"] = int(candidate_run.get("task_rerun_refine_bp_total", 0))
        updated["task_rerun_effective_sim_seconds"] = float(candidate_run.get("task_rerun_effective_sim_seconds", 0.0))
        updated["task_output_row_count"] = len(task_output_rows)
        updated["task_output_task_count"] = len(task_output_summaries)
        updated["task_output_task_keys"] = sorted(task_output_summaries.keys())
        updated["task_output_tsv_sha256"] = hashlib.sha256(task_output_tsv_path.read_bytes()).hexdigest()
        return updated

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        exported_tiles = list(executor.map(run_tile, range(len(tiles))))

    aggregate = {
        "selected_task_count_total": selected_task_count_total,
        "effective_task_count_total": sum(int(tile["effective_task_count"]) for tile in exported_tiles),
        "task_rerun_refine_bp_total": sum(int(tile["task_rerun_refine_bp_total"]) for tile in exported_tiles),
        "task_rerun_effective_sim_seconds_total": sum(float(tile["task_rerun_effective_sim_seconds"]) for tile in exported_tiles),
        "task_output_row_count_total": sum(int(tile["task_output_row_count"]) for tile in exported_tiles),
        "task_output_task_count_total": sum(int(tile["task_output_task_count"]) for tile in exported_tiles),
    }

    compare_root = Path(args.compare_task_output_root).resolve() if args.compare_task_output_root else None
    candidate_task_output_comparison: dict[str, object] | None = None
    if compare_root is not None:
        comparisons: list[dict[str, object]] = []
        for tile in exported_tiles:
            baseline_path = Path(str(tile["task_rerun_task_output_tsv"]))
            candidate_path = compare_root / baseline_path.name
            if not candidate_path.exists():
                comparisons.append(
                    {
                        "baseline_path": str(baseline_path),
                        "candidate_path": str(candidate_path),
                        "semantic_equivalent": False,
                        "semantic_mismatch_task_count": -1,
                        "missing_candidate_file": True,
                    }
                )
                continue
            comparisons.append(_compare_task_output_files(baseline_path, candidate_path))
        candidate_task_output_comparison = {
            "root": str(compare_root),
            "compared_tile_count": len(comparisons),
            "mismatched_tile_count": sum(0 if item.get("semantic_equivalent") else 1 for item in comparisons),
            "semantic_equivalent": all(bool(item.get("semantic_equivalent")) for item in comparisons),
            "tile_comparisons": comparisons,
        }

    summary = {
        "source_panel_summary": str(panel_summary_path),
        "baseline_run_label": baseline_run_label,
        "candidate_run_label": candidate_run_label,
        "selected_tile_count": len(exported_tiles),
        "selected_task_count_total": selected_task_count_total,
        "selected_microanchors": exported_tiles,
        "aggregate": aggregate,
    }
    if candidate_task_output_comparison is not None:
        summary["candidate_task_output_comparison"] = candidate_task_output_comparison
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
