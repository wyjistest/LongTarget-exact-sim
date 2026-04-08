#!/usr/bin/env python3
import argparse
import dataclasses
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


@dataclasses.dataclass(frozen=True)
class SweepRun:
    label: str
    prefilter_backend: str
    prefilter_topk: int
    peak_suppress_bp: int
    score_floor_delta: int
    refine_pad_bp: int
    refine_merge_gap_bp: int
    wall_seconds: float
    internal_seconds: float
    prefilter_hits: int
    refine_window_count: int
    refine_total_bp: int
    stderr_path: str
    output_dir: str
    output_mode: str
    output_files: list[str]
    line_count: int
    output_sha256: str
    comparison: dict[str, object]


def _parse_int_csv(spec: str, *, flag: str, min_value: int = 0) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as e:
            raise RuntimeError(f"invalid {flag} entry: {item}") from e
        if value < min_value:
            raise RuntimeError(f"{flag} entries must be >= {min_value}: {item}")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return values


def _parse_non_negative_float(value: str, *, flag: str) -> float:
    try:
        parsed = float(value)
    except ValueError as e:
        raise RuntimeError(f"invalid {flag}: {value}") from e
    if parsed < 0:
        raise RuntimeError(f"{flag} must be >= 0: {value}")
    return parsed


def _sanitize_label(topk: int, suppress_bp: int, score_floor_delta: int, refine_pad_bp: int, refine_merge_gap_bp: int) -> str:
    return (
        f"two_stage_topk_{topk}_suppress_{suppress_bp}"
        f"_delta_{score_floor_delta}_pad_{refine_pad_bp}_merge_{refine_merge_gap_bp}"
    )


def _summarize_output_dir(dir_path: Path, compare_output_mode: str) -> tuple[sample_vs_fasim.OutputSummary, str]:
    output_map = sample_vs_fasim._load_output_map(dir_path, compare_output_mode)
    summary = sample_vs_fasim._aggregate_output_summaries(list(output_map.values()))
    sha256 = sample_vs_fasim._aggregate_output_sha256(dir_path, compare_output_mode)
    return summary, sha256


def _load_benchmark_metrics(stderr_path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("benchmark."):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        metrics[key[len("benchmark."):]] = value
    return metrics


def _metric_int(metrics: dict[str, str], key: str, *, default: int = 0) -> int:
    raw = metrics.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def _metric_str(metrics: dict[str, str], key: str, *, default: str = "") -> str:
    raw = metrics.get(key)
    if raw is None or raw == "":
        return default
    return raw


def _is_qualifying(run: SweepRun, *, min_relaxed_recall: float, min_top_hit_retention: float) -> bool:
    relaxed = run.comparison["relaxed"]
    relaxed_recall = float(relaxed["recall"])
    top_hit_retention = float(run.comparison["top_hit_retention"])
    return relaxed_recall >= min_relaxed_recall and top_hit_retention >= min_top_hit_retention


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep LongTarget two-stage prealign_cuda frontier settings against one exact LongTarget baseline.",
    )
    parser.add_argument("--dna", default="testDNA.fa")
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", default=0, type=int)
    parser.add_argument("--strand", default="", help="optional: pass to LongTarget -t")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "two_stage_frontier_sweep"),
        help="work directory for inputs, exact baseline, and two-stage sweep outputs",
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
        help="shared output schema for the exact baseline and two-stage runs",
    )
    parser.add_argument(
        "--prefilter-topk-values",
        default="64,128,256",
        help="comma-separated LONGTARGET_PREFILTER_TOPK values to test",
    )
    parser.add_argument(
        "--peak-suppress-bp-values",
        default="0,1,5",
        help="comma-separated LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP values to test",
    )
    parser.add_argument(
        "--score-floor-delta-values",
        default="0",
        help="comma-separated LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA values to test",
    )
    parser.add_argument(
        "--refine-pad-values",
        default="64",
        help="comma-separated LONGTARGET_REFINE_PAD_BP values to test",
    )
    parser.add_argument(
        "--refine-merge-gap-values",
        default="32",
        help="comma-separated LONGTARGET_REFINE_MERGE_GAP_BP values to test",
    )
    parser.add_argument(
        "--min-relaxed-recall",
        default="0.0",
        help="minimum relaxed recall required for a run to be considered qualifying",
    )
    parser.add_argument(
        "--min-top-hit-retention",
        default="0.0",
        help="minimum top-hit retention required for a run to be considered qualifying",
    )
    parser.add_argument(
        "--require-qualifying-run",
        action="store_true",
        help="exit non-zero when no two-stage run clears the quality gate",
    )

    args = parser.parse_args()

    compare_output_mode = args.compare_output_mode
    prefilter_topk_values = _parse_int_csv(args.prefilter_topk_values, flag="--prefilter-topk-values", min_value=1)
    peak_suppress_bp_values = _parse_int_csv(
        args.peak_suppress_bp_values,
        flag="--peak-suppress-bp-values",
        min_value=0,
    )
    score_floor_delta_values = _parse_int_csv(
        args.score_floor_delta_values,
        flag="--score-floor-delta-values",
        min_value=0,
    )
    refine_pad_values = _parse_int_csv(args.refine_pad_values, flag="--refine-pad-values", min_value=0)
    refine_merge_gap_values = _parse_int_csv(
        args.refine_merge_gap_values,
        flag="--refine-merge-gap-values",
        min_value=0,
    )
    min_relaxed_recall = _parse_non_negative_float(args.min_relaxed_recall, flag="--min-relaxed-recall")
    min_top_hit_retention = _parse_non_negative_float(
        args.min_top_hit_retention,
        flag="--min-top-hit-retention",
    )

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
    if not dna_src.exists():
        raise RuntimeError(f"missing DNA fasta: {dna_src}")
    if not rna_src.exists():
        raise RuntimeError(f"missing RNA fasta: {rna_src}")

    longtarget = Path(args.longtarget)
    if not longtarget.is_absolute():
        longtarget = (ROOT / longtarget).resolve()
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

    exact_out = work_dir / "longtarget_exact" / "output"
    exact_log = work_dir / "longtarget_exact" / "stderr.log"
    exact_out.parent.mkdir(parents=True, exist_ok=True)
    exact_out.mkdir(parents=True, exist_ok=True)
    exact_env = {
        "LONGTARGET_ENABLE_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA_REGION": "1",
        "LONGTARGET_BENCHMARK": "1",
        "LONGTARGET_OUTPUT_MODE": compare_output_mode,
    }
    exact_run = sample_vs_fasim._run_checked(
        label="longtarget_exact",
        cmd=[str(longtarget), *base_args, "-O", str(exact_out)],
        env_overrides=exact_env,
        stderr_path=exact_log,
        output_dir=exact_out,
        expect_benchmark_total=True,
        cwd=inputs_dir,
    )
    exact_summary, exact_sha256 = _summarize_output_dir(exact_out, compare_output_mode)

    sweep_runs: list[SweepRun] = []
    for topk in prefilter_topk_values:
        for suppress_bp in peak_suppress_bp_values:
            for score_floor_delta in score_floor_delta_values:
                for refine_pad_bp in refine_pad_values:
                    for refine_merge_gap_bp in refine_merge_gap_values:
                        label = _sanitize_label(
                            topk,
                            suppress_bp,
                            score_floor_delta,
                            refine_pad_bp,
                            refine_merge_gap_bp,
                        )
                        out_dir = work_dir / "runs" / label / "output"
                        log_path = work_dir / "runs" / label / "stderr.log"
                        out_dir.parent.mkdir(parents=True, exist_ok=True)
                        out_dir.mkdir(parents=True, exist_ok=True)
                        env = {
                            "LONGTARGET_ENABLE_CUDA": "1",
                            "LONGTARGET_ENABLE_SIM_CUDA": "1",
                            "LONGTARGET_ENABLE_SIM_CUDA_REGION": "1",
                            "LONGTARGET_BENCHMARK": "1",
                            "LONGTARGET_OUTPUT_MODE": compare_output_mode,
                            "LONGTARGET_TWO_STAGE": "1",
                            "LONGTARGET_PREFILTER_BACKEND": "prealign_cuda",
                            "LONGTARGET_PREFILTER_TOPK": str(topk),
                            "LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP": str(suppress_bp),
                            "LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA": str(score_floor_delta),
                            "LONGTARGET_REFINE_PAD_BP": str(refine_pad_bp),
                            "LONGTARGET_REFINE_MERGE_GAP_BP": str(refine_merge_gap_bp),
                        }
                        run = sample_vs_fasim._run_checked(
                            label=label,
                            cmd=[str(longtarget), *base_args, "-O", str(out_dir)],
                            env_overrides=env,
                            stderr_path=log_path,
                            output_dir=out_dir,
                            expect_benchmark_total=True,
                            cwd=inputs_dir,
                        )
                        comparison, _, output_summary = sample_vs_fasim._compare_output_mode(
                            exact_out,
                            out_dir,
                            compare_output_mode,
                        )
                        metrics = _load_benchmark_metrics(log_path)
                        internal_seconds = run.internal_seconds
                        if internal_seconds is None:
                            raise RuntimeError(f"{label} missing benchmark.total_seconds")
                        sweep_runs.append(
                            SweepRun(
                                label=label,
                                prefilter_backend=_metric_str(metrics, "prefilter_backend", default="disabled"),
                                prefilter_topk=topk,
                                peak_suppress_bp=suppress_bp,
                                score_floor_delta=score_floor_delta,
                                refine_pad_bp=refine_pad_bp,
                                refine_merge_gap_bp=refine_merge_gap_bp,
                                wall_seconds=run.wall_seconds,
                                internal_seconds=internal_seconds,
                                prefilter_hits=_metric_int(metrics, "prefilter_hits"),
                                refine_window_count=_metric_int(metrics, "refine_window_count"),
                                refine_total_bp=_metric_int(metrics, "refine_total_bp"),
                                stderr_path=str(log_path),
                                output_dir=str(out_dir),
                                output_mode=compare_output_mode,
                                output_files=output_summary.files,
                                line_count=output_summary.line_count,
                                output_sha256=sample_vs_fasim._aggregate_output_sha256(out_dir, compare_output_mode),
                                comparison=comparison,
                            )
                        )

    if not sweep_runs:
        raise RuntimeError("no two-stage runs were executed")

    best_overall = min(sweep_runs, key=lambda item: item.wall_seconds)
    qualifying_runs = [
        run
        for run in sweep_runs
        if _is_qualifying(
            run,
            min_relaxed_recall=min_relaxed_recall,
            min_top_hit_retention=min_top_hit_retention,
        )
    ]
    best_qualifying = min(qualifying_runs, key=lambda item: item.wall_seconds) if qualifying_runs else None

    report = {
        "work_dir": str(work_dir),
        "inputs": {
            "dna_src": str(dna_src),
            "rna_src": str(rna_src),
            "dna_basename": dna.name,
            "rna_basename": rna.name,
            "rule": args.rule,
            "strand": args.strand,
        },
        "compare_output_mode": compare_output_mode,
        "prefilter_backend": "prealign_cuda",
        "prefilter_topk_values": prefilter_topk_values,
        "peak_suppress_bp_values": peak_suppress_bp_values,
        "score_floor_delta_values": score_floor_delta_values,
        "refine_pad_bp_values": refine_pad_values,
        "refine_merge_gap_bp_values": refine_merge_gap_values,
        "quality_gate": {
            "min_relaxed_recall": min_relaxed_recall,
            "min_top_hit_retention": min_top_hit_retention,
            "require_qualifying_run": args.require_qualifying_run,
        },
        "exact": sample_vs_fasim._output_report(
            exact_run,
            output_mode=compare_output_mode,
            output_summary=exact_summary,
            output_sha256=exact_sha256,
        ),
        "runs": [dataclasses.asdict(run) for run in sweep_runs],
        "best": dataclasses.asdict(best_overall),
        "best_overall": dataclasses.asdict(best_overall),
        "best_qualifying": dataclasses.asdict(best_qualifying) if best_qualifying else None,
    }
    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(
        f"exact baseline wall={exact_run.wall_seconds:.3f}s internal={exact_run.internal_seconds:.3f}s mode={compare_output_mode}"
    )
    for run in sweep_runs:
        relaxed = run.comparison["relaxed"]
        print(
            f"{run.label} backend={run.prefilter_backend} topk={run.prefilter_topk} "
            f"suppress_bp={run.peak_suppress_bp} score_floor_delta={run.score_floor_delta} "
            f"refine_pad_bp={run.refine_pad_bp} refine_merge_gap_bp={run.refine_merge_gap_bp} "
            f"wall={run.wall_seconds:.3f}s internal={run.internal_seconds:.3f}s "
            f"prefilter_hits={run.prefilter_hits} refine_window_count={run.refine_window_count} "
            f"refine_total_bp={run.refine_total_bp} relaxed_recall={relaxed['recall']:.3f} "
            f"top_hit_retention={run.comparison['top_hit_retention']:.3f}"
        )
    print(
        f"best overall topk={best_overall.prefilter_topk} suppress_bp={best_overall.peak_suppress_bp} "
        f"score_floor_delta={best_overall.score_floor_delta} refine_pad_bp={best_overall.refine_pad_bp} "
        f"refine_merge_gap_bp={best_overall.refine_merge_gap_bp} wall={best_overall.wall_seconds:.3f}s"
    )
    if best_qualifying:
        print(
            f"best qualifying topk={best_qualifying.prefilter_topk} suppress_bp={best_qualifying.peak_suppress_bp} "
            f"score_floor_delta={best_qualifying.score_floor_delta} refine_pad_bp={best_qualifying.refine_pad_bp} "
            f"refine_merge_gap_bp={best_qualifying.refine_merge_gap_bp} wall={best_qualifying.wall_seconds:.3f}s"
        )
    else:
        print("best qualifying: none")
    print(f"report: {report_path}")
    if args.require_qualifying_run and not best_qualifying:
        raise RuntimeError("no two-stage run satisfied the configured quality gate")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
