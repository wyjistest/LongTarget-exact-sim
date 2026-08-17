#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARIZER = ROOT / "scripts" / "summarize_fasim_gasal2_long_query_integrated.py"


FIELDS = [
    "workload",
    "repeat",
    "baseline_pipeline_wall_seconds",
    "candidate_pipeline_wall_seconds",
    "baseline_exact_stage_seconds",
    "candidate_exact_stage_seconds",
    "baseline_traceback_stage_seconds",
    "candidate_traceback_stage_seconds",
    "baseline_gasal2_requests",
    "candidate_gasal2_requests",
    "baseline_traceback_requests",
    "candidate_traceback_requests",
    "exact_work_tasks",
    "exact_work_cells",
    "baseline_archive_bytes",
    "candidate_archive_bytes",
    "baseline_peak_rss_kb",
    "candidate_peak_rss_kb",
    "full_output_byte_equal",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "offline_clustered_top5_equal",
    "archive_restore_clean",
    "temporary_text_bytes",
    "fallbacks",
    "oom",
    "decision",
]


def row(workload: str, repeat: int, baseline: float, candidate: float) -> dict[str, str]:
    return {
        "workload": workload,
        "repeat": str(repeat),
        "baseline_pipeline_wall_seconds": str(baseline),
        "candidate_pipeline_wall_seconds": str(candidate),
        "baseline_exact_stage_seconds": "20",
        "candidate_exact_stage_seconds": "10",
        "baseline_traceback_stage_seconds": "30",
        "candidate_traceback_stage_seconds": "30",
        "baseline_gasal2_requests": "1000",
        "candidate_gasal2_requests": "1000",
        "baseline_traceback_requests": "400",
        "candidate_traceback_requests": "400",
        "exact_work_tasks": "200",
        "exact_work_cells": "1000000",
        "baseline_archive_bytes": "4096",
        "candidate_archive_bytes": "4096",
        "baseline_peak_rss_kb": "50000",
        "candidate_peak_rss_kb": "51000",
        "full_output_byte_equal": "1",
        "top5_score_equal": "1",
        "top5_stability_equal": "1",
        "top5_nt_score_equal": "1",
        "offline_clustered_top5_equal": "1",
        "archive_restore_clean": "1",
        "temporary_text_bytes": "0",
        "fallbacks": "0",
        "oom": "0",
        "decision": "paired_integrated_contract_clean",
    }


class IntegratedSummarizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="fasim-phase7-summary-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_pairs(self, rows: list[dict[str, str]]) -> Path:
        path = self.root / "pairs.tsv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def run_summary(self, pairs: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(SUMMARIZER),
                "--pairs",
                str(pairs),
                "--details",
                str(self.root / "details.tsv"),
                "--summary",
                str(self.root / "summary.txt"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_allows_full_run_only_after_stable_max8_gate(self) -> None:
        pairs = self.write_pairs(
            [
                row("small", 1, 10.0, 9.0),
                row("max4", 1, 50.0, 44.0),
                row("max8", 1, 100.0, 85.0),
                row("max8", 2, 102.0, 88.0),
                row("h19_short", 1, 10.0, 10.2),
            ]
        )

        result = self.run_summary(pairs)

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = dict(
            line.split("=", 1)
            for line in (self.root / "summary.txt").read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        self.assertEqual(summary["max8_repeats"], "2")
        self.assertEqual(summary["max8_direction_stable"], "1")
        self.assertEqual(summary["max8_full_run_allowed"], "1")
        self.assertEqual(summary["short_query_regression_gate"], "1")
        self.assertEqual(summary["all_pair_contracts_clean"], "1")
        self.assertAlmostEqual(float(summary["max8_median_wall_reduction_percent"]), 14.356436, places=5)

    def test_denies_full_run_when_max8_direction_is_not_stable(self) -> None:
        pairs = self.write_pairs(
            [
                row("max8", 1, 100.0, 80.0),
                row("max8", 2, 100.0, 101.0),
                row("h19_short", 1, 10.0, 10.0),
            ]
        )

        result = self.run_summary(pairs)

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = dict(
            line.split("=", 1)
            for line in (self.root / "summary.txt").read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        self.assertEqual(summary["max8_direction_stable"], "0")
        self.assertEqual(summary["max8_full_run_allowed"], "0")

    def test_fails_closed_on_dirty_pair_contract(self) -> None:
        dirty = row("max8", 1, 100.0, 80.0)
        dirty["top5_nt_score_equal"] = "0"
        pairs = self.write_pairs([dirty])

        result = self.run_summary(pairs)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract", result.stderr.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
