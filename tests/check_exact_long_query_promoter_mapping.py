#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/exact_long_query_promoter_mapping.py"
SPEC = importlib.util.spec_from_file_location("promoter_mapping", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PromoterMappingCoordinateTests(unittest.TestCase):
    def test_normalizes_all_strand_coordinate_forms(self) -> None:
        for strand in ("ParaPlus", "AntiMinus"):
            row = {"StartInSeq": "11", "EndInSeq": "20", "Strand": strand}
            self.assertEqual(MODULE.normalized_target_interval(row, 100), (10, 20))
        for strand in ("ParaMinus", "AntiPlus"):
            row = {"StartInSeq": "10", "EndInSeq": "19", "Strand": strand}
            self.assertEqual(MODULE.normalized_target_interval(row, 100), (10, 20))

    def test_target_transform_matches_longtarget_strands(self) -> None:
        self.assertEqual(MODULE.target_transform("ACGT", "ParaPlus"), "ACGT")
        self.assertEqual(MODULE.target_transform("ACGT", "ParaMinus"), "ACGT")
        self.assertEqual(MODULE.target_transform("ACGT", "AntiMinus"), "TGCA")
        self.assertEqual(MODULE.target_transform("ACGT", "AntiPlus"), "TGCA")

    def test_rejects_interval_outside_target(self) -> None:
        row = {"StartInSeq": "0", "EndInSeq": "10", "Strand": "ParaPlus"}
        with self.assertRaises(MODULE.MappingError):
            MODULE.normalized_target_interval(row, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
