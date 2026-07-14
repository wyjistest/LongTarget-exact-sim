#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARIZER = ROOT / "scripts" / "summarize_fasim_gasal2_exact_column_benchmark.py"


def parse_metrics(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class ExactColumnBenchmarkSummarizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase5-benchmark-")
        self.work = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_run(
        self,
        mode: str,
        index: int,
        *,
        wall: float,
        exact_stage: float,
        exact_kernel: float,
        tasks: int = 100,
        cells: int = 500_000,
        compact_stage: float = 0.0,
        compact_kernel: float = 0.0,
        compact_batches: int = 0,
        overflow: int = 0,
        fallback: int = 0,
        digest: str = "abc123",
        scoreinfo_only: bool = False,
    ) -> None:
        run = self.work / mode / f"run_{index}"
        run.mkdir(parents=True)
        (run / "wall_seconds.txt").write_text(f"{wall}\n", encoding="utf-8")
        (run / "output.sha256").write_text(f"{digest}\n", encoding="utf-8")
        values = {
            "benchmark.fasim_top5_gasal2_phase_exact_column_batches": 2,
            "benchmark.fasim_top5_gasal2_phase_exact_column_tasks": 0 if scoreinfo_only else tasks,
            "benchmark.fasim_top5_gasal2_phase_exact_column_cells": 0 if scoreinfo_only else cells,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches": compact_batches,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks": tasks if scoreinfo_only else 0,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells": cells if scoreinfo_only else 0,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches": overflow,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches": fallback,
            "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds": exact_stage,
            "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds": exact_kernel,
            "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds": 0.1,
            "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds": 0.2,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds": compact_stage,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds": compact_kernel,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds": 0.0,
            "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds": 0.05,
            "benchmark.fasim_gasal2_fallbacks": fallback,
        }
        (run / "stderr.log").write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )

    def run_summarizer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(SUMMARIZER),
                "--baseline-root",
                str(self.work / "baseline"),
                "--candidate-root",
                str(self.work / "candidate"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_computes_repeat_medians_and_strong_go(self) -> None:
        for index, (wall, stage, kernel) in enumerate(
            ((10.0, 2.5, 1.5), (12.0, 2.4, 1.4), (11.0, 2.6, 1.6)), 1
        ):
            self.write_run(
                "baseline", index, wall=wall, exact_stage=stage, exact_kernel=kernel
            )
        for index, (wall, stage, kernel, compact, compact_kernel) in enumerate(
            (
                (8.5, 1.6, 1.1, 0.2, 0.1),
                (9.0, 1.7, 1.2, 0.2, 0.1),
                (8.0, 1.5, 1.0, 0.2, 0.1),
            ),
            1,
        ):
            self.write_run(
                "candidate",
                index,
                wall=wall,
                exact_stage=stage,
                exact_kernel=kernel,
                compact_stage=compact,
                compact_kernel=compact_kernel,
                compact_batches=2,
                scoreinfo_only=True,
            )

        result = self.run_summarizer()

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = parse_metrics(result.stdout)
        self.assertEqual(values["runs"], "3")
        self.assertEqual(values["baseline_wall_median_seconds"], "11.000000")
        self.assertEqual(values["candidate_wall_median_seconds"], "8.500000")
        self.assertEqual(values["wall_reduction_percent"], "22.73")
        self.assertEqual(values["speedup"], "1.294118")
        self.assertEqual(values["baseline_exact_stage_median_seconds"], "2.500000")
        self.assertEqual(values["candidate_exact_stage_median_seconds"], "1.800000")
        self.assertEqual(values["exact_stage_reduction_percent"], "28.00")
        self.assertEqual(values["exact_tasks_equal_all"], "1")
        self.assertEqual(values["exact_cells_equal_all"], "1")
        self.assertEqual(values["full_output_sha_equal_all"], "1")
        self.assertEqual(values["fallbacks"], "0")
        self.assertEqual(values["overflow_batches"], "0")
        self.assertEqual(values["promotion_gate"], "strong_go")

    def test_fails_closed_on_output_digest_mismatch(self) -> None:
        self.write_run("baseline", 1, wall=10, exact_stage=2, exact_kernel=1)
        self.write_run(
            "candidate",
            1,
            wall=8,
            exact_stage=1,
            exact_kernel=0.5,
            digest="different",
        )

        result = self.run_summarizer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output digest mismatch", result.stderr)

    def test_fails_closed_on_task_count_mismatch(self) -> None:
        self.write_run("baseline", 1, wall=10, exact_stage=2, exact_kernel=1)
        self.write_run(
            "candidate", 1, wall=8, exact_stage=1, exact_kernel=0.5, tasks=99
        )

        result = self.run_summarizer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact task mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
