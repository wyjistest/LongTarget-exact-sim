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
    wall_seconds: float
    stderr_path: str
    output_dir: str
    output_mode: str
    output_files: list[str]
    line_count: int
    output_sha256: str
    comparison: dict[str, object]


def _parse_int_csv(spec: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as e:
            raise RuntimeError(f"invalid {flag} entry: {item}") from e
        if value <= 0:
            raise RuntimeError(f"{flag} entries must be > 0: {item}")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return values


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


def _sanitize_label(device_set: str, extend_threads: int) -> str:
    return f"fasim_devices_{device_set.replace(',', '-')}_threads_{extend_threads}"


def _summarize_output_dir(dir_path: Path, compare_output_mode: str) -> tuple[sample_vs_fasim.OutputSummary, str]:
    output_map = sample_vs_fasim._load_output_map(dir_path, compare_output_mode)
    summary = sample_vs_fasim._aggregate_output_summaries(list(output_map.values()))
    sha256 = sample_vs_fasim._aggregate_output_sha256(dir_path, compare_output_mode)
    return summary, sha256


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

    args = parser.parse_args()

    compare_output_mode = args.compare_output_mode
    device_sets = _normalize_device_sets(args.device_sets)
    extend_threads = _parse_int_csv(args.extend_threads, flag="--extend-threads")

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
    if not longtarget.exists():
        raise RuntimeError(f"missing LongTarget binary: {longtarget}")

    local_fasim_cuda = Path(args.fasim_local_cuda)
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
            label = _sanitize_label(device_set, extend_thread)
            out_dir = work_dir / "runs" / label / "output"
            log_path = work_dir / "runs" / label / "stderr.log"
            out_dir.parent.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)
            env = {
                "BIN": str(local_fasim_cuda),
                "FASIM_THRESHOLD_POLICY": args.threshold_policy,
                "FASIM_OUTPUT_MODE": compare_output_mode,
                "FASIM_PREALIGN_CUDA_TOPK": str(args.fasim_prealign_cuda_topk),
                "FASIM_PREALIGN_PEAK_SUPPRESS_BP": str(args.fasim_prealign_peak_suppress_bp),
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

    best = min(sweep_runs, key=lambda item: item.wall_seconds)

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
        "device_sets": device_sets,
        "extend_threads": extend_threads,
        "exact": sample_vs_fasim._output_report(
            exact_run,
            output_mode=compare_output_mode,
            output_summary=exact_summary,
            output_sha256=exact_sha256,
        ),
        "runs": [dataclasses.asdict(run) for run in sweep_runs],
        "best": dataclasses.asdict(best),
    }
    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(
        f"exact baseline wall={exact_run.wall_seconds:.3f}s internal={exact_run.internal_seconds:.3f}s mode={compare_output_mode}"
    )
    for run in sweep_runs:
        relaxed = run.comparison["relaxed"]
        print(
            f"{run.label} devices={run.device_set} extend_threads={run.extend_threads} wall={run.wall_seconds:.3f}s "
            f"relaxed_recall={relaxed['recall']:.3f} top_hit_retention={run.comparison['top_hit_retention']:.3f}"
        )
    print(
        f"best devices={best.device_set} extend_threads={best.extend_threads} wall={best.wall_seconds:.3f}s"
    )
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
