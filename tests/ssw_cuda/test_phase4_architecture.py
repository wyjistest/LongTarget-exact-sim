#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class Phase4ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(
            (ROOT / "paper/ssw_cuda/upstream_build_receipt.json").read_text(encoding="utf-8")
        )
        with (ROOT / "paper/ssw_cuda/upstream_snapshot.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            cls.snapshots = list(csv.DictReader(handle, delimiter="\t"))
        with (ROOT / "paper/ssw_cuda/upstream_semantic_diff.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            cls.semantic_rows = list(csv.DictReader(handle, delimiter="\t"))

    def test_upstreams_are_exactly_pinned_and_licensed(self) -> None:
        by_id = {row["upstream_id"]: row for row in self.snapshots}
        self.assertEqual(set(by_id), {"accelign", "g3sa"})
        self.assertEqual(by_id["accelign"]["commit"], "c7ecd32d59e256716cca193556110051c171570f")
        self.assertEqual(by_id["accelign"]["license_spdx"], "Apache-2.0")
        self.assertEqual(by_id["g3sa"]["commit"], "f0e0c130631dc2e06f92822b66c0494683f77eef")
        self.assertEqual(by_id["g3sa"]["license_spdx"], "GPL-3.0")
        self.assertEqual(by_id["g3sa"]["reuse_policy"], "paper_and_structure_reference_only_no_code_copy_or_link")

    def test_build_and_runtime_limitations_are_not_hidden(self) -> None:
        attempts = {row["attempt_id"]: row for row in self.receipt["build_attempts"]}
        self.assertEqual(self.receipt["build_budget"]["attempt_counts"], {"accelign": 1, "g3sa": 3})
        self.assertEqual(attempts["accelign_build01"]["returncode"], 0)
        self.assertEqual(attempts["g3sa_build01"]["returncode"], 2)
        self.assertEqual(attempts["g3sa_build02"]["returncode"], 2)
        self.assertEqual(attempts["g3sa_build03"]["returncode"], 0)
        runtimes = {row["attempt_id"]: row for row in self.receipt["runtime_attempts"]}
        self.assertEqual(runtimes["g3sa_run02"]["returncode"], 139)
        self.assertFalse(self.receipt["results"]["g3sa_runtime_correctness_claimed"])
        self.assertFalse(self.receipt["results"]["accelign_ssw_equivalence_claimed"])

    def test_semantic_matrix_covers_every_contract_layer(self) -> None:
        coverage = {
            upstream: {row["layer"] for row in self.semantic_rows if row["upstream_id"] == upstream}
            for upstream in ("accelign", "g3sa")
        }
        for upstream in coverage:
            self.assertTrue({"L0", "L1", "L2", "L3", "L4", "L5"} <= coverage[upstream])
        g3sa_l5 = next(
            row for row in self.semantic_rows if row["upstream_id"] == "g3sa" and row["layer"] == "L5"
        )
        self.assertIn("implement every recurrence and tie in-tree", g3sa_l5["reuse_decision"])

    def test_selected_architecture_keeps_all_semantics_in_tree(self) -> None:
        self.assertEqual(
            self.receipt["results"]["selected_architecture"],
            "C_mixed_in_tree_checkpoint_recompute",
        )
        self.assertFalse(self.receipt["results"]["third_party_code_linked_or_copied"])
        self.assertEqual(self.receipt["claim_boundary"]["l1_l5_implementation_owner"], "in_tree")
        self.assertFalse(self.receipt["claim_boundary"]["cpu_oracle_replaced"])
        decision = (ROOT / "paper/ssw_cuda/architecture_decision.md").read_text(encoding="utf-8")
        for layer in ("L1", "L2", "L3", "L4", "L5"):
            self.assertIn(f"| {layer} ", decision)
        self.assertIn("`bioinformatics_b3_track` remains `closed_amdahl`", decision)


if __name__ == "__main__":
    unittest.main()
