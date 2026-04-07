#!/usr/bin/env python3
import argparse
import dataclasses
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


@dataclasses.dataclass(frozen=True)
class SweepRun:
    label: str
    device_set: str
    extend_threads: int
    topk: int
    suppress_bp: int
    wall_seconds: float
    stderr_path: str
    output_dir: str
    output_mode: str
    output_files: list[str]
    line_count: int
    output_sha256: str
    comparison: dict[str, object]


def _parse_int_csv(spec: str, *, flag: str, min_value: int = 1) -> list[int]:
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
            comparator = f">= {min_value}"
            raise RuntimeError(f"{flag} entries must be {comparator}: {item}")
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


def _normalize_device_sets(items: list[str] | None) -> list[str]:
    if items:
        normalized = [item.strip() for item in items if item.strip()]
        if not normalized:
            raise RuntimeError("--device-sets must not be empty")
        return normalized

    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            gpu_ids = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            if gpu_ids:
                device_sets = [gpu_ids[0]]
                if len(gpu_ids) >= 2:
                    device_sets.append(",".join(gpu_ids[:2]))
                return device_sets
    except FileNotFoundError:
        pass

    return ["0"]


def _sanitize_label(device_set: str, extend_threads: int, topk: int, suppress_bp: int) -> str:
    return (
        f"fasim_devices_{device_set.replace(',', '-')}_threads_{extend_threads}"
        f"_topk_{topk}_suppress_{suppress_bp}"
    )


def _summarize_output_dir(dir_path: Path, compare_output_mode: str) -> tuple[sample_vs_fasim.OutputSummary, str]:
    output_map = sample_vs_fasim._load_output_map(dir_path, compare_output_mode)
    summary = sample_vs_fasim._aggregate_output_summaries(list(output_map.values()))
    sha256 = sample_vs_fasim._aggregate_output_sha256(dir_path, compare_output_mode)
    return summary, sha256


def _is_qualifying(run: SweepRun, *, min_relaxed_recall: float, min_top_hit_retention: float) -> bool:
    relaxed = run.comparison["relaxed"]
    relaxed_recall = float(relaxed["recall"])
    top_hit_retention = float(run.comparison["top_hit_retention"])
    return relaxed_recall >= min_relaxed_recall and top_hit_retention >= min_top_hit_retention


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep vendored fasim throughput presets against one exact LongTarget baseline.",
    )
    parser.add_argument("--dna", default="testDNA.fa")
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", default=0, type=int)
    parser.add_argument("--strand", default="", help="optional: pass to LongTarget -t")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_throughput_sweep"),
        help="work directory for inputs, exact baseline, and throughput sweep outputs",
    )
    parser.add_argument(
        "--longtarget",
        default=str(ROOT / "longtarget_cuda"),
        help="path to LongTarget binary",
    )
    parser.add_argument(
        "--fasim-local-cuda",
        default=str(ROOT / "fasim_longtarget_cuda"),
        help="path to the vendored/local fasim CUDA binary",
    )
    parser.add_argument(
        "--compare-output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
        help="shared output schema for the exact baseline and throughput runs",
    )
    parser.add_argument(
        "--threshold-policy",
        default="fasim_peak80",
        help="FASIM_THRESHOLD_POLICY passed to the throughput preset wrapper",
    )
    parser.add_argument(
        "--fasim-prealign-cuda-topk",
        default="64",
        help="FASIM_PREALIGN_CUDA_TOPK passed to the throughput preset wrapper",
    )
    parser.add_argument(
        "--fasim-prealign-peak-suppress-bp",
        default="5",
        help="FASIM_PREALIGN_PEAK_SUPPRESS_BP passed to the throughput preset wrapper",
    )
    parser.add_argument(
        "--topk-values",
        default=None,
        help="optional comma-separated TOPK sweep values (default: use --fasim-prealign-cuda-topk as a single fixed value)",
    )
    parser.add_argument(
        "--suppress-bp-values",
        default=None,
        help="optional comma-separated peak suppress bp sweep values (default: use --fasim-prealign-peak-suppress-bp as a single fixed value)",
    )
    parser.add_argument(
        "--device-sets",
        nargs="+",
        default=None,
        help="list of FASIM_CUDA_DEVICES settings to test, e.g. --device-sets 0 0,1",
    )
    parser.add_argument(
        "--extend-threads",
        default="1,4,8,16",
        help="comma-separated FASIM_EXTEND_THREADS values to test (default: 1,4,8,16)",
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
        help="exit non-zero when no throughput run clears the quality gate",
    )

    args = parser.parse_args()

    compare_output_mode = args.compare_output_mode
    device_sets = _normalize_device_sets(args.device_sets)
    extend_threads = _parse_int_csv(args.extend_threads, flag="--extend-threads")
    topk_values = (
        _parse_int_csv(args.topk_values, flag="--topk-values")
        if args.topk_values
        else [int(args.fasim_prealign_cuda_topk)]
    )
    suppress_bp_values = (
        _parse_int_csv(args.suppress_bp_values, flag="--suppress-bp-values", min_value=0)
        if args.suppress_bp_values
        else [int(args.fasim_prealign_peak_suppress_bp)]
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

    local_fasim_cuda = Path(args.fasim_local_cuda)
    if not local_fasim_cuda.is_absolute():
        local_fasim_cuda = (ROOT / local_fasim_cuda).resolve()
    throughput_runner = ROOT / "scripts" / "run_fasim_throughput_preset.sh"

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
    for device_set in device_sets:
        for extend_thread in extend_threads:
            for topk in topk_values:
                for suppress_bp in suppress_bp_values:
                    label = _sanitize_label(device_set, extend_thread, topk, suppress_bp)
                    out_dir = work_dir / "runs" / label / "output"
                    log_path = work_dir / "runs" / label / "stderr.log"
                    out_dir.parent.mkdir(parents=True, exist_ok=True)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    env = {
                        "BIN": str(local_fasim_cuda),
                        "FASIM_THRESHOLD_POLICY": args.threshold_policy,
                        "FASIM_OUTPUT_MODE": compare_output_mode,
                        "FASIM_PREALIGN_CUDA_TOPK": str(topk),
                        "FASIM_PREALIGN_PEAK_SUPPRESS_BP": str(suppress_bp),
                        "FASIM_CUDA_DEVICES": device_set,
                        "FASIM_EXTEND_THREADS": str(extend_thread),
                    }
                    run = sample_vs_fasim._run_checked(
                        label=label,
                        cmd=[str(throughput_runner), *base_args, "-O", str(out_dir)],
                        env_overrides=env,
                        stderr_path=log_path,
                        output_dir=out_dir,
                        expect_benchmark_total=False,
                        cwd=inputs_dir,
                    )
                    comparison, _, output_summary = sample_vs_fasim._compare_output_mode(
                        exact_out,
                        out_dir,
                        compare_output_mode,
                    )
                    sweep_runs.append(
                        SweepRun(
                            label=label,
                            device_set=device_set,
                            extend_threads=extend_thread,
                            topk=topk,
                            suppress_bp=suppress_bp,
                            wall_seconds=run.wall_seconds,
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
        raise RuntimeError("no throughput runs were executed")

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
        "threshold_policy": args.threshold_policy,
        "fasim_prealign_cuda_topk": int(args.fasim_prealign_cuda_topk),
        "fasim_prealign_peak_suppress_bp": int(args.fasim_prealign_peak_suppress_bp),
        "fasim_prealign_cuda_topk_values": topk_values,
        "fasim_prealign_peak_suppress_bp_values": suppress_bp_values,
        "device_sets": device_sets,
        "extend_threads": extend_threads,
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
            f"{run.label} devices={run.device_set} extend_threads={run.extend_threads} topk={run.topk} "
            f"suppress_bp={run.suppress_bp} wall={run.wall_seconds:.3f}s "
            f"relaxed_recall={relaxed['recall']:.3f} top_hit_retention={run.comparison['top_hit_retention']:.3f}"
        )
    print(
        f"best overall devices={best_overall.device_set} extend_threads={best_overall.extend_threads} "
        f"topk={best_overall.topk} suppress_bp={best_overall.suppress_bp} wall={best_overall.wall_seconds:.3f}s"
    )
    if best_qualifying:
        print(
            f"best qualifying devices={best_qualifying.device_set} extend_threads={best_qualifying.extend_threads} "
            f"topk={best_qualifying.topk} suppress_bp={best_qualifying.suppress_bp} wall={best_qualifying.wall_seconds:.3f}s"
        )
    else:
        print("best qualifying: none")
    print(f"report: {report_path}")
    if args.require_qualifying_run and not best_qualifying:
        raise RuntimeError("no throughput run satisfied the configured quality gate")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
