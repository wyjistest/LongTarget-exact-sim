#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_exact_long_query_hybrid_promoter_panel_v1.py"
SPEC = importlib.util.spec_from_file_location("prepare_promoter_panel", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreparePromoterPanelTests(unittest.TestCase):
    def test_interpolates_checkpoint_timing(self) -> None:
        points = [(4000, 40.0), (8000, 80.0), (12000, 100.0)]
        self.assertAlmostEqual(MODULE.interpolate(6000, points), 60.0)
        self.assertAlmostEqual(MODULE.interpolate(10000, points), 90.0)

    def test_short_fasta_adapter_changes_only_header_and_wrapping(self) -> None:
        sequence = "ACGT" * 31
        value = MODULE.short_fasta_bytes("ENSG00000000001", sequence).decode("ascii")
        lines = value.splitlines()
        self.assertEqual(lines[0], ">ENSG00000000001")
        self.assertEqual("".join(lines[1:]), sequence)
        self.assertTrue(all(len(line) <= 80 for line in lines[1:]))

    def test_dynamic_shared_memory_formula_matches_checkpoint(self) -> None:
        values = {
            4006: 24192,
            8181: 49152,
            12397: 74496,
        }
        for length, expected in values.items():
            self.assertEqual(3 * ((length + 31) // 32) * 32 * 2, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
