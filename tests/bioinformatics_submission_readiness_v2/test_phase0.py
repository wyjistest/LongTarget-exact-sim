from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_checker():
    path = ROOT / "scripts/check_bioinformatics_submission_readiness_v2.py"
    spec = importlib.util.spec_from_file_location("submission_readiness_v2_checker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["submission_readiness_v2_checker"] = module
    spec.loader.exec_module(module)
    return module


CHECKER = load_checker()


class Phase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = json.loads(CHECKER.STATE.read_text(encoding="utf-8"))
        self.schema = json.loads(CHECKER.SCHEMA.read_text(encoding="utf-8"))

    def test_state_validates(self) -> None:
        CHECKER.validate_schema(self.state, self.schema)
        CHECKER.validate_state_transitions(self.state)

    def test_unknown_field_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["mostly_ready"] = True
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(state, self.schema)

    def test_legacy_route_cannot_be_reopened(self) -> None:
        state = copy.deepcopy(self.state)
        state["current_legacy_bioinformatics_route"] = "conditionally_open"
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(state, self.schema)

    def test_product_cannot_be_promoted_before_phase4(self) -> None:
        state = copy.deepcopy(self.state)
        state["product_status"] = "validated_release_candidate"
        state["validation_status"] = "passed"
        with self.assertRaises(CHECKER.CheckError):
            CHECKER.validate_state_transitions(state)

    def test_acceleration_claim_cannot_be_promoted_before_phase4(self) -> None:
        state = copy.deepcopy(self.state)
        state["target_claim_status"] = "supported"
        with self.assertRaises(CHECKER.CheckError):
            CHECKER.validate_state_transitions(state)

    def test_downstream_authorizations_are_false(self) -> None:
        self.assertFalse(self.state["external_comparison_authorized"])
        self.assertFalse(self.state["release_packaging_authorized"])
        self.assertFalse(self.state["submission_drafting_authorized"])

    def test_phase0_has_no_runtime_artifact_root(self) -> None:
        self.assertFalse(CHECKER.ARTIFACT_ROOT.exists())

    def test_authorization_is_independent_and_nonretroactive(self) -> None:
        authorization = json.loads(
            (CHECKER.PAPER / "owner_phase0_authorization.json").read_text(encoding="utf-8")
        )
        self.assertEqual(authorization["approval_message"], "启动并完成v2")
        self.assertFalse(authorization["historical_evidence_may_be_modified"])
        self.assertFalse(authorization["historical_no_go_may_be_reopened"])
        self.assertTrue(authorization["phase_4_stop_loss_required"])


if __name__ == "__main__":
    unittest.main()
