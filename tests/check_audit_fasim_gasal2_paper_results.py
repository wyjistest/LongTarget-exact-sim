#!/usr/bin/env python3
"""Unit tests for the independent paper arithmetic audit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reproduce/audit_paper_results.py"
SPEC = importlib.util.spec_from_file_location("audit_paper_results", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load independent audit module")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

LANGUAGE_PATH = ROOT / "reproduce/audit_claim_language.py"
LANGUAGE_SPEC = importlib.util.spec_from_file_location("audit_claim_language", LANGUAGE_PATH)
if LANGUAGE_SPEC is None or LANGUAGE_SPEC.loader is None:
    raise RuntimeError("cannot load claim-language audit module")
LANGUAGE = importlib.util.module_from_spec(LANGUAGE_SPEC)
LANGUAGE_SPEC.loader.exec_module(LANGUAGE)


class IndependentPaperArithmeticTests(unittest.TestCase):
    def test_median_is_independent_for_odd_and_even_samples(self) -> None:
        self.assertEqual(MODULE.median([9.0, 1.0, 5.0]), 5.0)
        self.assertEqual(MODULE.median([8.0, 2.0, 6.0, 4.0]), 5.0)

    def test_pair_validation_rejects_reported_speedup_drift(self) -> None:
        rows = [{
            "pair_id_text": "pair-1",
            "baseline_wall_seconds": "12",
            "candidate_wall_seconds": "3",
            "paired_speedup": "3.5",
        }]
        with self.assertRaisesRegex(ValueError, "pair-1"):
            MODULE.recomputed_pair_speedups(rows)

    def test_ratio_rows_recompute_storage_and_exact_stage(self) -> None:
        storage = MODULE.storage_ratio({"legacy_text_bytes": "120", "archive_bytes": "20"})
        stage = MODULE.stage_speedup({
            "baseline_exact_stage_seconds": "9", "candidate_exact_stage_seconds": "6",
        })
        self.assertEqual(storage, 6.0)
        self.assertEqual(stage, 1.5)


class ClaimLanguageAuditTests(unittest.TestCase):
    def test_rejects_positive_universal_claim(self) -> None:
        violations = LANGUAGE.find_violations({"bad.md": "Our method universally accelerates LongTarget.\n"})
        self.assertEqual(len(violations), 1)
        self.assertIn("bad.md:1", violations[0])

    def test_allows_explicit_boundary_or_forbidden_wording_context(self) -> None:
        documents = {
            "limits.md": "We do not claim a full replacement.\n",
            "sheet.md": "- forbidden extrapolation: all short queries are clean.\n",
        }
        self.assertEqual(LANGUAGE.find_violations(documents), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
