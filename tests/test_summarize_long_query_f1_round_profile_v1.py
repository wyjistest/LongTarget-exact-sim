#!/usr/bin/env python3

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "summarize_long_query_f1_round_profile_v1.py"
SPEC = importlib.util.spec_from_file_location("round_profile_summary", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RoundProfileSummaryTests(unittest.TestCase):
    def write_report(self, rows):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "f1.tsv"
        fields = [
            "task_index",
            "ok",
            "cpu_continuation_failures",
            "gpu_kernel_seconds",
            "round_profile_active",
            "round_profile_owner",
            "error",
            *MODULE.COUNT_COLUMNS,
            *MODULE.TIME_COLUMNS,
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        return directory, path

    @staticmethod
    def base_row(task_index, owner):
        row = {
            "task_index": str(task_index),
            "ok": "1",
            "cpu_continuation_failures": "0",
            "gpu_kernel_seconds": "0.0",
            "round_profile_active": "1",
            "round_profile_owner": "1" if owner else "0",
            "error": "none",
            "round_active_groups": "10,2,0",
            "round_forward_attempts": "10,2,0",
            "round_reverse_requests": "8,1,1",
        }
        for name in MODULE.TIME_COLUMNS:
            row[name] = "0,0,0" if owner else ""
        return row

    def test_valid_owner_profiles_sum_to_aggregate(self):
        owner = self.base_row(0, True)
        owner["round_forward_gpu_seconds"] = "3,1,0"
        owner["round_reverse_gpu_seconds"] = "1,0.5,0.5"
        owner["round_host_descriptor_seconds"] = "0.1,0.1,0"
        owner["gpu_kernel_seconds"] = "3.0"
        other = self.base_row(1, False)
        other["gpu_kernel_seconds"] = "3.0"
        directory, path = self.write_report([owner, other])
        self.addCleanup(directory.cleanup)

        summary = MODULE.summarize(path)

        self.assertEqual(summary["decision"], "round_profile_pass")
        self.assertEqual(summary["owner_task_indexes"], [0])
        self.assertEqual(summary["rounds"][0]["active_groups"], 20)
        self.assertAlmostEqual(summary["profile_gpu_seconds"], 6.0)
        self.assertAlmostEqual(summary["profiled_host_seconds"], 0.2)

    def test_non_owner_profile_values_fail_closed(self):
        owner = self.base_row(0, True)
        other = self.base_row(1, False)
        other["round_forward_gpu_seconds"] = "1,0,0"
        owner["gpu_kernel_seconds"] = "0.0"
        directory, path = self.write_report([owner, other])
        self.addCleanup(directory.cleanup)

        summary = MODULE.summarize(path)

        self.assertEqual(summary["decision"], "round_profile_no_go")
        self.assertTrue(
            any("non_owner_has_profile_values" in item for item in summary["failures"])
        )

    def test_gpu_sum_mismatch_fails_closed(self):
        owner = self.base_row(0, True)
        owner["round_forward_gpu_seconds"] = "1,0,0"
        owner["gpu_kernel_seconds"] = "2.0"
        directory, path = self.write_report([owner])
        self.addCleanup(directory.cleanup)

        summary = MODULE.summarize(path)

        self.assertIn("round_gpu_sum_differs_from_aggregate", summary["failures"])


if __name__ == "__main__":
    unittest.main()
