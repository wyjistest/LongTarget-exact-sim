#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPT = ROOT / "scripts/run_fasim_gasal2_paper_benchmarks.py"
MERGE_HELPER = ROOT / "scripts/run_fasim_gasal2_paper_archive_merge.py"
PHASE4_DRIVER = ROOT / "scripts/run_fasim_gasal2_paper_phase4.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("paper_harness_phase4", HARNESS_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load paper benchmark harness")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_phase4_driver():
    if not PHASE4_DRIVER.is_file():
        raise AssertionError("Phase 4 driver is missing")
    spec = importlib.util.spec_from_file_location("paper_phase4_driver", PHASE4_DRIVER)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load Phase 4 driver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def environment(command: list[str]) -> dict[str, str]:
    if not command or command[0] != "env":
        raise AssertionError(f"expected env command, got {command}")
    values: dict[str, str] = {}
    for item in command[1:]:
        if "=" not in item:
            break
        key, value = item.split("=", 1)
        values[key] = value
    return values


class PaperPhase4HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.binary = self.work / "fasim"
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.run_dir = self.work / "run"
        self.binary.write_text("", encoding="utf-8")
        self.query.write_text(">q\nACGT\n", encoding="utf-8")
        self.target.write_text(">t\nACGT\n", encoding="utf-8")
        self.module = load_harness()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def row(self, adapter: str, workload: str) -> dict[str, str]:
        return {
            "adapter_id": adapter,
            "workload_id": workload,
            "rule": "0",
        }

    def command(self, row: dict[str, str], mode: str) -> list[str]:
        return self.module.adapter_command(
            row,
            mode,
            self.binary,
            self.query,
            self.target,
            self.run_dir,
        )

    def test_real_archive_pair_changes_only_archive_output_mode(self) -> None:
        row = self.row("archive_pair", "c5_archive_h19_2mb")

        baseline = environment(self.command(row, "baseline"))
        candidate = environment(self.command(row, "candidate"))

        self.assertEqual(baseline["FASIM_OUTPUT_MODE"], "tfosorted")
        self.assertEqual(candidate["FASIM_OUTPUT_MODE"], "tfosorted")
        self.assertEqual(baseline["FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT"], "0")
        self.assertEqual(candidate["FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT"], "1")
        for key in self.module.base_gasal2_env():
            self.assertEqual(baseline[key], candidate[key])

    def test_exact_column_candidate_uses_checked_pruned_scoreinfo_flags(self) -> None:
        row = self.row("exact_column_pair", "c6_exact_h19_2mb")

        baseline = environment(self.command(row, "baseline"))
        candidate = environment(self.command(row, "candidate"))

        self.assertEqual(baseline["FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT"], "1")
        self.assertNotIn("FASIM_EXACT_COLUMN_SCOREINFO_GPU", baseline)
        self.assertEqual(candidate["FASIM_EXACT_COLUMN_SCOREINFO_GPU"], "1")
        self.assertEqual(candidate["FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK"], "512")
        self.assertEqual(candidate["FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT"], "1")

    def test_synthetic_archive_pair_uses_phase4_merge_helper(self) -> None:
        row = self.row("archive_pair", "c5_archive_large_synthetic")

        command = self.command(row, "candidate")

        self.assertIn(str(ROOT / "scripts/run_fasim_gasal2_paper_archive_merge.py"), command)
        self.assertIn("--backend", command)
        self.assertIn("sqlite", command)
        self.assertIn("--rows", command)
        self.assertIn("150000", command)

    def test_merge_helper_emits_exact_output_and_machine_readable_metrics(self) -> None:
        output = self.work / "synthetic-output.tsv"

        result = subprocess.run(
            [
                sys.executable,
                str(MERGE_HELPER),
                "--backend",
                "memory",
                "--rows",
                "100",
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        self.assertEqual(values["backend"], "memory")
        self.assertEqual(values["input_rows"], "100")
        self.assertEqual(values["output_rows"], "100")
        self.assertEqual(values["dedup_backend"], "memory")
        self.assertGreater(float(values["merge_wall_seconds"]), 0)
        self.assertTrue(output.is_file())

    def test_phase4_plan_is_frozen_to_four_rows_and_twelve_pairs(self) -> None:
        module = load_phase4_driver()
        rows = [
            {
                "workload_id": workload,
                "claim_id": claim,
                "adapter_id": adapter,
                "required_pairs": "3",
                "preset_id": preset,
            }
            for workload, claim, adapter, preset in (
                ("c5_archive_h19_2mb", "C5", "archive_pair", "archive_first_exact_restore_v1"),
                ("c5_archive_large_synthetic", "C5", "archive_pair", "archive_merge_large_synthetic_v1"),
                ("c6_exact_h19_2mb", "C6", "exact_column_pair", "exact_column_safe_v1"),
                ("c6_exact_kcnq_segment_chr22", "C6", "exact_column_pair", "exact_column_safe_v1"),
            )
        ]

        plan = module.build_phase4_plan(rows, seed=20260715)

        self.assertEqual(plan["workload_count"], 4)
        self.assertEqual(plan["pair_count"], 12)
        self.assertEqual(plan["timed_run_count"], 24)
        self.assertEqual(plan["warmup_count"], 8)

    def test_exact_telemetry_reports_stage_work_and_fallbacks(self) -> None:
        module = load_phase4_driver()
        stderr = self.work / "exact.stderr"
        stderr.write_text(
            "\n".join(
                (
                    "benchmark.fasim_top5_gasal2_phase_exact_column_batches=2",
                    "benchmark.fasim_top5_gasal2_phase_exact_column_tasks=100",
                    "benchmark.fasim_top5_gasal2_phase_exact_column_cells=1000",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches=0",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks=0",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells=0",
                    "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds=3.5",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=0",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches=0",
                    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches=0",
                    "benchmark.fasim_gasal2_requests=200",
                    "benchmark.fasim_gasal2_traceback_requests=80",
                    "benchmark.fasim_gasal2_fallbacks=0",
                )
            )
            + "\n",
            encoding="utf-8",
        )

        metrics = module.exact_metrics(stderr)

        self.assertEqual(metrics["exact_tasks"], 100)
        self.assertEqual(metrics["exact_cells"], 1000)
        self.assertEqual(metrics["exact_stage_seconds"], 3.5)
        self.assertEqual(metrics["gasal2_requests"], 200)
        self.assertEqual(metrics["traceback_requests"], 80)
        self.assertEqual(metrics["fallbacks"], 0)
        self.assertEqual(metrics["overflow_batches"], 0)

    def test_exact_contract_requires_output_work_and_request_equality(self) -> None:
        module = load_phase4_driver()
        baseline = {
            "exact_tasks": 100,
            "exact_cells": 1000,
            "exact_stage_seconds": 4.0,
            "gasal2_requests": 200,
            "traceback_requests": 80,
            "fallbacks": 0,
            "overflow_batches": 0,
        }
        candidate = {**baseline, "exact_stage_seconds": 2.0}

        clean = module.evaluate_exact_contract(
            baseline,
            candidate,
            full_output_byte_equal=True,
            all_three_top5_equal=True,
            boundary_ties_equal=True,
        )
        drifted = module.evaluate_exact_contract(
            baseline,
            {**candidate, "exact_tasks": 99},
            full_output_byte_equal=True,
            all_three_top5_equal=True,
            boundary_ties_equal=True,
        )

        self.assertEqual(clean["status"], "clean")
        self.assertEqual(clean["exact_stage_speedup"], 2.0)
        self.assertEqual(clean["exact_work_equal"], 1)
        self.assertEqual(clean["request_counts_equal"], 1)
        self.assertEqual(drifted["status"], "mismatch")
        self.assertEqual(drifted["exact_work_equal"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
