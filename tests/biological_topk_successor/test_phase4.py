from __future__ import annotations

import csv
import gzip
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/fresh-holdout"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class SuccessorPhase4Tests(unittest.TestCase):
    def test_all_attempts_are_terminal_successes_before_comparison(self) -> None:
        summary = load_json(ARTIFACT_ROOT / "run-summary.json")
        self.assertEqual(summary["status"], "complete_success")
        self.assertEqual(summary["planned_attempt_count"], 368)
        self.assertEqual(summary["terminal_attempt_count"], 368)
        self.assertEqual(summary["successful_attempt_count"], 368)
        self.assertEqual(summary["technical_failure_count"], 0)
        self.assertFalse(summary["comparison_started"])

    def test_every_g_telemetry_is_deterministic_lossless_gzip(self) -> None:
        archives = sorted(ARTIFACT_ROOT.glob("*/telemetry.json.gz"))
        self.assertEqual(len(archives), 184)
        self.assertFalse(list(ARTIFACT_ROOT.glob("*/telemetry.json")))
        for archive in archives:
            receipt = load_json(archive.parent / "attempt-complete.json")
            metadata = receipt["telemetry_storage"]
            compressed = archive.read_bytes()
            self.assertEqual(compressed[4:8], b"\0\0\0\0")
            self.assertEqual(metadata["compressed_sha256"], hashlib.sha256(compressed).hexdigest())
            raw_digest = hashlib.sha256()
            raw_size = 0
            with gzip.open(archive, "rb") as decoded:
                for block in iter(lambda: decoded.read(1024 * 1024), b""):
                    raw_digest.update(block)
                    raw_size += len(block)
            self.assertEqual(metadata["uncompressed_size_bytes"], raw_size)
            self.assertEqual(metadata["uncompressed_sha256"], raw_digest.hexdigest())

    def test_scientific_decision_and_information_gates(self) -> None:
        decision = load_json(PAPER / "fresh_holdout_decision.json")
        self.assertIn(decision["decision"], {"pass", "no_go", "blocked_insufficient_information", "blocked_fixed_budget"})
        self.assertEqual(decision["primary_workload_count"], 178)
        self.assertTrue(decision["primary_identity_uniqueness_gate_pass"])
        self.assertEqual(decision["rank_order_claim"], "diagnostic_only")
        self.assertFalse(decision["gpu_screen_status_if_applied"] != "experimental")

    def test_actual_resources_stay_inside_fixed_limits(self) -> None:
        resources = load_json(PAPER / "fresh_holdout_actual_resources.json")
        self.assertEqual(resources["fixed_total_artifact_storage_bytes"], 64 * 1024**3)
        self.assertTrue(resources["fixed_budget_gate_pass"])
        self.assertLessEqual(float(resources["actual_gpu_hours"]), 72)
        self.assertLessEqual(float(resources["actual_scheduled_elapsed_wall_seconds"]), 172800)
        self.assertGreater(resources["artifact_storage_margin_bytes"], 0)

    def test_binary_denominator_has_no_technical_failures(self) -> None:
        with (PAPER / "source_data/fresh_workload_metrics.tsv").open(newline="", encoding="utf-8") as handle:
            metrics = list(csv.DictReader(handle, delimiter="\t"))
        primary = [row for row in metrics if row["primary_instance"] == "1"]
        self.assertEqual(len(primary), 178 * 3)
        self.assertTrue(all(row["technical_failure"] == "0" for row in primary))
        self.assertTrue(all(row["input_identity_pass"] == "1" for row in primary))


if __name__ == "__main__":
    unittest.main()
