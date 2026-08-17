from __future__ import annotations

import csv
import gzip
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
V1 = ROOT / "paper/biological_topk"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class SuccessorPhase1Tests(unittest.TestCase):
    def test_contract_and_thresholds_are_unchanged(self) -> None:
        binding = load_json(PAPER / "contract_binding.json")
        self.assertEqual(binding["status"], "exact_predecessor_contract_reused")
        self.assertFalse(binding["scientific_contract_changed"])
        self.assertFalse(binding["comparator_changed"])
        self.assertFalse(binding["threshold_changed"])
        self.assertEqual(binding["N_panel"], 178)
        self.assertEqual(binding["n_binary_required"], 124)
        self.assertEqual(binding["k_min"], 122)
        self.assertEqual(binding["allowed_failures"], 2)

    def test_every_predecessor_workload_is_newly_excluded(self) -> None:
        with (PAPER / "successor_exclusion_registry.tsv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        added = [row for row in rows if row["exclusion_reason"] == "predecessor_phase4_fresh_concordance_input"]
        self.assertEqual(len(added), 178)
        with (V1 / "fresh_holdout_manifest.tsv").open(newline="", encoding="utf-8") as handle:
            manifest = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual({row["pair_digest"] for row in added}, {row["input_pair_digest"] for row in manifest})

    def test_eligible_universes_have_zero_predecessor_identity_overlap(self) -> None:
        with (V1 / "fresh_holdout_manifest.tsv").open(newline="", encoding="utf-8") as handle:
            manifest = list(csv.DictReader(handle, delimiter="\t"))
        old_queries = {row["query_sequence_sha256"] for row in manifest}
        old_targets = {row["target_sequence_sha256"] for row in manifest}
        with gzip.open(PAPER / "query_source_universe.tsv.gz", "rt", newline="", encoding="utf-8") as handle:
            queries = [row for row in csv.DictReader(handle, delimiter="\t") if row["historical_exclusion_status"] == "fresh_eligible"]
        with gzip.open(PAPER / "target_source_universe.tsv.gz", "rt", newline="", encoding="utf-8") as handle:
            targets = [row for row in csv.DictReader(handle, delimiter="\t") if row["historical_exclusion_status"] == "fresh_eligible"]
        self.assertFalse(old_queries & {row["sequence_sha256"] for row in queries})
        self.assertFalse(old_targets & {row["sequence_sha256"] for row in targets})

    def test_source_capacity_and_information_gates_pass(self) -> None:
        information = load_json(PAPER / "information_feasibility.json")
        self.assertEqual(information["status"], "pass")
        self.assertTrue(information["all_information_gates_pass"])
        self.assertTrue(information["source_capacity"]["query_gate_pass"])
        self.assertTrue(all(information["source_capacity"]["target_gate_pass_by_stratum"].values()))
        self.assertEqual(information["predecessor_overlap_count"], 0)

    def test_resource_model_uses_receipts_and_bytes_only(self) -> None:
        model = load_json(PAPER / "resource_projection_model.json")
        self.assertEqual(model["observation_source"], "terminal_attempt_receipts_and_directory_file_bytes_only")
        self.assertFalse(model["scientific_output_fields_read"])
        self.assertFalse(model["resource_values_are_performance_claims"])
        self.assertEqual(len(model["observations"]), 165)
        self.assertEqual({row["arm"] for row in model["observations"]}, {"A", "G"})

    def test_resource_stress_gate_includes_predecessor_and_raw_reservation(self) -> None:
        resource = load_json(PAPER / "resource_projection.json")
        storage = resource["projection"]["artifact_storage_bytes"]
        self.assertEqual(storage["predecessor_retained"], 7_142_325_727)
        self.assertEqual(storage["raw_g_reservation"], 1_610_612_736)
        self.assertEqual(storage["quota"], 64 * 1024**3)
        self.assertEqual(storage["gate_basis"], storage["total_max_observed_stress_with_reservation"])
        self.assertGreater(storage["margin"], 0)
        self.assertTrue(storage["gate_pass"])

    def test_runtime_resource_gates_pass(self) -> None:
        projection = load_json(PAPER / "resource_projection.json")["projection"]
        self.assertTrue(projection["gpu_hours"]["gate_pass"])
        self.assertLessEqual(float(projection["gpu_hours"]["upper_95"]), 72)
        self.assertTrue(projection["scheduled_elapsed_wall_seconds"]["gate_pass"])
        self.assertLessEqual(float(projection["scheduled_elapsed_wall_seconds"]["upper_95"]), 172800)

    def test_phase1_selected_no_pair_and_started_no_prediction(self) -> None:
        for name in ("source_universe_receipt.json", "information_feasibility.json", "resource_decision.json"):
            payload = load_json(PAPER / name)
            self.assertFalse(payload["fresh_pair_selected"])
            self.assertFalse(payload["new_prediction_run"])

    def test_gzip_headers_are_deterministic(self) -> None:
        for name in ("query_source_universe.tsv.gz", "target_source_universe.tsv.gz"):
            header = (PAPER / name).read_bytes()[:10]
            self.assertEqual(header[:2], b"\x1f\x8b")
            self.assertEqual(header[4:8], b"\x00\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
