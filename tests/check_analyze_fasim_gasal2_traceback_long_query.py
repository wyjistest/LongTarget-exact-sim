#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts" / "analyze_fasim_gasal2_traceback_long_query.py"


METRICS = {
    "benchmark.fasim_gasal2_score_fill_seconds": 1.0,
    "benchmark.fasim_gasal2_score_submit_seconds": 0.1,
    "benchmark.fasim_gasal2_score_wait_seconds": 2.0,
    "benchmark.fasim_gasal2_score_poll_wait_seconds": 1.7,
    "benchmark.fasim_gasal2_score_result_copy_seconds": 0.3,
    "benchmark.fasim_gasal2_traceback_fill_seconds": 3.0,
    "benchmark.fasim_gasal2_traceback_submit_seconds": 0.2,
    "benchmark.fasim_gasal2_traceback_wait_seconds": 4.0,
    "benchmark.fasim_gasal2_traceback_poll_wait_seconds": 3.2,
    "benchmark.fasim_gasal2_traceback_result_copy_seconds": 0.8,
    "benchmark.fasim_gasal2_traceback_cigar_vector_seconds": 0.6,
    "benchmark.fasim_gasal2_traceback_cigar_string_seconds": 0.1,
    "benchmark.fasim_gasal2_cpu_traceback_convert_seconds": 5.0,
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds": 0.4,
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds": 0.5,
    "benchmark.fasim_gasal2_traceback_requests": 100,
    "benchmark.fasim_gasal2_traceback_batches": 2,
    "benchmark.fasim_gasal2_fallbacks": 0,
    "benchmark.fasim_gasal2_length_guard_fallbacks": 0,
}


def parse_key_values(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


class TracebackLongQueryAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_run(
        self,
        shift: int,
        run: int,
        wall: float,
        scale: float = 1.0,
        omit: str | None = None,
        overrides: dict[str, float] | None = None,
    ) -> None:
        run_dir = self.root / "grids" / f"shift_{shift}" / f"run_{run}"
        run_dir.mkdir(parents=True)
        values = dict(METRICS)
        if overrides:
            values.update(overrides)
        lines = []
        for key, value in values.items():
            if key == omit:
                continue
            if key.endswith("fallbacks"):
                scaled: float | int = value
            elif isinstance(value, int):
                scaled = int(value * scale)
            else:
                scaled = value * scale
            lines.append(f"{key}={scaled}")
        (run_dir / "stderr.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (run_dir / "wall_seconds.txt").write_text(f"{wall}\n", encoding="utf-8")

    def run_analyzer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(ANALYZER),
                "--run-root",
                str(self.root),
                "--details",
                str(self.root / "details.tsv"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_aggregates_host_timing_without_double_counting_nested_components(self) -> None:
        self.add_run(0, 0, 10.0)
        self.add_run(256, 0, 20.0, scale=2.0)

        result = self.run_analyzer()

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = parse_key_values(result.stdout)
        self.assertEqual(summary["runs"], "2")
        self.assertEqual(summary["grid_shifts"], "0,256")
        self.assertEqual(summary["end_to_end_seconds"], "30.000000")
        self.assertEqual(summary["traceback_requests"], "300")
        self.assertEqual(summary["traceback_score_prepass_seconds"], "9.300000")
        self.assertEqual(summary["traceback_pack_seconds"], "9.000000")
        self.assertEqual(summary["traceback_submit_seconds"], "0.600000")
        self.assertEqual(summary["traceback_host_wait_seconds"], "12.000000")
        self.assertEqual(summary["traceback_result_copy_seconds"], "2.400000")
        self.assertEqual(summary["traceback_cigar_materialize_seconds"], "2.100000")
        self.assertEqual(summary["traceback_convert_seconds"], "15.000000")
        self.assertEqual(summary["traceback_filter_dedup_cluster_seconds"], "2.700000")
        self.assertEqual(summary["traceback_host_observed_stage_seconds"], "36.600000")
        self.assertEqual(summary["traceback_h2d_seconds"], "unavailable")
        self.assertEqual(summary["traceback_kernel_seconds"], "unavailable")
        self.assertEqual(summary["traceback_d2h_seconds"], "unavailable")
        self.assertEqual(summary["device_timing_supported"], "0")
        self.assertEqual(summary["filter_dedup_cluster_scope"], "per_run_filter_sort_only")
        self.assertEqual(summary["timing_closure"], "clean")
        details = (self.root / "details.tsv").read_text(encoding="utf-8")
        self.assertIn("grid_shift\trun\twall_seconds", details)
        self.assertEqual(len(details.splitlines()), 3)

    def test_fails_closed_when_a_required_metric_is_missing(self) -> None:
        missing = "benchmark.fasim_gasal2_traceback_wait_seconds"
        self.add_run(0, 0, 10.0, omit=missing)

        result = self.run_analyzer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required metric traceback_wait_seconds", result.stderr)

    def test_fails_closed_when_wait_components_do_not_close(self) -> None:
        self.add_run(
            0,
            0,
            10.0,
            overrides={"benchmark.fasim_gasal2_traceback_poll_wait_seconds": 3.0},
        )

        result = self.run_analyzer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("traceback wait timing does not close", result.stderr)


if __name__ == "__main__":
    unittest.main()
