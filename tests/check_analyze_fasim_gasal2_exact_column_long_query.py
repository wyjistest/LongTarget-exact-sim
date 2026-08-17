#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts" / "analyze_fasim_gasal2_exact_column_long_query.py"


def parse_metrics(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class ExactColumnLongQueryAnalyzerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase5-profile-")
        self.work = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_run(
        self,
        shift: int,
        index: int,
        *,
        wall: float,
        batches: int,
        compact_batches: int,
        tasks: int,
        cells: int,
        stage: float,
        kernel: float,
        h2d: float,
        d2h: float,
        column_pruned: int = 0,
        compact_stage: float = 0.0,
        compact_kernel: float = 0.0,
        compact_h2d: float = 0.0,
        compact_d2h: float = 0.0,
    ) -> None:
        run = self.work / "grids" / f"shift_{shift}" / f"run_{index}"
        run.mkdir(parents=True)
        (run / "wall_seconds.txt").write_text(f"{wall}\n", encoding="utf-8")
        values = {
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled": column_pruned,
            "benchmark.fasim_top5_gasal2_phase_exact_column_batches": batches,
            "benchmark.fasim_top5_gasal2_phase_exact_column_tasks": tasks,
            "benchmark.fasim_top5_gasal2_phase_exact_column_cells": cells,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches": compact_batches,
            "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds": stage,
            "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds": kernel,
            "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds": h2d,
            "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds": d2h,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds": compact_stage,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds": compact_kernel,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds": compact_h2d,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds": compact_d2h,
            "benchmark.fasim_gasal2_fallbacks": 0,
        }
        (run / "stderr.log").write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )

    def run_analyzer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(ANALYZER), "--run-root", str(self.work)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_aggregates_nested_grids_and_classifies_material_exact_stage(self) -> None:
        self.write_run(
            0,
            0,
            wall=20.0,
            batches=2,
            compact_batches=0,
            tasks=200,
            cells=1_000_000,
            stage=2.5,
            kernel=1.5,
            h2d=0.2,
            d2h=0.3,
        )
        self.write_run(
            256,
            0,
            wall=30.0,
            batches=3,
            compact_batches=0,
            tasks=300,
            cells=1_500_000,
            stage=3.5,
            kernel=2.0,
            h2d=0.2,
            d2h=0.5,
        )

        result = self.run_analyzer()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = parse_metrics(result.stdout)
        self.assertEqual(values["runs"], "2")
        self.assertEqual(values["grid_shifts"], "0,256")
        self.assertEqual(values["end_to_end_seconds"], "50.000000")
        self.assertEqual(values["exact_stage_seconds"], "6.000000")
        self.assertEqual(values["exact_stage_percent"], "12.00")
        self.assertEqual(values["exact_kernel_seconds"], "3.500000")
        self.assertEqual(values["exact_kernel_percent_of_stage"], "58.33")
        self.assertEqual(values["exact_h2d_seconds"], "0.400000")
        self.assertEqual(values["exact_d2h_seconds"], "0.800000")
        self.assertEqual(values["exact_batches"], "5")
        self.assertEqual(values["exact_launches"], "5")
        self.assertEqual(values["exact_tasks_before"], "500")
        self.assertEqual(values["exact_tasks_after"], "500")
        self.assertEqual(values["exact_tasks_dropped_identical"], "0")
        self.assertEqual(values["exact_cells_before"], "2500000")
        self.assertEqual(values["exact_cells_after"], "2500000")
        self.assertEqual(values["kernel_variant"], "column_maxima_cpu_scoreinfo")
        self.assertEqual(values["entry_gate"], "material")

    def test_counts_the_compact_kernel_as_a_second_launch(self) -> None:
        self.write_run(
            0,
            0,
            wall=10.0,
            batches=4,
            compact_batches=4,
            tasks=40,
            cells=200_000,
            stage=0.5,
            kernel=0.3,
            h2d=0.05,
            d2h=0.02,
            column_pruned=1,
            compact_stage=0.15,
            compact_kernel=0.08,
            compact_d2h=0.03,
        )

        result = self.run_analyzer()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = parse_metrics(result.stdout)
        self.assertEqual(values["exact_launches"], "8")
        self.assertEqual(values["exact_stage_seconds"], "0.650000")
        self.assertEqual(values["exact_kernel_seconds"], "0.380000")
        self.assertEqual(values["kernel_variant"], "column_scoreinfo_pruned_fused")
        self.assertEqual(values["entry_gate"], "no_go_low_ceiling")

    def test_fails_closed_when_a_required_metric_is_missing(self) -> None:
        self.write_run(
            0,
            0,
            wall=10.0,
            batches=1,
            compact_batches=0,
            tasks=10,
            cells=50_000,
            stage=2.0,
            kernel=1.0,
            h2d=0.1,
            d2h=0.2,
        )
        stderr_path = self.work / "grids" / "shift_0" / "run_0" / "stderr.log"
        lines = [
            line
            for line in stderr_path.read_text(encoding="utf-8").splitlines()
            if "exact_column_cells" not in line
        ]
        stderr_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = self.run_analyzer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact_cells", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
