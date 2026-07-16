#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reproduce/analyze_results.py"


def load_module():
    if not SCRIPT.is_file():
        raise AssertionError("paper result analyzer is missing")
    spec = importlib.util.spec_from_file_location("paper_result_analyzer", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load paper result analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pair(workload: str, pair_id: int, baseline: float, candidate: float) -> dict[str, str]:
    return {
        "data_freeze_id": "paper-data-v1-test-20260716",
        "runtime_epoch": "0",
        "runtime_commit": "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f",
        "machine_id": "machine-test",
        "workload_id": workload,
        "claim_id": "C1",
        "pair_id": str(pair_id),
        "pair_id_text": f"{workload}__pair{pair_id:02d}__0",
        "preset_id": "preset-v1",
        "output_contract": "fast_topk_score_stability_nt",
        "baseline_wall_seconds": str(baseline),
        "candidate_wall_seconds": str(candidate),
        "paired_speedup": str(baseline / candidate),
        "status": "clean",
        "excluded": "0",
        "exclusion_reason": "NA",
    }


class PaperResultAnalyzerTests(unittest.TestCase):
    def test_bootstrap_median_interval_is_seed_reproducible(self) -> None:
        module = load_module()

        first = module.bootstrap_median_ci([1.0, 2.0, 4.0], seed=20260715, resamples=10000)
        second = module.bootstrap_median_ci([1.0, 2.0, 4.0], seed=20260715, resamples=10000)

        self.assertEqual(first, second)
        self.assertLessEqual(first[0], 2.0)
        self.assertGreaterEqual(first[1], 2.0)

    def test_fewer_than_three_pairs_has_no_bootstrap_interval(self) -> None:
        module = load_module()

        interval = module.bootstrap_median_ci([1.0, 2.0], seed=20260715, resamples=10000)

        self.assertEqual(interval, ("NA", "NA"))

    def test_summary_recomputes_speedup_and_rejects_duplicate_pairs(self) -> None:
        module = load_module()
        rows = [
            pair("w1", 1, 10, 5),
            pair("w1", 2, 12, 6),
            pair("w1", 3, 14, 7),
        ]

        summary = module.summarize_pairs(rows, seed=20260715, resamples=10000)[0]

        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["median_paired_speedup"], 2.0)
        with self.assertRaisesRegex(ValueError, "duplicate pair"):
            module.summarize_pairs([rows[0], rows[0]], seed=20260715, resamples=10000)

    def test_summary_fails_on_speedup_arithmetic_drift(self) -> None:
        module = load_module()
        row = pair("w1", 1, 10, 5)
        row["paired_speedup"] = "3"

        with self.assertRaisesRegex(ValueError, "speedup arithmetic"):
            module.summarize_pairs([row], seed=20260715, resamples=10000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
