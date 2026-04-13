#!/usr/bin/env python3
import argparse
import dataclasses
import hashlib
import json
import shutil
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
RUN_LABELS = (
    "legacy",
    "deferred_exact",
    "deferred_exact_minimal_v1",
    "deferred_exact_minimal_v2",
    "deferred_exact_minimal_v2_selective_fallback",
)
DEFAULT_RUN_LABELS = ("legacy", "deferred_exact", "deferred_exact_minimal_v1")


@dataclasses.dataclass(frozen=True)
class ThresholdModeRun:
    label: str
    threshold_mode: str
    reject_mode: str
    wall_seconds: float
    internal_seconds: float
    prefilter_backend: str
    prefilter_hits: int
    refine_window_count: int
    refine_total_bp: int
    tasks_with_any_seed: int
    tasks_with_any_refine_window_before_gate: int
    tasks_with_any_refine_window_after_gate: int
    threshold_invoked: int
    threshold_skipped_no_seed: int
    threshold_skipped_no_refine_window: int
    threshold_skipped_after_gate: int
    threshold_batch_count: int
    threshold_batch_tasks_total: int
    threshold_batch_size_mean: float
    threshold_batch_size_max: int
    threshold_batched_seconds: float
    windows_before_gate: int
    windows_after_gate: int
    singleton_rescued_windows: int
    singleton_rescued_tasks: int
    singleton_rescue_bp_total: int
    selective_fallback_enabled: int
    selective_fallback_triggered_tasks: int
    selective_fallback_non_empty_triggered_tasks: int
    selective_fallback_selected_windows: int
    selective_fallback_selected_bp_total: int
    output_dir: str
    stderr_path: str
    output_mode: str
    output_files: list[str]
    line_count: int
    output_sha256: str
    normalized_output_sha256: str
    debug_windows_csv: str


def _parse_metrics(stderr_path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("benchmark.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        metrics[key[len("benchmark."):]] = value
    return metrics


def _metric_str(metrics: dict[str, str], key: str, *, default: str = "") -> str:
    value = metrics.get(key)
    return default if value is None or value == "" else value


def _metric_int(metrics: dict[str, str], key: str, *, default: int = 0) -> int:
    value = metrics.get(key)
    return default if value is None or value == "" else int(value)


def _metric_float(metrics: dict[str, str], key: str, *, default: float = 0.0) -> float:
    value = metrics.get(key)
    return default if value is None or value == "" else float(value)


def _normalized_output_sha256(dir_path: Path, compare_output_mode: str) -> str:
    files = sorted(dir_path.glob(sample_vs_fasim._output_glob(compare_output_mode)))
    if not files:
        return "n/a"

    h = hashlib.sha256()
    for path in files:
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        with path.open("r", encoding="utf-8", errors="replace") as f:
            header = f.readline().rstrip("\n")
            rows = sorted(
                line.rstrip("\n")
                for line in f
                if line.strip() and not line.startswith("#")
            )
        h.update(header.encode("utf-8"))
        h.update(b"\n")
        for row in rows:
            h.update(row.encode("utf-8"))
            h.update(b"\n")
    return h.hexdigest()


def _strict_key_dict(key: tuple) -> dict[str, object]:
    return {
        "query_start": key[0],
        "query_end": key[1],
        "start_in_genome": key[2],
        "end_in_genome": key[3],
        "strand": key[4],
        "rule": key[5],
    }


def _tolerant_equal(
    legacy_summary: sample_vs_fasim.OutputSummary,
    candidate_summary: sample_vs_fasim.OutputSummary,
    *,
    tolerance: float = SCORE_TOLERANCE,
) -> bool:
    if legacy_summary.strict_keys != candidate_summary.strict_keys:
        return False
    for key in legacy_summary.strict_keys:
        legacy_score = legacy_summary.strict_scores.get(key)
        candidate_score = candidate_summary.strict_scores.get(key)
        if legacy_score is None or candidate_score is None:
            return False
        if abs(candidate_score - legacy_score) > tolerance:
            return False
    return True


def _first_diff_examples(
    legacy_summary: sample_vs_fasim.OutputSummary,
    candidate_summary: sample_vs_fasim.OutputSummary,
    *,
    max_examples: int = 10,
    tolerance: float = SCORE_TOLERANCE,
) -> dict[str, list[dict[str, object]]]:
    missing_in_candidate = [
        _strict_key_dict(key)
        for key in sorted(legacy_summary.strict_keys - candidate_summary.strict_keys)[:max_examples]
    ]
    missing_in_legacy = [
        _strict_key_dict(key)
        for key in sorted(candidate_summary.strict_keys - legacy_summary.strict_keys)[:max_examples]
    ]
    score_changed: list[dict[str, object]] = []
    for key in sorted(legacy_summary.strict_keys & candidate_summary.strict_keys):
        legacy_score = legacy_summary.strict_scores.get(key)
        candidate_score = candidate_summary.strict_scores.get(key)
        if legacy_score is None or candidate_score is None:
            continue
        if abs(candidate_score - legacy_score) <= tolerance:
            continue
        score_changed.append(
            {
                **_strict_key_dict(key),
                "legacy_score": legacy_score,
                "candidate_score": candidate_score,
                "score_delta": candidate_score - legacy_score,
            }
        )
        if len(score_changed) >= max_examples:
            break
    return {
        "missing_in_candidate": missing_in_candidate,
        "missing_in_legacy": missing_in_legacy,
        "score_changed": score_changed,
    }


def _comparison_against_legacy(
    legacy_dir: Path,
    cand_dir: Path,
    compare_output_mode: str,
) -> dict[str, object]:
    comparison, legacy_summary, candidate_summary = sample_vs_fasim._compare_output_mode(
        legacy_dir,
        cand_dir,
        compare_output_mode,
    )
    raw_legacy = sample_vs_fasim._aggregate_output_sha256(legacy_dir, compare_output_mode)
    raw_cand = sample_vs_fasim._aggregate_output_sha256(cand_dir, compare_output_mode)
    norm_legacy = _normalized_output_sha256(legacy_dir, compare_output_mode)
    norm_cand = _normalized_output_sha256(cand_dir, compare_output_mode)
    comparison["raw_equal"] = raw_legacy == raw_cand
    comparison["normalized_equal"] = norm_legacy == norm_cand
    comparison["tolerant_equal"] = _tolerant_equal(legacy_summary, candidate_summary)
    if comparison["raw_equal"]:
        comparison["difference_class"] = "none"
    elif comparison["normalized_equal"]:
        comparison["difference_class"] = "ordering_or_format_only"
    else:
        comparison["difference_class"] = "content_diff"
    comparison["first_diff_examples"] = _first_diff_examples(legacy_summary, candidate_summary)
    comparison["legacy_output_sha256"] = raw_legacy
    comparison["candidate_output_sha256"] = raw_cand
    comparison["legacy_normalized_output_sha256"] = norm_legacy
    comparison["candidate_normalized_output_sha256"] = norm_cand
    return comparison


def _summarize_output_dir(dir_path: Path, compare_output_mode: str) -> tuple[sample_vs_fasim.OutputSummary, str, str]:
    output_map = sample_vs_fasim._load_output_map(dir_path, compare_output_mode)
    summary = sample_vs_fasim._aggregate_output_summaries(list(output_map.values()))
    raw_sha256 = sample_vs_fasim._aggregate_output_sha256(dir_path, compare_output_mode)
    normalized_sha256 = _normalized_output_sha256(dir_path, compare_output_mode)
    return summary, raw_sha256, normalized_sha256


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare LongTarget two-stage legacy vs deferred threshold modes on one shared input.",
    )
    parser.add_argument("--dna", default="testDNA.fa")
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", default=0, type=int)
    parser.add_argument("--strand", default="", help="optional: pass to LongTarget -t")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "two_stage_threshold_modes"),
        help="work directory for inputs, outputs, logs, and report.json",
    )
    parser.add_argument(
        "--longtarget",
        default=str(ROOT / "longtarget_cuda"),
        help="path to LongTarget binary",
    )
    parser.add_argument(
        "--compare-output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
        help="shared output schema for all threshold-mode runs",
    )
    parser.add_argument("--prefilter-topk", default=64, type=int)
    parser.add_argument("--peak-suppress-bp", default=5, type=int)
    parser.add_argument("--score-floor-delta", default=0, type=int)
    parser.add_argument("--refine-pad-bp", default=64, type=int)
    parser.add_argument("--refine-merge-gap-bp", default=32, type=int)
    parser.add_argument("--min-peak-score", default=80, type=int)
    parser.add_argument("--min-support", default=2, type=int)
    parser.add_argument("--min-margin", default=6, type=int)
    parser.add_argument("--strong-score-override", default=100, type=int)
    parser.add_argument("--max-windows-per-task", default=8, type=int)
    parser.add_argument("--max-bp-per-task", default=32768, type=int)
    parser.add_argument(
        "--run-label",
        action="append",
        choices=RUN_LABELS,
        default=None,
        help="optional: limit execution to one or more specific run labels",
    )
    parser.add_argument(
        "--debug-window-run-label",
        action="append",
        choices=RUN_LABELS,
        default=None,
        help="optional: emit LONGTARGET_TWO_STAGE_DEBUG_WINDOWS_CSV for selected run labels",
    )
    args = parser.parse_args()

    work_dir = Path(args.work_dir).resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    dna_src = Path(args.dna)
    if not dna_src.is_absolute():
        dna_src = (ROOT / dna_src).resolve()
    rna_src = Path(args.rna)
    if not rna_src.is_absolute():
        rna_src = (ROOT / rna_src).resolve()
    longtarget = Path(args.longtarget)
    if not longtarget.is_absolute():
        longtarget = (ROOT / longtarget).resolve()
    if not dna_src.exists():
        raise RuntimeError(f"missing DNA fasta: {dna_src}")
    if not rna_src.exists():
        raise RuntimeError(f"missing RNA fasta: {rna_src}")
    if not longtarget.exists():
        raise RuntimeError(f"missing LongTarget binary: {longtarget}")

    inputs_dir = work_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dna = inputs_dir / dna_src.name
    rna = inputs_dir / rna_src.name
    shutil.copyfile(dna_src, dna)
    shutil.copyfile(rna_src, rna)

    base_args = ["-f1", dna.name, "-f2", rna.name, "-r", str(args.rule)]
    if args.strand:
        base_args += ["-t", args.strand]

    shared_env = {
        "LONGTARGET_ENABLE_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA_REGION": "1",
        "LONGTARGET_BENCHMARK": "1",
        "LONGTARGET_OUTPUT_MODE": args.compare_output_mode,
        "LONGTARGET_TWO_STAGE": "1",
        "LONGTARGET_PREFILTER_BACKEND": "prealign_cuda",
        "LONGTARGET_PREFILTER_TOPK": str(args.prefilter_topk),
        "LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP": str(args.peak_suppress_bp),
        "LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA": str(args.score_floor_delta),
        "LONGTARGET_REFINE_PAD_BP": str(args.refine_pad_bp),
        "LONGTARGET_REFINE_MERGE_GAP_BP": str(args.refine_merge_gap_bp),
    }

    all_run_specs = [
        ("legacy", {}),
        ("deferred_exact", {"LONGTARGET_TWO_STAGE_THRESHOLD_MODE": "deferred_exact"}),
        (
            "deferred_exact_minimal_v1",
            {
                "LONGTARGET_TWO_STAGE_THRESHOLD_MODE": "deferred_exact",
                "LONGTARGET_TWO_STAGE_REJECT_MODE": "minimal_v1",
                "LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE": str(args.min_peak_score),
                "LONGTARGET_TWO_STAGE_MIN_SUPPORT": str(args.min_support),
                "LONGTARGET_TWO_STAGE_MIN_MARGIN": str(args.min_margin),
                "LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE": str(args.strong_score_override),
                "LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK": str(args.max_windows_per_task),
                "LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK": str(args.max_bp_per_task),
            },
        ),
        (
            "deferred_exact_minimal_v2",
            {
                "LONGTARGET_TWO_STAGE_THRESHOLD_MODE": "deferred_exact",
                "LONGTARGET_TWO_STAGE_REJECT_MODE": "minimal_v2",
                "LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE": str(args.min_peak_score),
                "LONGTARGET_TWO_STAGE_MIN_SUPPORT": str(args.min_support),
                "LONGTARGET_TWO_STAGE_MIN_MARGIN": str(args.min_margin),
                "LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE": str(args.strong_score_override),
                "LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK": str(args.max_windows_per_task),
                "LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK": str(args.max_bp_per_task),
            },
        ),
        (
            "deferred_exact_minimal_v2_selective_fallback",
            {
                "LONGTARGET_TWO_STAGE_THRESHOLD_MODE": "deferred_exact",
                "LONGTARGET_TWO_STAGE_REJECT_MODE": "minimal_v2",
                "LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE": str(args.min_peak_score),
                "LONGTARGET_TWO_STAGE_MIN_SUPPORT": str(args.min_support),
                "LONGTARGET_TWO_STAGE_MIN_MARGIN": str(args.min_margin),
                "LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE": str(args.strong_score_override),
                "LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK": str(args.max_windows_per_task),
                "LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK": str(args.max_bp_per_task),
                "LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK": "1",
            },
        ),
    ]
    requested_run_labels = args.run_label or list(DEFAULT_RUN_LABELS)
    debug_window_run_labels = set(args.debug_window_run_label or [])
    run_specs = [(label, env) for label, env in all_run_specs if label in requested_run_labels]
    if not run_specs:
        raise RuntimeError("no run specs selected")

    runs: dict[str, ThresholdModeRun] = {}
    for label, extra_env in run_specs:
        out_dir = work_dir / label / "output"
        stderr_path = work_dir / label / "stderr.log"
        debug_windows_csv = work_dir / label / "two_stage_windows.tsv"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        env = dict(shared_env)
        env.update(extra_env)
        if label in debug_window_run_labels:
            env["LONGTARGET_TWO_STAGE_DEBUG_WINDOWS_CSV"] = str(debug_windows_csv)
        run = sample_vs_fasim._run_checked(
            label=label,
            cmd=[str(longtarget), *base_args, "-O", str(out_dir)],
            env_overrides=env,
            stderr_path=stderr_path,
            output_dir=out_dir,
            expect_benchmark_total=True,
            cwd=inputs_dir,
        )
        metrics = _parse_metrics(stderr_path)
        summary, raw_sha256, normalized_sha256 = _summarize_output_dir(out_dir, args.compare_output_mode)
        internal_seconds = run.internal_seconds
        if internal_seconds is None:
            raise RuntimeError(f"{label} missing benchmark.total_seconds")
        debug_windows_csv_str = ""
        if label in debug_window_run_labels:
            if not debug_windows_csv.exists():
                raise RuntimeError(f"{label} requested debug windows CSV but file was not created: {debug_windows_csv}")
            debug_windows_csv_str = str(debug_windows_csv)
        runs[label] = ThresholdModeRun(
            label=label,
            threshold_mode=_metric_str(metrics, "two_stage_threshold_mode", default="legacy"),
            reject_mode=_metric_str(metrics, "two_stage_reject_mode", default="off"),
            wall_seconds=run.wall_seconds,
            internal_seconds=internal_seconds,
            prefilter_backend=_metric_str(metrics, "prefilter_backend", default="disabled"),
            prefilter_hits=_metric_int(metrics, "prefilter_hits"),
            refine_window_count=_metric_int(metrics, "refine_window_count"),
            refine_total_bp=_metric_int(metrics, "refine_total_bp"),
            tasks_with_any_seed=_metric_int(metrics, "two_stage_tasks_with_any_seed"),
            tasks_with_any_refine_window_before_gate=_metric_int(metrics, "two_stage_tasks_with_any_refine_window_before_gate"),
            tasks_with_any_refine_window_after_gate=_metric_int(metrics, "two_stage_tasks_with_any_refine_window_after_gate"),
            threshold_invoked=_metric_int(metrics, "two_stage_threshold_invoked_tasks"),
            threshold_skipped_no_seed=_metric_int(metrics, "two_stage_threshold_skipped_no_seed_tasks"),
            threshold_skipped_no_refine_window=_metric_int(metrics, "two_stage_threshold_skipped_no_refine_window_tasks"),
            threshold_skipped_after_gate=_metric_int(metrics, "two_stage_threshold_skipped_after_gate_tasks"),
            threshold_batch_count=_metric_int(metrics, "two_stage_threshold_batch_count"),
            threshold_batch_tasks_total=_metric_int(metrics, "two_stage_threshold_batch_tasks_total"),
            threshold_batch_size_mean=(
                _metric_int(metrics, "two_stage_threshold_batch_tasks_total")
                / _metric_int(metrics, "two_stage_threshold_batch_count")
                if _metric_int(metrics, "two_stage_threshold_batch_count") > 0
                else 0.0
            ),
            threshold_batch_size_max=_metric_int(metrics, "two_stage_threshold_batch_size_max"),
            threshold_batched_seconds=_metric_float(metrics, "two_stage_threshold_batched_seconds"),
            windows_before_gate=_metric_int(metrics, "two_stage_windows_before_gate"),
            windows_after_gate=_metric_int(metrics, "two_stage_windows_after_gate"),
            singleton_rescued_windows=_metric_int(metrics, "two_stage_singleton_rescued_windows"),
            singleton_rescued_tasks=_metric_int(metrics, "two_stage_singleton_rescued_tasks"),
            singleton_rescue_bp_total=_metric_int(metrics, "two_stage_singleton_rescue_bp_total"),
            selective_fallback_enabled=_metric_int(metrics, "two_stage_selective_fallback_enabled"),
            selective_fallback_triggered_tasks=_metric_int(metrics, "two_stage_selective_fallback_triggered_tasks"),
            selective_fallback_non_empty_triggered_tasks=_metric_int(metrics, "two_stage_selective_fallback_non_empty_triggered_tasks"),
            selective_fallback_selected_windows=_metric_int(metrics, "two_stage_selective_fallback_selected_windows"),
            selective_fallback_selected_bp_total=_metric_int(metrics, "two_stage_selective_fallback_selected_bp_total"),
            output_dir=str(out_dir),
            stderr_path=str(stderr_path),
            output_mode=args.compare_output_mode,
            output_files=summary.files,
            line_count=summary.line_count,
            output_sha256=raw_sha256,
            normalized_output_sha256=normalized_sha256,
            debug_windows_csv=debug_windows_csv_str,
        )

    comparisons: dict[str, dict[str, object]] = {}
    if "legacy" in runs:
        legacy_dir = Path(runs["legacy"].output_dir)
        comparisons = {
            label: _comparison_against_legacy(legacy_dir, Path(run.output_dir), args.compare_output_mode)
            for label, run in runs.items()
            if label != "legacy"
        }

    report = {
        "compare_output_mode": args.compare_output_mode,
        "work_dir": str(work_dir),
        "inputs": {
            "dna_src": str(dna_src),
            "rna_src": str(rna_src),
            "dna_basename": dna.name,
            "rna_basename": rna.name,
            "rule": args.rule,
            "strand": args.strand,
        },
        "prefilter_backend": "prealign_cuda",
        "prefilter_topk": args.prefilter_topk,
        "peak_suppress_bp": args.peak_suppress_bp,
        "score_floor_delta": args.score_floor_delta,
        "refine_pad_bp": args.refine_pad_bp,
        "refine_merge_gap_bp": args.refine_merge_gap_bp,
        "reject_defaults": {
            "min_peak_score": args.min_peak_score,
            "min_support": args.min_support,
            "min_margin": args.min_margin,
            "strong_score_override": args.strong_score_override,
            "max_windows_per_task": args.max_windows_per_task,
            "max_bp_per_task": args.max_bp_per_task,
        },
        "run_labels_requested": requested_run_labels,
        "debug_window_run_labels_requested": sorted(debug_window_run_labels),
        "runs": {label: dataclasses.asdict(run) for label, run in runs.items()},
        "comparisons_vs_legacy": comparisons,
    }

    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
