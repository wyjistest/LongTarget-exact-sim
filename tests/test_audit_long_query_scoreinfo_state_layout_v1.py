#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_long_query_scoreinfo_state_layout_v1.py"
SPEC = importlib.util.spec_from_file_location("state_layout_audit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class LongQueryScoreInfoStateLayoutAuditTests(unittest.TestCase):
    def test_frozen_bounded_panel_is_exact(self):
        audit = MODULE.build_audit("test-source")
        self.assertEqual(audit["summary"]["cases"], 6)
        self.assertEqual(audit["summary"]["columns"], 1076)
        self.assertTrue(audit["summary"]["saturating_add_255_observed"])
        saturating = next(
            case for case in audit["cases"]
            if case["case_id"] == "all_match_byte_ceiling"
        )
        self.assertEqual(saturating["max_observed_state"], 251)
        self.assertTrue(saturating["saturating_add_255_observed"])
        self.assertEqual(
            audit["summary"]["three_state_uint8_differential_mismatches"], 0
        )
        self.assertEqual(
            audit["summary"]["two_state_inplace_differential_mismatches"], 0
        )
        self.assertFalse(audit["decisions"]["production_authorized"])

    def test_uint8_three_state_matches_int16_on_boundary_columns(self):
        columns = MODULE.random_columns(5, 73, 0xA4093822)
        self.assertEqual(
            MODULE.run_double_buffer(columns, 2),
            MODULE.run_double_buffer(columns, 1),
        )

    def test_in_place_h_matches_double_buffer_on_boundary_columns(self):
        columns = MODULE.random_columns(7, 81, 0x299F31D0)
        self.assertEqual(
            MODULE.run_double_buffer(columns, 2), MODULE.run_in_place(columns)
        )

    def test_signed_byte_lazy_f_boundary(self):
        self.assertEqual(MODULE.signed_i8(0), 0)
        self.assertEqual(MODULE.signed_i8(127), 127)
        self.assertEqual(MODULE.signed_i8(128), -128)
        self.assertEqual(MODULE.signed_i8(255), -1)

    def test_byte_storage_range_invariant_closes(self):
        bounds = MODULE.derive_range_invariant()
        self.assertEqual(bounds["transient_add_min"], -4)
        self.assertEqual(bounds["transient_add_max"], 255)
        self.assertEqual(bounds["diagonal_after_bias_max"], 251)
        self.assertEqual(bounds["inductive_h_storage_max"], 251)
        self.assertEqual(bounds["inductive_e_f_storage_max"], 235)
        self.assertTrue(bounds["uint8_storage_safe"])

    def test_invalid_profile_score_fails_closed(self):
        columns = MODULE.constant_columns(1, 1, 5)
        columns[0][0][0] = 4
        with self.assertRaises(ValueError):
            MODULE.run_in_place(columns)


if __name__ == "__main__":
    unittest.main()
