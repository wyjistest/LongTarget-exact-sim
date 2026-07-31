from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase6"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SuccessorPhase6Tests(unittest.TestCase):
    def test_all_attempts_are_terminal_before_label_unsealing(self) -> None:
        summary = load_json(ARTIFACT_ROOT / "run-summary.json")
        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["planned_attempt_count"], 15)
        self.assertEqual(summary["terminal_attempt_count"], 15)
        self.assertEqual(summary["successful_attempt_count"], 10)
        self.assertEqual(summary["technical_failure_count"], 5)
        self.assertEqual(summary["missing_attempt_ids"], [])
        self.assertFalse(summary["comparison_started"])
        receipt = load_json(PAPER / "biological_utility_receipt.json")
        self.assertTrue(receipt["comparison_started_only_after_all_attempts_terminal"])
        self.assertTrue(receipt["labels_unsealed_only_by_offline_analyzer"])
        self.assertEqual(receipt["terminal_attempts"], 15)

    def test_primary_attempts_succeed_and_external_failures_are_retained(self) -> None:
        attempts = read_tsv(PAPER / "experimental_attempt_plan.tsv")
        primary_successes = 0
        external_failures = 0
        for attempt in attempts:
            root = ROOT / attempt["artifact_root"]
            receipt = load_json(root / "attempt-complete.json")
            self.assertEqual(receipt["attempt_id"], attempt["attempt_id"])
            self.assertFalse(receipt["labels_visible_to_backend"])
            self.assertFalse(receipt["label_manifest_mounted_in_sandbox"])
            self.assertFalse(receipt["comparison_started"])
            self.assertEqual(receipt["retry_policy"], "none")
            self.assertFalse(receipt["replacement_retry_allowed"])
            if attempt["arm"] in {"A", "G"}:
                primary_successes += 1
                self.assertEqual(receipt["status"], "success")
                output = root / receipt["output_path"]
                self.assertEqual(sha256_file(output), receipt["output_sha256"])
            else:
                external_failures += 1
                self.assertEqual(receipt["status"], "technical_failure")
                self.assertEqual(
                    receipt["failure_reason"],
                    "output_validation:RunnerError:Triplexator summary output missing",
                )
                self.assertIsNone(receipt["output_sha256"])
                self.assertIn("Failed to create temporary summary file", (root / "stderr.txt").read_text(encoding="utf-8"))
        self.assertEqual(primary_successes, 10)
        self.assertEqual(external_failures, 5)

    def test_g_telemetry_is_validated_deterministic_lossless_gzip(self) -> None:
        attempts = [row for row in read_tsv(PAPER / "experimental_attempt_plan.tsv") if row["arm"] == "G"]
        self.assertEqual(len(attempts), 5)
        for attempt in attempts:
            root = ROOT / attempt["artifact_root"]
            receipt = load_json(root / "attempt-complete.json")
            metadata = receipt["telemetry_storage"]
            archive = root / metadata["path"]
            self.assertFalse((root / "telemetry.json").exists())
            self.assertTrue(metadata["validated_before_compression"])
            self.assertTrue(metadata["lossless"])
            compressed = archive.read_bytes()
            self.assertEqual(compressed[:2], b"\x1f\x8b")
            self.assertEqual(compressed[4:8], b"\0\0\0\0")
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), metadata["compressed_sha256"])
            raw_digest = hashlib.sha256()
            raw_size = 0
            with gzip.open(archive, "rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    raw_digest.update(block)
                    raw_size += len(block)
            self.assertEqual(raw_size, metadata["uncompressed_size_bytes"])
            self.assertEqual(raw_digest.hexdigest(), metadata["uncompressed_sha256"])

    def test_region_scores_and_bootstrap_reproduce_the_no_go(self) -> None:
        score_rows = read_tsv(PAPER / "source_data/experimental_region_scores.tsv")
        self.assertEqual(len(score_rows), 10000)
        by_region: dict[tuple[str, str], dict[str, int]] = {}
        for row in score_rows:
            by_region.setdefault((row["dataset_id"], row["region_id"]), {})[row["arm"]] = int(row["region_score"])
        self.assertEqual(len(by_region), 5000)
        self.assertEqual(sum(values["A"] != values["G"] for values in by_region.values()), 7)

        bootstrap = read_tsv(PAPER / "source_data/experimental_bootstrap.tsv")
        self.assertEqual(len(bootstrap), 10000)
        e4 = np.asarray([float(row["E4"]) for row in bootstrap], dtype=np.float64)
        self.assertEqual(np.isneginf(e4).sum(), 5)
        self.assertEqual((e4 <= 0).sum(), 671)
        lcb = float(np.quantile(e4, 0.05, method="inverted_cdf"))
        self.assertEqual(format(lcb, ".17g"), "-0.024581674369296539")

        decision = load_json(PAPER / "biological_utility_decision.json")
        self.assertEqual(decision["decision"], "no_go")
        self.assertFalse(decision["biological_utility_pass"])
        self.assertEqual(decision["endpoint_pass"], {"E1": True, "E2": True, "E3": True, "E4": False})
        self.assertEqual(decision["one_sided_95_lcb"]["E4"], format(lcb, ".17g"))
        self.assertFalse(decision["later_phase_authorized"])

    def test_fixed_resource_gates_pass_without_becoming_performance_claims(self) -> None:
        resources = load_json(PAPER / "biological_utility_actual_resources.json")
        self.assertEqual(resources["fixed_total_artifact_storage_bytes"], 64 * 1024**3)
        self.assertEqual(resources["successful_primary_attempt_count"], 10)
        self.assertEqual(resources["primary_technical_failure_count"], 0)
        self.assertEqual(resources["external_technical_failure_count"], 5)
        self.assertTrue(resources["all_fixed_budget_gates_pass"])
        self.assertGreater(resources["artifact_storage_margin_bytes"], 0)
        self.assertLessEqual(float(resources["gpu_backend_hours"]), 96)
        self.assertLessEqual(float(resources["cpu_and_external_backend_wall_hours"]), 96)
        self.assertFalse(resources["resource_values_are_performance_claims"])

    def test_final_artifact_manifest_and_terminal_state_are_bound(self) -> None:
        manifest = read_tsv(PAPER / "biological_utility_artifact_manifest.tsv")
        self.assertEqual(len(manifest), 10)
        for row in manifest:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, int(row["size_bytes"]))
            self.assertEqual(sha256_file(path), row["sha256"])
        state = load_json(PAPER / "PROGRAM_STATE.json")
        self.assertIsNone(state["active_phase"])
        self.assertEqual(state["phase_status"]["6"], "no_go")
        self.assertTrue(all(state["phase_status"][str(phase)] == "not_authorized_previous_no_go" for phase in range(7, 10)))
        self.assertEqual(state["last_decision"], "biological_utility_no_go")
        self.assertEqual(state["gpu_screen_status"], "experimental")
        self.assertEqual(state["bioinformatics_route"], "closed_biological_utility_gap")


if __name__ == "__main__":
    unittest.main()
