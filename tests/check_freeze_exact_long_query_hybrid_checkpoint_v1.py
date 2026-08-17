#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/freeze_exact_long_query_hybrid_checkpoint_v1.py"
SPEC = importlib.util.spec_from_file_location("freeze_checkpoint", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FreezeCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="exact-hybrid-freeze-")
        self.path = Path(self.temp.name) / "consumer.tsv"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def row(self, task_index: int, groups: int) -> dict[str, str]:
        values = {field: "0" for field in MODULE.CONSUMER_FIELDS}
        selected = groups
        values.update({
            "task_index": str(task_index),
            "execution_mode": "replacement_prototype",
            "authority_comparison_available": "0",
            "validation_enabled": "0",
            "ok": "1",
            "output_equal": "-1",
            "scoreinfo_groups": str(groups),
            "attempts": str(4 * groups),
            "gpu_scored_attempts": str(4 * groups),
            "endpoint_batches": str(int(groups > 0)),
            "control_selected_attempts": str(selected),
            "consumer_selection_equal": str(int(groups > 0)),
            "consumer_attempt_prefix_equal": str(int(groups > 0)),
            "cpu_continuation_requested": str(int(groups > 0)),
            "cpu_continuation_active": str(int(groups > 0)),
            "cpu_continuation_calls": str(selected),
            "replay_attempts": str(selected),
            "cpu_align_attempts": str(selected),
            "threshold_groups": str(groups),
            "score_seconds": "0.5",
            "gpu_kernel_seconds": "0.4",
            "h2d_seconds": "0.01",
            "d2h_seconds": "0.01",
            "select_seconds": "0.02",
            "traceback_seconds": "0.3",
            "convert_seconds": "0.1",
            "total_seconds": "1.0",
            "first_attempt_mismatch": "none",
            "first_consumer_mismatch": "none",
            "error": "none",
        })
        return values

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

    def test_verifies_complete_gpu_coverage_and_selected_cpu_continuation(self) -> None:
        self.write([self.row(0, 2), self.row(1, 0)])

        result = MODULE.verify_consumer(self.path, expected_tasks=2)

        self.assertEqual(result["task_rows"], 2)
        self.assertEqual(result["scoreinfo_groups"], 2)
        self.assertEqual(result["attempts"], 8)
        self.assertEqual(result["gpu_scored_attempts"], 8)
        self.assertEqual(result["cpu_oracle_attempts"], 0)
        self.assertEqual(result["cpu_continuation_calls"], 2)

    def test_rejects_all_attempt_cpu_oracle_activity(self) -> None:
        row = self.row(0, 1)
        row["cpu_oracle_attempts"] = "1"
        self.write([row])

        with self.assertRaises(MODULE.FreezeError):
            MODULE.verify_consumer(self.path, expected_tasks=1)

    def test_rejects_noncontiguous_task_indices(self) -> None:
        self.write([self.row(1, 1)])

        with self.assertRaises(MODULE.FreezeError):
            MODULE.verify_consumer(self.path, expected_tasks=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
