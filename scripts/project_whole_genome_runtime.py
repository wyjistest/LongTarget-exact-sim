#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project whole-genome runtime from a LongTarget benchmark stderr log."
    )
    parser.add_argument("--stderr", required=True, help="Path to benchmark stderr log.")
    parser.add_argument(
        "--sample-bp",
        type=int,
        default=0,
        help="Processed bp represented by the sample benchmark.",
    )
    parser.add_argument(
        "--sample-fasta",
        help="FASTA used for the sample benchmark; sequence length is used when --sample-bp is omitted.",
    )
    parser.add_argument(
        "--genome-bp",
        type=int,
        required=True,
        help="Target whole-genome bp to project to.",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help="Number of independent workers/devices sharing the genome workload.",
    )
    parser.add_argument(
        "--target-hours",
        type=float,
        default=24.0,
        help="Wall-time target in hours for the projection report.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text report.",
    )
    return parser.parse_args()


def parse_metric_value(raw: str):
    text = raw.strip()
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_benchmark_metrics(path: Path) -> dict[str, object]:
    metrics: dict[str, object] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("benchmark.") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            metrics[key[len("benchmark.") :]] = parse_metric_value(value)
    return metrics


def fasta_bp(path: Path) -> int:
    total = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line or line.startswith(">"):
                continue
            total += len(line.strip())
    return total


def metric_as_float(metrics: dict[str, object], key: str) -> float:
    value = metrics.get(key)
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"benchmark.{key} is not numeric: {value!r}")


def optional_ratio(metrics: dict[str, object], numerator_key: str, denominator_key: str):
    numerator = metrics.get(numerator_key)
    denominator = metrics.get(denominator_key)
    if numerator is None or denominator is None:
        return None
    if not isinstance(numerator, (int, float)):
        raise ValueError(f"benchmark.{numerator_key} is not numeric: {numerator!r}")
    if not isinstance(denominator, (int, float)):
        raise ValueError(f"benchmark.{denominator_key} is not numeric: {denominator!r}")
    if float(denominator) <= 0.0:
        return None
    return float(numerator) / float(denominator)


def main() -> int:
    args = parse_args()
    stderr_path = Path(args.stderr)
    if not stderr_path.is_file():
        raise SystemExit(f"missing stderr log: {stderr_path}")

    sample_bp = args.sample_bp
    if sample_bp <= 0:
        if not args.sample_fasta:
            raise SystemExit("either --sample-bp or --sample-fasta is required")
        sample_bp = fasta_bp(Path(args.sample_fasta))
    if sample_bp <= 0:
        raise SystemExit("sample bp must be > 0")
    if args.genome_bp <= 0:
        raise SystemExit("genome bp must be > 0")
    if args.parallel_workers <= 0:
        raise SystemExit("parallel workers must be > 0")

    metrics = parse_benchmark_metrics(stderr_path)
    if "total_seconds" not in metrics:
        raise SystemExit(f"benchmark.total_seconds missing in {stderr_path}")

    total_seconds = metric_as_float(metrics, "total_seconds")
    calc_score_seconds = metric_as_float(metrics, "calc_score_seconds")
    sim_seconds = metric_as_float(metrics, "sim_seconds")
    postprocess_seconds = metric_as_float(metrics, "postprocess_seconds")

    scale_factor = (float(args.genome_bp) / float(sample_bp)) / float(args.parallel_workers)
    projected_total_seconds = total_seconds * scale_factor
    projected_calc_score_seconds = calc_score_seconds * scale_factor
    projected_sim_seconds = sim_seconds * scale_factor
    projected_postprocess_seconds = postprocess_seconds * scale_factor
    projected_total_hours = projected_total_seconds / 3600.0
    target_hours = float(args.target_hours)

    report = {
        "stderr": str(stderr_path),
        "sample_bp": sample_bp,
        "genome_bp": args.genome_bp,
        "parallel_workers": args.parallel_workers,
        "scale_factor": scale_factor,
        "sample_total_seconds": total_seconds,
        "projected_total_seconds": projected_total_seconds,
        "projected_total_hours": projected_total_hours,
        "projected_calc_score_seconds": projected_calc_score_seconds,
        "projected_sim_seconds": projected_sim_seconds,
        "projected_postprocess_seconds": projected_postprocess_seconds,
        "target_hours": target_hours,
        "meets_target": projected_total_hours <= target_hours,
        "benchmark": metrics,
    }

    window_pipeline_eligible_ratio = optional_ratio(
        metrics, "sim_window_pipeline_tasks_eligible", "sim_window_pipeline_tasks_considered"
    )
    if window_pipeline_eligible_ratio is not None:
        report["window_pipeline_eligible_ratio"] = window_pipeline_eligible_ratio

    window_pipeline_fallback_ratio = optional_ratio(
        metrics, "sim_window_pipeline_task_fallbacks", "sim_window_pipeline_tasks_considered"
    )
    if window_pipeline_fallback_ratio is not None:
        report["window_pipeline_fallback_ratio"] = window_pipeline_fallback_ratio

    calc_score_cuda_task_ratio = optional_ratio(
        metrics, "calc_score_cuda_tasks", "calc_score_tasks_total"
    )
    if calc_score_cuda_task_ratio is not None:
        report["calc_score_cuda_task_ratio"] = calc_score_cuda_task_ratio

    calc_score_cpu_fallback_ratio = optional_ratio(
        metrics, "calc_score_cpu_fallback_tasks", "calc_score_tasks_total"
    )
    if calc_score_cpu_fallback_ratio is not None:
        report["calc_score_cpu_fallback_ratio"] = calc_score_cpu_fallback_ratio

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    solver_backend = metrics.get("sim_solver_backend", "unknown")
    print(f"stderr={stderr_path}")
    print(f"sim_solver_backend={solver_backend}")
    print(f"sample_bp={sample_bp}")
    print(f"genome_bp={args.genome_bp}")
    print(f"parallel_workers={args.parallel_workers}")
    print(f"scale_factor={scale_factor:.6f}")
    print(f"sample_total_seconds={total_seconds:.6f}")
    print(f"projected_total_seconds={projected_total_seconds:.6f}")
    print(f"projected_total_hours={projected_total_hours:.6f}")
    print(f"projected_calc_score_seconds={projected_calc_score_seconds:.6f}")
    print(f"projected_sim_seconds={projected_sim_seconds:.6f}")
    print(f"projected_postprocess_seconds={projected_postprocess_seconds:.6f}")
    print(f"target_hours={target_hours:.6f}")
    print(f"meets_target={'yes' if report['meets_target'] else 'no'}")
    if "window_pipeline_eligible_ratio" in report:
        print(f"window_pipeline_eligible_ratio={report['window_pipeline_eligible_ratio']:.6f}")
    if "window_pipeline_fallback_ratio" in report:
        print(f"window_pipeline_fallback_ratio={report['window_pipeline_fallback_ratio']:.6f}")
    if "calc_score_cuda_task_ratio" in report:
        print(f"calc_score_cuda_task_ratio={report['calc_score_cuda_task_ratio']:.6f}")
    if "calc_score_cpu_fallback_ratio" in report:
        print(f"calc_score_cpu_fallback_ratio={report['calc_score_cpu_fallback_ratio']:.6f}")
    print(
        "note=phase seconds are projected independently; use projected_total_hours as the wall-time estimate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
