#!/usr/bin/env python3
"""Tests for the input-only canonical-hybrid-v2 performance selector."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZER_PATH = ROOT / "scripts/freeze_bioinformatics_canonical_hybrid_v2_performance.py"


def load_freezer():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_performance_freeze_test", FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {FREEZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PerformanceFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freezer = load_freezer()

    def query_rows(self):
        lengths = [600] * 7 + [1000] * 7 + [2000] * 7
        return [
            {
                "source_ordinal": index,
                "sequence_length": str(length),
                "record_id": f"query-{index}",
                "sequence_sha256": f"digest-{index}",
            }
            for index, length in enumerate(lengths, 1)
        ]

    def target_rows(self):
        chromosomes = ["chr21"] * 7 + ["chr22"] * 7
        return [
            {
                "source_ordinal": index,
                "chromosome": chromosome,
                "record_id": f"target-{index}",
                "sequence_sha256": f"digest-{index}",
            }
            for index, chromosome in enumerate(chromosomes, 1)
        ]

    def selected_ordinals(self, queries, targets):
        selected_queries, selected_targets = self.freezer.select_inputs(
            queries, targets, {2, 8, 15}, {2, 9}
        )
        return (
            [int(row["source_ordinal"]) for row in selected_queries],
            [int(row["source_ordinal"]) for row in selected_targets],
        )

    def test_names_and_digests_cannot_change_selection(self) -> None:
        queries = self.query_rows()
        targets = self.target_rows()
        expected = self.selected_ordinals(queries, targets)
        for row in queries + targets:
            row["record_id"] = "renamed"
            row["sequence_sha256"] = "changed"
        self.assertEqual(self.selected_ordinals(queries, targets), expected)

    def test_correctness_partition_and_v1_prefix_are_ineligible(self) -> None:
        query_ordinals, target_ordinals = self.selected_ordinals(self.query_rows(), self.target_rows())
        self.assertFalse(set(query_ordinals) & {1, 2, 8, 15})
        self.assertFalse(set(target_ordinals) & {1, 2, 9})

    def test_selection_has_one_input_per_coverage_group(self) -> None:
        queries, targets = self.freezer.select_inputs(
            self.query_rows(), self.target_rows(), {2, 8, 15}, {2, 9}
        )
        self.assertEqual([row["query_stratum"] for row in queries], list(self.freezer.QUERY_STRATA))
        self.assertEqual([row["chromosome"] for row in targets], list(self.freezer.TARGET_CHROMOSOMES))


if __name__ == "__main__":
    unittest.main()
