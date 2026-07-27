#!/usr/bin/env python3
"""Tests for the input-only canonical-hybrid-v2 holdout selector."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZER_PATH = ROOT / "scripts/freeze_bioinformatics_canonical_hybrid_v2_holdout.py"


def load_freezer():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_holdout_freeze_test", FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {FREEZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HoldoutFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freezer = load_freezer()

    def query_rows(self):
        lengths = [600] * 6 + [1000] * 6 + [2000] * 6
        return [
            {
                "source_ordinal": index,
                "sequence_length": str(length),
                "record_id": f"mutable-query-name-{index}",
                "sequence_sha256": f"mutable-query-digest-{index}",
            }
            for index, length in enumerate(lengths, 1)
        ]

    def target_rows(self):
        chromosomes = ["chr21"] * 6 + ["chr22"] * 6
        return [
            {
                "source_ordinal": index,
                "chromosome": chromosome,
                "record_id": f"mutable-target-name-{index}",
                "sequence_sha256": f"mutable-target-digest-{index}",
            }
            for index, chromosome in enumerate(chromosomes, 1)
        ]

    def selected_ordinals(self, queries, targets):
        selected_queries, selected_targets = self.freezer.select_inputs(queries, targets)
        return (
            [int(row["source_ordinal"]) for row in selected_queries],
            [int(row["source_ordinal"]) for row in selected_targets],
        )

    def test_names_and_digests_cannot_change_selection(self) -> None:
        queries = self.query_rows()
        targets = self.target_rows()
        expected = self.selected_ordinals(queries, targets)
        for row in queries:
            row["record_id"] = f"renamed-{row['source_ordinal']}"
            row["sequence_sha256"] = "changed"
        for row in targets:
            row["record_id"] = f"renamed-{row['source_ordinal']}"
            row["sequence_sha256"] = "changed"
        self.assertEqual(self.selected_ordinals(queries, targets), expected)

    def test_prior_v1_pilot_ordinals_are_ineligible(self) -> None:
        query_ordinals, target_ordinals = self.selected_ordinals(self.query_rows(), self.target_rows())
        self.assertNotIn(1, query_ordinals)
        self.assertNotIn(1, target_ordinals)

    def test_selection_covers_every_fixed_group(self) -> None:
        queries, targets = self.freezer.select_inputs(self.query_rows(), self.target_rows())
        self.assertEqual(
            {stratum: sum(row["query_stratum"] == stratum for row in queries) for stratum in self.freezer.QUERY_STRATA},
            {stratum: 4 for stratum in self.freezer.QUERY_STRATA},
        )
        self.assertEqual(
            {chromosome: sum(row["chromosome"] == chromosome for row in targets) for chromosome in self.freezer.TARGET_CHROMOSOMES},
            {chromosome: 2 for chromosome in self.freezer.TARGET_CHROMOSOMES},
        )


if __name__ == "__main__":
    unittest.main()
