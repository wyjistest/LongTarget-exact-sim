#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FREEZER_PATH = ROOT / "reproduce/ssw_cuda/freeze_phase0.py"


def load_freezer():
    spec = importlib.util.spec_from_file_location("ssw_cuda_phase0_freezer", FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase 0 freezer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FREEZER = load_freezer()


class Phase0FreezeTests(unittest.TestCase):
    def test_historical_numbers_are_rebuilt_from_receipts(self) -> None:
        summary = FREEZER.historical_summary()
        self.assertEqual(summary["phase2"]["decision"], "verified_only_contract")
        self.assertEqual(summary["phase2"]["formal_attempts"], 36)
        self.assertEqual(summary["canonical_hybrid_v2"]["regression_top5_equal"], 36)
        self.assertEqual(summary["canonical_hybrid_v2"]["regression_full_output_equal"], 35)
        self.assertEqual(summary["canonical_hybrid_v2"]["fresh_holdout_equal"], 60)
        self.assertEqual(summary["canonical_hybrid_v2"]["performance_correct"], 18)
        self.assertEqual(summary["canonical_hybrid_v2"]["b3_status"], "no_go")
        self.assertEqual(summary["canonical_hybrid_v2"]["track"], "closed")

    def test_registry_has_all_required_exclusion_classes(self) -> None:
        rows = FREEZER.build_registry()
        reasons = {
            reason
            for row in rows
            for reason in str(row["exclusion_reason"]).split(";")
        }
        self.assertTrue(
            {
                "historical_development_or_paper_workload",
                "historical_development_query",
                "phase2_fixed_pilot",
                "phase2_correctness_holdout",
                "phase2_traceback_replay",
                "phase3_v1_fixed_pilot",
                "canonical_hybrid_v2_regression",
                "canonical_hybrid_v2_fresh_holdout",
                "canonical_hybrid_v2_performance_pilot",
            }.issubset(reasons)
        )
        pair_rows = [row for row in rows if row["record_type"] == "pair"]
        self.assertEqual(len(pair_rows), len({row["pair_digest"] for row in pair_rows}))
        self.assertTrue(all(len(str(row["pair_digest"])) == 64 for row in pair_rows))

    def test_application_ordinals_and_sequence_digests_are_bound(self) -> None:
        with (ROOT / "paper/bioinformatics/application_manifest.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            manifest = {row["record_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        rows = FREEZER.build_registry()
        pilot = next(row for row in rows if "phase3_v1_fixed_pilot" in row["exclusion_reason"])
        self.assertEqual(pilot["query_source_ordinal"], "1")
        self.assertEqual(pilot["target_source_ordinal"], "1")
        self.assertEqual(pilot["query_sha256"], manifest["aq001"]["sequence_sha256"])
        self.assertEqual(pilot["target_sha256"], manifest["at0001"]["sequence_sha256"])

    def test_committed_registry_checksum_matches(self) -> None:
        path = ROOT / "paper/ssw_cuda/used_input_exclusion_registry.tsv"
        expected = (ROOT / "paper/ssw_cuda/used_input_exclusion_registry.sha256").read_text(
            encoding="ascii"
        ).split()[0]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_program_boundaries_are_machine_readable(self) -> None:
        state = json.loads((ROOT / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(state["ssw_cpu_oracle_epoch"], 2)
        self.assertEqual(state["ssw_cuda_program_epoch"], 1)
        self.assertEqual(state["l8_contract_status"], "diagnostic_only")
        self.assertEqual(state["bioinformatics_b3_track"], "pending_amdahl")


if __name__ == "__main__":
    unittest.main()
