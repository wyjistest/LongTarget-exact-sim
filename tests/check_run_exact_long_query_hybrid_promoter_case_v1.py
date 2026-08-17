#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_exact_long_query_hybrid_promoter_case_v1.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("run_promoter_case", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PromoterCaseConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="promoter-consumer-")
        self.path = Path(self.temp.name) / "consumer.tsv"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def row(self, index: int, groups: int) -> dict[str, str]:
        row = {field: "0" for field in MODULE.CONSUMER_FIELDS}
        active = int(groups > 0)
        row.update({
            "task_index": str(index),
            "execution_mode": "replacement_prototype",
            "ok": "1",
            "output_equal": "-1",
            "scoreinfo_groups": str(groups),
            "attempts": str(4 * groups),
            "gpu_scored_attempts": str(4 * groups),
            "endpoint_batches": str(active),
            "control_selected_attempts": str(groups),
            "consumer_selection_equal": str(active),
            "consumer_attempt_prefix_equal": str(active),
            "cpu_continuation_requested": str(active),
            "cpu_continuation_active": str(active),
            "cpu_continuation_calls": str(groups),
            "cpu_align_attempts": str(groups),
            "threshold_groups": str(groups),
            "score_seconds": "0.1",
            "gpu_kernel_seconds": "0.08",
            "h2d_seconds": "0.01",
            "d2h_seconds": "0.01",
            "select_seconds": "0.01",
            "traceback_seconds": "0.1",
            "convert_seconds": "0.01",
            "total_seconds": "0.25",
            "first_attempt_mismatch": "none",
            "first_consumer_mismatch": "none",
            "error": "none",
        })
        return row

    def write(self, rows: list[dict[str, str]]) -> None:
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=MODULE.CONSUMER_FIELDS,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_streams_complete_consumer_report(self) -> None:
        self.write([self.row(0, 3), self.row(1, 0)])
        result = MODULE.summarize_consumer(self.path)
        self.assertEqual(result["task_rows"], 2)
        self.assertEqual(result["scoreinfo_groups"], 3)
        self.assertEqual(result["attempts"], 12)
        self.assertEqual(result["cpu_oracle_attempts"], 0)
        self.assertEqual(result["cpu_continuation_calls"], 3)

    def test_rejects_missing_gpu_attempt(self) -> None:
        row = self.row(0, 1)
        row["gpu_scored_attempts"] = "3"
        self.write([row])
        with self.assertRaises(MODULE.CaseError):
            MODULE.summarize_consumer(self.path)

    def test_runtime_environment_does_not_inherit_fasim_state(self) -> None:
        key = "FASIM_UNRELATED_PARENT_STATE"
        previous = os.environ.get(key)
        os.environ[key] = "must-not-leak"
        try:
            baseline = MODULE.runtime_environment("baseline", 1, self.path)
            candidate = MODULE.runtime_environment("candidate", 0, self.path)
        finally:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        self.assertNotIn(key, baseline)
        self.assertNotIn(key, candidate)
        self.assertEqual(baseline["FASIM_ALIGN_GASAL2"], "0")
        self.assertEqual(candidate["FASIM_ALIGN_GASAL2"], "1")
        self.assertEqual(
            candidate["FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT"],
            str(self.path),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
