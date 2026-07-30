from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
V1_PAPER = ROOT / "paper/biological_topk"
REGRESSION_NAMES = (
    "phase2_known_cases.json",
    "phase2_regression_details.tsv",
    "phase2_regression_manifest.tsv",
    "phase2_regression_receipt.json",
    "phase2_regression_results.tsv",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SuccessorPhase2Tests(unittest.TestCase):
    def test_regression_outputs_are_byte_identical_to_predecessor(self) -> None:
        for name in REGRESSION_NAMES:
            self.assertEqual((PAPER / name).read_bytes(), (V1_PAPER / name).read_bytes(), name)

    def test_freeze_binds_unchanged_comparator(self) -> None:
        freeze = json.loads((PAPER / "phase2_comparator_freeze.json").read_text(encoding="utf-8"))
        binding = json.loads((PAPER / "contract_binding.json").read_text(encoding="utf-8"))
        self.assertEqual(freeze["status"], "pass")
        self.assertFalse(freeze["scientific_contract_changed"])
        self.assertFalse(freeze["comparator_changed"])
        self.assertTrue(freeze["historical_regression_rerun"])
        self.assertTrue(freeze["prior_mismatch_and_no_go_preserved"])
        self.assertEqual(
            freeze["comparator_sha256"],
            binding["bindings"]["reproduce/biological_topk/compare_candidate_topk.py"],
        )

    def test_every_regression_digest_is_bound(self) -> None:
        freeze = json.loads((PAPER / "phase2_comparator_freeze.json").read_text(encoding="utf-8"))
        for name in REGRESSION_NAMES:
            self.assertEqual(
                freeze["successor_regression_sha256"][f"paper/biological_topk_successor/{name}"],
                sha256_file(PAPER / name),
            )
            self.assertEqual(
                freeze["predecessor_regression_sha256"][f"paper/biological_topk/{name}"],
                sha256_file(V1_PAPER / name),
            )

    def test_known_mismatches_and_failure_counts_are_preserved(self) -> None:
        receipt = json.loads((PAPER / "phase2_regression_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["comparison_count"], 184)
        self.assertEqual(receipt["ranking_result_count"], 552)
        self.assertEqual(receipt["strict_row_mismatch_result_count"], 14)
        self.assertEqual(receipt["technical_failure_count"], 0)
        self.assertEqual(receipt["input_identity_mismatch_count"], 0)
        self.assertFalse(receipt["fresh_pair_selected"])
        self.assertFalse(receipt["new_prediction_run"])


if __name__ == "__main__":
    unittest.main()
