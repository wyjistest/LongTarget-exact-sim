#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCALAR = load_module("ssw_scalar_reference", ROOT / "reproduce/ssw_cuda/scalar_ssw_reference.py")
RUNNER = load_module("ssw_phase2_runner", ROOT / "reproduce/ssw_cuda/run_phase2_oracle.py")


class ScalarReferenceTests(unittest.TestCase):
    def test_tiny_exact_match_frontier(self) -> None:
        self.assertEqual(SCALAR.column_maxima("AC", "AC"), [5, 10])

    def test_local_restart(self) -> None:
        self.assertEqual(SCALAR.column_maxima("A", "CA"), [0, 5])

    def test_scoreinfo_threshold_group_and_tie(self) -> None:
        columns = [10, 11, 12, 12, 0, 0, 0, 0, 13, 13]
        selected = SCALAR.select_scoreinfos(columns, 10)
        self.assertEqual(
            [(item.score, item.position) for item in selected],
            [(12, 2), (13, 8)],
        )


class OracleContractTests(unittest.TestCase):
    def test_schema_and_plan(self) -> None:
        RUNNER.validate_schema_document()
        rows = RUNNER.validate_plan()
        self.assertEqual(len(rows), 20)
        self.assertIn("fasim/sim.h", RUNNER.SOURCE_INVENTORY)
        self.assertIn("cuda/prealign_cuda_stub.cpp", RUNNER.SOURCE_INVENTORY)

    def test_historical_mismatch_anchors_are_one_based_equivalent(self) -> None:
        hq10, hq11 = RUNNER.CASES
        self.assertEqual(
            (hq10.query_begin + 1, hq10.query_end + 1, hq10.global_target_begin + 1, hq10.global_target_end + 1),
            (1697, 1752, 525, 581),
        )
        self.assertEqual(
            (hq11.query_begin + 1, hq11.query_end + 1, hq11.global_target_begin + 1, hq11.global_target_end + 1),
            (726, 791, 2192, 2253),
        )

    def test_trace_source_contains_all_required_hooks(self) -> None:
        source = (ROOT / "fasim/ssw_oracle_trace.cpp").read_text(encoding="utf-8")
        ssw = (ROOT / "fasim/sswNew.cpp").read_text(encoding="utf-8")
        fastsim = (ROOT / "fasim/fastsim.h").read_text(encoding="utf-8")
        for marker in (
            "FASIM_SSW_ORACLE_TRACE",
            "FASIM_SSW_ORACLE_TRACE_DIR",
            "FASIM_SSW_ORACLE_TRACE_FILTER",
            "FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS",
        ):
            self.assertIn(marker, source)
        for marker in (
            "record_prealign_columns_u8",
            "record_alignment_dp_pass_u8",
            "record_alignment_dp_pass_u16",
            "record_band_iteration",
            "record_emitted_row",
            "publish_workload_records",
        ):
            self.assertIn(marker, ssw + fastsim)
        self.assertIn("finish_scoreinfo_group", fastsim)
        self.assertIn("ssw_oracle_attempt_key", fastsim)

    def test_contracts_state_concrete_tie_rules(self) -> None:
        cigar = (ROOT / "docs/ssw_cuda/CIGAR_CONTRACT.md").read_text(encoding="utf-8")
        endpoint = (ROOT / "docs/ssw_cuda/ENDPOINT_CONTRACT.md").read_text(encoding="utf-8")
        for marker in (
            "extend wins equality",
            "F wins equality",
            "diagonal wins equality",
        ):
            self.assertIn(marker, cigar)
        self.assertIn("strictly greater", endpoint)
        self.assertNotIn("same as SSW", endpoint.lower())
        self.assertIn("LongTarget emitted row (L6)", cigar)


if __name__ == "__main__":
    unittest.main()
