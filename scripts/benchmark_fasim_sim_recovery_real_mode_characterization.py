#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import os
import shutil
import statistics
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_profile import read_expected_digest  # noqa: E402


def parse_benchmark_metrics(text: str) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("benchmark."):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        metrics[key[len("benchmark.") :]] = value
    return metrics


def run_command(
    *,
    cmd: Sequence[str],
    cwd: Path,
    env: Dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> Tuple[Dict[str, str], float]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    wall_seconds = time.perf_counter() - start
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"command failed with exit {proc.returncode}: {' '.join(cmd)}")
    return parse_benchmark_metrics(proc.stdout + "\n" + proc.stderr), wall_seconds


def clean_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("FASIM_SIM_RECOVERY", None)
    env.pop("FASIM_SIM_RECOVERY_VALIDATE", None)
    return env


def run_fast_profile(
    *,
    bin_path: Path,
    work_dir: Path,
    expected_digest_file: Path,
) -> Tuple[Dict[str, str], float]:
    env = clean_env()
    return run_command(
        cmd=[
            sys.executable,
            str(SCRIPTS_DIR / "benchmark_fasim_profile.py"),
            "--mode",
            "exactness",
            "--bin",
            str(bin_path),
            "--require-profile",
            "--expected-digest-file",
            str(expected_digest_file),
            "--work-dir",
            str(work_dir / "fast_profile"),
        ],
        cwd=ROOT,
        env=env,
        stdout_path=work_dir / "fast_profile.stdout.log",
        stderr_path=work_dir / "fast_profile.stderr.log",
    )


def run_sim_recovery(
    *,
    bin_path: Path,
    work_dir: Path,
    profile_set: str,
    validate: bool,
) -> Tuple[Dict[str, str], float]:
    env = clean_env()
    env["FASIM_SIM_RECOVERY"] = "1"
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "benchmark_fasim_sim_gap_taxonomy.py"),
        "--bin",
        str(bin_path),
        "--profile-set",
        profile_set,
        "--require-sim-gap-taxonomy",
        "--sim-recovery",
        "--sim-recovery-output",
        str(work_dir / "sim_close.lite"),
        "--sim-recovery-report",
        str(work_dir / "sim_close_report.md"),
        "--output",
        str(work_dir / "taxonomy.md"),
        "--work-dir",
        str(work_dir / "taxonomy_work"),
    ]
    if validate:
        env["FASIM_SIM_RECOVERY_VALIDATE"] = "1"
        cmd.append("--sim-recovery-validate")
    return run_command(
        cmd=cmd,
        cwd=ROOT,
        env=env,
        stdout_path=work_dir / "stdout.log",
        stderr_path=work_dir / "stderr.log",
    )


def metric_float(metrics: Dict[str, str], key: str) -> float:
    try:
        return float(metrics.get(key, "0"))
    except ValueError:
        return 0.0


def metric_int(metrics: Dict[str, str], key: str) -> int:
    try:
        return int(float(metrics.get(key, "0")))
    except ValueError:
        return 0


def median_float(values: Iterable[float]) -> float:
    values_list = list(values)
    return float(statistics.median(values_list)) if values_list else 0.0


def stable(values: Iterable[str]) -> bool:
    values_list = list(values)
    return bool(values_list) and all(value == values_list[0] for value in values_list)


def append_table(lines: List[str], headers: List[str], rows: Iterable[List[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def first(values: Sequence[str]) -> str:
    return values[0] if values else ""


def characterize(
    *,
    bin_path: Path,
    profile_set: str,
    repeat: int,
    work_dir: Path,
    expected_digest_file: Path,
) -> Tuple[str, Dict[str, str]]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    expected_fast_digest = read_expected_digest(expected_digest_file)

    runs: List[Dict[str, object]] = []
    for index in range(1, repeat + 1):
        run_dir = work_dir / f"run{index}"
        fast_metrics, fast_wall = run_fast_profile(
            bin_path=bin_path,
            work_dir=run_dir,
            expected_digest_file=expected_digest_file,
        )
        sim_metrics, sim_wall = run_sim_recovery(
            bin_path=bin_path,
            work_dir=run_dir / "sim_close",
            profile_set=profile_set,
            validate=False,
        )
        validate_metrics, validate_wall = run_sim_recovery(
            bin_path=bin_path,
            work_dir=run_dir / "sim_close_validate",
            profile_set=profile_set,
            validate=True,
        )
        runs.append(
            {
                "index": index,
                "fast_metrics": fast_metrics,
                "fast_wall": fast_wall,
                "sim_metrics": sim_metrics,
                "sim_wall": sim_wall,
                "validate_metrics": validate_metrics,
                "validate_wall": validate_wall,
            }
        )

    fast_digests = [str(run["fast_metrics"].get("fasim_output_digest", "")) for run in runs]  # type: ignore[index, union-attr]
    sim_close_digests = [
        str(run["sim_metrics"].get("fasim_sim_recovery.total.output_digest", ""))  # type: ignore[index, union-attr]
        for run in runs
    ]
    validate_digests = [
        str(run["validate_metrics"].get("fasim_sim_recovery.total.output_digest", ""))  # type: ignore[index, union-attr]
        for run in runs
    ]
    fast_digest_stable = stable(fast_digests)
    fast_expected_digest_match = bool(fast_digests) and all(digest == expected_fast_digest for digest in fast_digests)
    sim_close_digest_stable = stable(sim_close_digests)
    validate_selection_stable = (
        stable(validate_digests)
        and len(sim_close_digests) == len(validate_digests)
        and all(left == right for left, right in zip(sim_close_digests, validate_digests))
    )

    fast_total_seconds_median = median_float(
        metric_float(run["fast_metrics"], "fasim_total_seconds") for run in runs  # type: ignore[arg-type]
    )
    sim_close_wall_seconds_median = median_float(float(run["sim_wall"]) for run in runs)
    validate_wall_seconds_median = median_float(float(run["validate_wall"]) for run in runs)
    boxes_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.boxes")  # type: ignore[arg-type]
        for run in runs
    )
    cells_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.cells")  # type: ignore[arg-type]
        for run in runs
    )
    full_search_cells_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.full_search_cells")  # type: ignore[arg-type]
        for run in runs
    )
    cell_fraction_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.cell_fraction")  # type: ignore[arg-type]
        for run in runs
    )
    executor_seconds_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.executor_seconds")  # type: ignore[arg-type]
        for run in runs
    )
    fasim_records_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.fasim_records")  # type: ignore[arg-type]
        for run in runs
    )
    recovered_candidates_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.recovered_candidates")  # type: ignore[arg-type]
        for run in runs
    )
    recovered_accepted_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.recovered_accepted")  # type: ignore[arg-type]
        for run in runs
    )
    fasim_suppressed_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.fasim_suppressed")  # type: ignore[arg-type]
        for run in runs
    )
    output_records_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.output_records")  # type: ignore[arg-type]
        for run in runs
    )
    recall_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.recall_vs_sim")  # type: ignore[arg-type]
        for run in runs
    )
    precision_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.precision_vs_sim")  # type: ignore[arg-type]
        for run in runs
    )
    extra_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.extra_vs_sim")  # type: ignore[arg-type]
        for run in runs
    )
    overlap_conflicts_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.overlap_conflicts")  # type: ignore[arg-type]
        for run in runs
    )
    fast_mode_output_mutations = max(
        metric_int(run["validate_metrics"], "fasim_sim_recovery.total.output_mutations_fast_mode")  # type: ignore[arg-type]
        for run in runs
    )
    fallbacks_median = median_float(
        metric_float(run["validate_metrics"], "fasim_sim_recovery.total.fallbacks")  # type: ignore[arg-type]
        for run in runs
    )

    recommendation = (
        "experimental_opt_in"
        if (
            fast_digest_stable
            and fast_expected_digest_match
            and sim_close_digest_stable
            and validate_selection_stable
            and fast_mode_output_mutations == 0
            and recall_median >= 90.0
            and precision_median >= 80.0
        )
        else "needs_followup"
    )

    lines: List[str] = []
    lines.append("# Fasim SIM-Close Recovery Real Mode Characterization")
    lines.append("")
    lines.append("Base branch:")
    lines.append("")
    lines.append("```text")
    lines.append("fasim-sim-recovery-real-mode-skeleton")
    lines.append("```")
    lines.append("")
    lines.append(
        "This report characterizes the default-off `FASIM_SIM_RECOVERY=1` "
        "skeleton. It adds no new recovery logic and does not change scoring, "
        "threshold, non-overlap, GPU, filter, or default fast-mode behavior."
    )
    lines.append("")
    append_table(
        lines,
        ["Setting", "Value"],
        [
            ["profile_set", profile_set],
            ["repeat", str(repeat)],
            ["fast_mode", "default Fasim exactness profile"],
            ["sim_close_mode", "FASIM_SIM_RECOVERY=1"],
            ["validate_mode", "FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1"],
            ["expected_fast_digest", expected_fast_digest],
        ],
    )
    lines.append("")

    rows: List[List[str]] = []
    for run in runs:
        fast_metrics = run["fast_metrics"]  # type: ignore[assignment]
        sim_metrics = run["sim_metrics"]  # type: ignore[assignment]
        validate_metrics = run["validate_metrics"]  # type: ignore[assignment]
        rows.append(
            [
                str(run["index"]),
                f"{metric_float(fast_metrics, 'fasim_total_seconds'):.6f}",
                str(fast_metrics.get("fasim_output_digest", "")),
                str(sim_metrics.get("fasim_sim_recovery.total.output_digest", "")),
                str(validate_metrics.get("fasim_sim_recovery.total.output_digest", "")),
                str(validate_metrics.get("fasim_sim_recovery.total.output_records", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.recall_vs_sim", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.precision_vs_sim", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.extra_vs_sim", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.overlap_conflicts", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.fallbacks", "0")),
                f"{float(run['sim_wall']):.6f}",
                f"{float(run['validate_wall']):.6f}",
            ]
        )

    lines.append("## Run Summary")
    lines.append("")
    append_table(
        lines,
        [
            "Run",
            "Fast seconds",
            "Fast digest",
            "SIM-close digest",
            "Validate digest",
            "Output records",
            "Recall vs SIM",
            "Precision vs SIM",
            "Extra vs SIM",
            "Overlap conflicts",
            "Fallbacks",
            "SIM-close wall seconds",
            "Validate wall seconds",
        ],
        rows,
    )
    lines.append("")

    footprint_rows: List[List[str]] = []
    for run in runs:
        validate_metrics = run["validate_metrics"]  # type: ignore[assignment]
        footprint_rows.append(
            [
                str(run["index"]),
                str(validate_metrics.get("fasim_sim_recovery.total.boxes", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.cells", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.full_search_cells", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.cell_fraction", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.executor_seconds", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.fasim_records", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.recovered_candidates", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.recovered_accepted", "0")),
                str(validate_metrics.get("fasim_sim_recovery.total.fasim_suppressed", "0")),
            ]
        )

    lines.append("## Recovery Footprint")
    lines.append("")
    append_table(
        lines,
        [
            "Run",
            "Boxes",
            "Cells",
            "Full search cells",
            "Cell fraction",
            "Executor seconds",
            "Fasim records",
            "Recovered candidates",
            "Recovered accepted",
            "Fasim suppressed",
        ],
        footprint_rows,
    )
    lines.append("")

    aggregate_rows = [
        ["fasim_sim_recovery_characterization_repeat", str(repeat)],
        ["fasim_sim_recovery_characterization_fast_digest_stable", "1" if fast_digest_stable else "0"],
        ["fasim_sim_recovery_characterization_fast_expected_digest_match", "1" if fast_expected_digest_match else "0"],
        ["fasim_sim_recovery_characterization_sim_close_digest_stable", "1" if sim_close_digest_stable else "0"],
        ["fasim_sim_recovery_characterization_validate_selection_stable", "1" if validate_selection_stable else "0"],
        ["fasim_sim_recovery_characterization_fast_digest", first(fast_digests)],
        ["fasim_sim_recovery_characterization_sim_close_digest", first(sim_close_digests)],
        ["fasim_sim_recovery_characterization_fast_total_seconds_median", f"{fast_total_seconds_median:.6f}"],
        ["fasim_sim_recovery_characterization_sim_close_wall_seconds_median", f"{sim_close_wall_seconds_median:.6f}"],
        ["fasim_sim_recovery_characterization_validate_wall_seconds_median", f"{validate_wall_seconds_median:.6f}"],
        ["fasim_sim_recovery_characterization_boxes_median", f"{boxes_median:.6f}"],
        ["fasim_sim_recovery_characterization_cells_median", f"{cells_median:.6f}"],
        ["fasim_sim_recovery_characterization_full_search_cells_median", f"{full_search_cells_median:.6f}"],
        ["fasim_sim_recovery_characterization_cell_fraction_median", f"{cell_fraction_median:.6f}"],
        ["fasim_sim_recovery_characterization_executor_seconds_median", f"{executor_seconds_median:.6f}"],
        ["fasim_sim_recovery_characterization_fasim_records_median", f"{fasim_records_median:.6f}"],
        ["fasim_sim_recovery_characterization_recovered_candidates_median", f"{recovered_candidates_median:.6f}"],
        ["fasim_sim_recovery_characterization_recovered_accepted_median", f"{recovered_accepted_median:.6f}"],
        ["fasim_sim_recovery_characterization_fasim_suppressed_median", f"{fasim_suppressed_median:.6f}"],
        ["fasim_sim_recovery_characterization_output_records_median", f"{output_records_median:.6f}"],
        ["fasim_sim_recovery_characterization_recall_vs_sim_median", f"{recall_median:.6f}"],
        ["fasim_sim_recovery_characterization_precision_vs_sim_median", f"{precision_median:.6f}"],
        ["fasim_sim_recovery_characterization_extra_vs_sim_median", f"{extra_median:.6f}"],
        ["fasim_sim_recovery_characterization_overlap_conflicts_median", f"{overlap_conflicts_median:.6f}"],
        ["fasim_sim_recovery_characterization_fallbacks_median", f"{fallbacks_median:.6f}"],
        ["fasim_sim_recovery_characterization_fast_mode_output_mutations", str(fast_mode_output_mutations)],
        ["fasim_sim_recovery_characterization_recommendation", recommendation],
    ]

    lines.append("## Aggregate")
    lines.append("")
    append_table(lines, ["Metric", "Value"], aggregate_rows)
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    if recommendation == "experimental_opt_in":
        lines.append(
            "Keep `FASIM_SIM_RECOVERY=1` as an experimental opt-in. The repeated "
            "synthetic characterization shows stable fast and SIM-close digests, "
            "post-hoc validation does not alter selection, recall remains high, "
            "precision remains acceptable, and fast-mode output mutations remain zero."
        )
    else:
        lines.append(
            "Do not expand SIM-close mode yet. One or more stability, recall, "
            "precision, digest, or fast-mode mutation gates failed."
        )
    lines.append("")
    lines.append("Do not recommend or default SIM-close mode until production-corpus evidence exists.")
    lines.append("")

    lines.append("## Scope")
    lines.append("")
    lines.append("```text")
    lines.append("Default Fasim output changed: no")
    lines.append("SIM labels used as production input: no")
    lines.append("Validation affects production selection: no")
    lines.append("Scoring/threshold/non-overlap behavior change: no")
    lines.append("GPU/filter behavior change: no")
    lines.append("Recommended/default mode: no")
    lines.append("Production accuracy claim: no")
    lines.append("```")
    lines.append("")

    telemetry = {
        "repeat": str(repeat),
        "fast_digest_stable": "1" if fast_digest_stable else "0",
        "fast_expected_digest_match": "1" if fast_expected_digest_match else "0",
        "sim_close_digest_stable": "1" if sim_close_digest_stable else "0",
        "validate_selection_stable": "1" if validate_selection_stable else "0",
        "fast_digest": first(fast_digests),
        "sim_close_digest": first(sim_close_digests),
        "fast_total_seconds_median": f"{fast_total_seconds_median:.6f}",
        "sim_close_wall_seconds_median": f"{sim_close_wall_seconds_median:.6f}",
        "validate_wall_seconds_median": f"{validate_wall_seconds_median:.6f}",
        "boxes_median": f"{boxes_median:.6f}",
        "cells_median": f"{cells_median:.6f}",
        "full_search_cells_median": f"{full_search_cells_median:.6f}",
        "cell_fraction_median": f"{cell_fraction_median:.6f}",
        "executor_seconds_median": f"{executor_seconds_median:.6f}",
        "fasim_records_median": f"{fasim_records_median:.6f}",
        "recovered_candidates_median": f"{recovered_candidates_median:.6f}",
        "recovered_accepted_median": f"{recovered_accepted_median:.6f}",
        "fasim_suppressed_median": f"{fasim_suppressed_median:.6f}",
        "sim_close_output_records_median": f"{output_records_median:.6f}",
        "recall_vs_sim_median": f"{recall_median:.6f}",
        "precision_vs_sim_median": f"{precision_median:.6f}",
        "extra_vs_sim_median": f"{extra_median:.6f}",
        "overlap_conflicts_median": f"{overlap_conflicts_median:.6f}",
        "fallbacks_median": f"{fallbacks_median:.6f}",
        "fast_mode_output_mutations": str(fast_mode_output_mutations),
        "sim_labels_production_inputs": "0",
        "recommendation": recommendation,
    }
    for key, value in telemetry.items():
        print(f"benchmark.fasim_sim_recovery_characterization.total.{key}={value}")

    return "\n".join(lines), telemetry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", default=str(ROOT / "fasim_longtarget_x86"))
    parser.add_argument("--profile-set", choices=("smoke", "small_medium", "representative"), default="smoke")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp" / "fasim_sim_recovery_real_mode_characterization"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_sim_recovery_real_mode_characterization.md"))
    parser.add_argument("--expected-fast-digest-file", default=str(ROOT / "tests" / "oracle_fasim_profile" / "sample_lite.digest"))
    args = parser.parse_args()

    try:
        bin_path = Path(args.bin)
        if not bin_path.is_absolute():
            bin_path = (ROOT / bin_path).resolve()
        if not bin_path.exists():
            raise RuntimeError(f"missing Fasim binary: {bin_path}")
        repeat = args.repeat if args.repeat > 0 else 1
        report, _ = characterize(
            bin_path=bin_path,
            profile_set=args.profile_set,
            repeat=repeat,
            work_dir=Path(args.work_dir),
            expected_digest_file=Path(args.expected_fast_digest_file),
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")
        print(report)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
