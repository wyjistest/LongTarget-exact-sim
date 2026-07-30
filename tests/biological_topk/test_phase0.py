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


CHECKER = load_module("biological_topk_checker", ROOT / "scripts/check_biological_topk_phase.py")
HISTORY = load_module(
    "biological_topk_history",
    ROOT / "reproduce/biological_topk/build_historical_blob_registry.py",
)
EXCLUSIONS = load_module(
    "biological_topk_exclusions",
    ROOT / "reproduce/biological_topk/build_exclusion_registry.py",
)


class Phase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(
            (ROOT / "schemas/biological_topk_program_state.schema.json").read_text(encoding="utf-8")
        )
        self.state = json.loads(
            (ROOT / "paper/biological_topk/PROGRAM_STATE.json").read_text(encoding="utf-8")
        )

    def test_program_state_validates(self) -> None:
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

    def test_illegal_phase8_product_promotion_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["gpu_screen_status"] = "validated_screening_backend_v1_release_candidate"
        with self.assertRaises(CHECKER.CheckError):
            CHECKER.validate_state_transitions(state)

    def test_historical_registry_uses_frozen_blobs(self) -> None:
        rows = HISTORY.build_rows()
        self.assertEqual(len(rows), 27)
        self.assertTrue(all(row["frozen_at_commit"] == CHECKER.EXECUTION_START_HEAD for row in rows))
        self.assertTrue(all(row["frozen_blob_mutable"] == 0 for row in rows))

    def test_exclusion_registry_covers_development_and_corpus(self) -> None:
        rows = EXCLUSIONS.build_rows()
        self.assertEqual(len(rows), 1455)
        reasons = {reason for row in rows for reason in row["exclusion_reason"].split(";")}
        self.assertIn("historical_development_lncRNA", reasons)
        self.assertIn("ssw_cuda_differential_corpus_adversarial", reasons)
        self.assertEqual(
            sum(
                row["exclusion_reason"] == "phase3_v1_preregistered_application_universe"
                for row in rows
            ),
            718,
        )
        self.assertEqual(
            sum(row["query_ordinal_namespace"] == "ssw_cuda_corpus_case_v1" for row in rows),
            625,
        )

    def test_precommit_receipt_cannot_claim_self_commit(self) -> None:
        receipt = json.loads(
            (ROOT / "paper/biological_topk/phase_0_precommit_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("commit_sha", receipt)
        self.assertNotIn("phase_commit", receipt)


if __name__ == "__main__":
    unittest.main()
