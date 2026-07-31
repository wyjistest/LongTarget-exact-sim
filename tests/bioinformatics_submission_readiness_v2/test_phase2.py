from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
ARTIFACTS = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Phase2Tests(unittest.TestCase):
    def test_state_advances_only_to_phase3(self) -> None:
        state = load_json(PAPER / "PROGRAM_STATE.json")
        self.assertEqual(state["active_phase"], 3)
        self.assertEqual(state["last_completed_phase"], 2)
        self.assertEqual(state["software_epoch"], "submission_rc_v2_2")
        self.assertEqual(state["phase_status"]["2"], "pass")
        self.assertEqual(state["phase_status"]["3"], "active")
        self.assertEqual(state["product_status"], "experimental")
        self.assertEqual(state["validation_status"], "pending")
        self.assertFalse(state["external_comparison_authorized"])
        self.assertFalse(state["release_packaging_authorized"])
        self.assertFalse(state["submission_drafting_authorized"])

    def test_original_epoch_is_preserved_and_v22_is_pending(self) -> None:
        phase1 = load_json(PAPER / "phase_1_runtime_identity.json")
        supersession = load_json(PAPER / "phase_2_supersession_receipt.json")
        runtime = load_json(PAPER / "phase_2_runtime_identity.json")
        self.assertEqual(phase1["execution_identity"]["software_epoch"], "submission_rc_v2")
        self.assertEqual(supersession["old_epoch"]["software_epoch"], "submission_rc_v2")
        self.assertTrue(supersession["old_epoch"]["preserved_artifact"])
        self.assertEqual(runtime["execution_identity"]["software_epoch"], "submission_rc_v2_2")
        self.assertEqual(runtime["validation_status"], "pending_phase4")
        self.assertFalse(runtime["formal_performance_claim"])

    def test_v22_host_and_container_products_are_bound(self) -> None:
        runtime = load_json(PAPER / "phase_2_runtime_identity.json")
        smoke = runtime["smoke"]
        host = ARTIFACTS / "phase1/runtime-epoch-v2-2/real-gpu-smoke-host/product/candidate_sites.tsv"
        container = ARTIFACTS / "phase1/runtime-epoch-v2-2/real-gpu-smoke/product/candidate_sites.tsv"
        self.assertEqual(host.read_bytes(), container.read_bytes())
        self.assertEqual(sha256(host), smoke["candidate_sites_sha256"])
        self.assertEqual(smoke["target_extracted_interval"], [18902299, 18904800])
        self.assertEqual(smoke["fallbacks"], 0)
        self.assertEqual(smoke["gasal2_requests"], 1389)

    def test_all_development_pairs_are_retained_without_claim(self) -> None:
        receipt = load_json(PAPER / "phase_2_development_receipt.json")
        self.assertFalse(receipt["formal_claim"])
        self.assertIsNone(receipt["formal_performance_estimate"])
        pairs = {row["workload_id"]: row for row in receipt["development_pairs"]}
        self.assertEqual(set(pairs), {
            "phase2_dev_bts3_w022",
            "phase2_dev_bts3_w006",
            "phase2_dev_bts3_w153",
        })
        self.assertFalse(pairs["phase2_dev_bts3_w022"]["contract_pass"])
        self.assertFalse(pairs["phase2_dev_bts3_w006"]["contract_pass"])
        self.assertTrue(pairs["phase2_dev_bts3_w153"]["contract_pass"])
        for row in pairs.values():
            self.assertAlmostEqual(
                row["diagnostic_speedup"],
                row["authority_wall_seconds"] / row["candidate_wall_seconds"],
                places=12,
            )

    def test_external_landscape_keeps_runtime_roles_separate(self) -> None:
        protocol = load_json(PAPER / "phase_2_external_search_protocol.json")
        self.assertEqual(protocol["search_date"], "2026-07-31")
        self.assertFalse(protocol["formal_comparator_selection_frozen"])
        with (PAPER / "external_method_landscape.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {row["tool"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(rows["PATO"]["landscape_role"], "candidate_current_executable")
        self.assertEqual(rows["Triplexator"]["landscape_role"], "legacy_executable")
        self.assertEqual(rows["TripLexicon"]["direct_runtime_candidate"], "no")
        self.assertEqual(rows["3plex"]["direct_runtime_candidate"], "no")

    def test_external_smokes_are_development_only(self) -> None:
        receipt = load_json(PAPER / "phase_2_external_tool_receipt.json")
        self.assertFalse(receipt["formal_comparison_authorized"])
        for tool in ("pato", "triplexator"):
            record = receipt[tool]
            report_path = ARTIFACTS / record["development_report_relative_path"]
            self.assertEqual(sha256(report_path), record["development_report_sha256"])
            report = load_json(report_path)
            self.assertEqual(report["status"], "development_success")
            self.assertTrue(report["development_diagnostic_only"])
            self.assertTrue(report["excluded_from_all_v2_formal_panels"])
            self.assertTrue(report["output_basename_only"])


if __name__ == "__main__":
    unittest.main()
