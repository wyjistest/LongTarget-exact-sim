#!/usr/bin/env python3
"""Focused regression checks for the frozen Phase 4 no-go evidence."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "reproduce/bioinformatics_submission_readiness_v2/freeze_phase4_evidence.py"
SPEC = importlib.util.spec_from_file_location("v2_phase4_freeze_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
FREEZE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FREEZE
SPEC.loader.exec_module(FREEZE)


class Phase4EvidenceTests(unittest.TestCase):
    def test_artifact_roles_are_closed(self) -> None:
        self.assertEqual(FREEZE.artifact_role(Path("phase4/run-start.json")), "formal_run_start")
        self.assertEqual(
            FREEZE.artifact_role(Path("phase4/formal/example/product/candidate_sites.tsv")),
            "formal_candidate_sites",
        )
        self.assertEqual(
            FREEZE.artifact_role(Path("phase4/comparisons/example/comparison.json")),
            "formal_comparison_result",
        )
        self.assertEqual(FREEZE.artifact_role(Path("phase4/unknown.txt")), "")

    def test_failure_is_repeatable_and_stability_scoped(self) -> None:
        for repeat_index in range(5):
            pair_id = f"v2p4_w010__repeat{repeat_index:02d}"
            path = FREEZE.PHASE4_ROOT / "comparisons" / pair_id / "comparison.json"
            comparison = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(comparison["comparison_status"], "scientific_mismatch")
            self.assertFalse(comparison["technical_failure"])
            self.assertTrue(comparison["modes"]["score"]["binary_success"])
            self.assertTrue(comparison["modes"]["nt"]["binary_success"])
            self.assertFalse(comparison["modes"]["stability"]["binary_success"])
            self.assertTrue(comparison["modes"]["stability"]["top1_retained"])

    def test_observed_repeat_digests_are_deterministic_diagnostic_only(self) -> None:
        diagnostic = FREEZE.repeat_digest_diagnostic()
        self.assertTrue(diagnostic["diagnostic_only"])
        self.assertTrue(diagnostic["all_observed_repeat_digests_deterministic"])
        self.assertEqual(len(diagnostic["workload_arm_groups"]), 20)


if __name__ == "__main__":
    unittest.main()
