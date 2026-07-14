#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts" / "analyze_fasim_gasal2_multi_segment_setup.py"


def parse_metrics(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class MultiSegmentSetupAnalyzerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase3-profile-")
        self.work = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_run(
        self,
        index: int,
        *,
        wall: float,
        flush: float,
        score_requests: int,
        traceback_requests: int,
    ) -> None:
        run = self.work / f"run_{index}"
        run.mkdir()
        (run / "wall_seconds.txt").write_text(f"{wall}\n", encoding="utf-8")
        values = {
            "benchmark.fasim_top5_gasal2_phase_fasta_read_seconds": 1.0 + index,
            "benchmark.fasim_top5_gasal2_phase_cut_sequence_seconds": 0.1,
            "benchmark.fasim_top5_gasal2_phase_transfer_string_seconds": 2.0,
            "benchmark.fasim_top5_gasal2_phase_transfer_table_seconds": 1.9,
            "benchmark.fasim_top5_gasal2_phase_src_transform_seconds": 3.0,
            "benchmark.fasim_top5_gasal2_phase_encode_seconds": 4.0,
            "benchmark.fasim_top5_gasal2_phase_cuda_query_init_seconds": 0.5,
            "benchmark.fasim_top5_gasal2_phase_flush_total_seconds": flush,
            "benchmark.fasim_gasal2_init_seconds": 0.25,
            "benchmark.fasim_gasal2_fill_seconds": 0.75,
            "benchmark.fasim_gasal2_score_target_bytes": 1000 + index,
            "benchmark.fasim_gasal2_traceback_target_bytes": 2000 + index,
            "benchmark.fasim_gasal2_score_requests": score_requests,
            "benchmark.fasim_gasal2_traceback_requests": traceback_requests,
            "benchmark.fasim_gasal2_fallbacks": 0,
        }
        (run / "stderr.log").write_text(
            "".join(f"{key}={value}\n" for key, value in values.items()),
            encoding="utf-8",
        )

    def test_aggregates_nonoverlapping_setup_and_marks_missing_counts_unavailable(self) -> None:
        self.write_run(0, wall=20.0, flush=15.0, score_requests=100, traceback_requests=40)
        self.write_run(1, wall=30.0, flush=22.0, score_requests=120, traceback_requests=50)
        result = subprocess.run(
            ["python3", str(ANALYZER), "--run-root", str(self.work)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = parse_metrics(result.stdout)
        self.assertEqual(values["segments"], "2")
        self.assertEqual(values["processes"], "2")
        self.assertEqual(values["target_read_passes"], "2")
        self.assertEqual(values["wall_seconds"], "50.000000")
        self.assertEqual(values["flush_total_seconds"], "37.000000")
        self.assertEqual(values["nonflush_wall_seconds"], "13.000000")
        # transfer_table is nested inside transfer_string and must not be added twice.
        self.assertEqual(values["host_setup_observed_seconds"], "22.200000")
        self.assertEqual(values["gasal2_init_seconds"], "0.500000")
        self.assertEqual(values["gasal2_target_batch_bytes"], "6002")
        self.assertEqual(values["score_requests_min"], "100")
        self.assertEqual(values["score_requests_max"], "120")
        self.assertEqual(values["target_batches_query_dependent"], "1")
        self.assertEqual(values["target_h2d_copy_count"], "unavailable")
        self.assertEqual(values["device_alloc_count"], "unavailable")
        self.assertEqual(values["device_alloc_bytes"], "unavailable")
        self.assertEqual(values["workspace_initializations"], "unavailable")

    def test_fails_closed_when_a_required_metric_is_missing(self) -> None:
        self.write_run(0, wall=20.0, flush=15.0, score_requests=100, traceback_requests=40)
        stderr_path = self.work / "run_0" / "stderr.log"
        lines = [
            line
            for line in stderr_path.read_text(encoding="utf-8").splitlines()
            if "score_target_bytes" not in line
        ]
        stderr_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = subprocess.run(
            ["python3", str(ANALYZER), "--run-root", str(self.work)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("score_target_bytes", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
