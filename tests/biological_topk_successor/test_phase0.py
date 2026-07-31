from __future__ import annotations

import copy
import csv
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CHECKER = load_module(
    "biological_topk_successor_checker",
    ROOT / "scripts/check_biological_topk_successor_phase.py",
)


class SuccessorPhase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(
            (ROOT / "schemas/biological_topk_successor_program_state.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.state = json.loads(
            (ROOT / "paper/biological_topk_successor/PROGRAM_STATE.json").read_text(
                encoding="utf-8"
            )
        )

    def test_successor_state_validates(self) -> None:
        CHECKER.validate_schema(self.state, self.schema)
        CHECKER.validate_state_transitions(self.state)

    def test_unknown_state_field_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["mostly_ready"] = True
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(state, self.schema)

    def test_unknown_phase_status_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["phase_status"]["1"] = "mostly_pass"
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(state, self.schema)

    def test_premature_product_promotion_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["gpu_screen_status"] = "validated_screening_backend_v1_release_candidate"
        with self.assertRaises(CHECKER.CheckError):
            CHECKER.validate_state_transitions(state)

    def test_owner_authorized_exact_64_gib_total_quota(self) -> None:
        authorization = json.loads(
            (ROOT / "paper/biological_topk_successor/owner_successor_authorization.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(authorization["approval_message"], "\u6279\u51c6")
        self.assertEqual(authorization["max_total_artifact_storage_bytes"], 64 * 1024**3)
        self.assertTrue(authorization["includes_predecessor_artifact_bytes"])
        self.assertFalse(authorization["predecessor_evidence_may_be_modified"])
        self.assertFalse(authorization["quota_may_be_raised_after_successor_phase3_projection"])

    def test_quota_exceeds_conservative_observed_size_envelope(self) -> None:
        conservative_observed_envelope = 52_167_802_495
        self.assertGreater(self.state["fixed_total_artifact_storage_bytes"], conservative_observed_envelope)

    def test_predecessor_remains_terminal_and_unmodified(self) -> None:
        predecessor = json.loads(
            (ROOT / "paper/biological_topk/PROGRAM_STATE.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(predecessor["active_phase"])
        self.assertEqual(predecessor["phase_status"]["4"], "blocked_fixed_budget")
        self.assertTrue(
            all(
                predecessor["phase_status"][str(phase)] == "not_authorized_previous_no_go"
                for phase in range(5, 10)
            )
        )

    def test_predecessor_registry_is_substantial_and_unique(self) -> None:
        with (ROOT / "paper/biological_topk_successor/v1_evidence_registry.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertGreaterEqual(len(rows), 50)
        self.assertEqual(len(rows), len({row["path"] for row in rows}))
        self.assertTrue(
            all(row["frozen_at_commit"] == CHECKER.PREDECESSOR_COMMIT for row in rows)
        )

    def test_phase0_receipt_records_no_runtime_root_at_its_boundary(self) -> None:
        epoch = json.loads(
            (ROOT / "paper/biological_topk_successor/epoch_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(epoch["new_scientific_run_started"])
        self.assertFalse(epoch["successor_artifact_root_exists"])

    def test_precommit_receipt_cannot_claim_self_commit(self) -> None:
        receipt = json.loads(
            (ROOT / "paper/biological_topk_successor/phase_0_precommit_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("commit_sha", receipt)
        self.assertNotIn("phase_commit", receipt)


if __name__ == "__main__":
    unittest.main()
