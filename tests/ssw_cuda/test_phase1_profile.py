#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "reproduce/ssw_cuda/run_cpu_profile.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("ssw_cuda_phase1_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase 1 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


class Phase1ProfileTests(unittest.TestCase):
    def test_frozen_plan_is_complete_and_consumed(self) -> None:
        rows = RUNNER.validate_plan()
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({row["attempt_id"] for row in rows}), 50)
        self.assertEqual({row["retry_policy"] for row in rows}, {"none"})
        by_workload = {}
        for row in rows:
            by_workload.setdefault(row["workload_id"], []).append(row)
        self.assertEqual(set(by_workload), {spec["workload_id"] for spec in RUNNER.WORKLOAD_SPECS})
        self.assertTrue(all(len(items) == 10 for items in by_workload.values()))

    def test_recovery_plan_is_complete_and_changes_only_execution_identity(self) -> None:
        v1_rows = RUNNER.validate_plan()
        v2_rows = RUNNER.validate_recovery_plan()
        self.assertEqual(len(v2_rows), 50)
        self.assertEqual({row["timeout_seconds"] for row in v2_rows}, {"7200"})
        self.assertTrue(all(row["attempt_id"].startswith("p1v2_") for row in v2_rows))
        self.assertTrue(
            all("/profile-runs-v2/" in row["expected_artifact_root"] for row in v2_rows)
        )
        ignored = {"attempt_id", "timeout_seconds", "expected_artifact_root"}
        for v1, v2 in zip(v1_rows, v2_rows):
            self.assertEqual(
                {key: value for key, value in v1.items() if key not in ignored},
                {key: value for key, value in v2.items() if key not in ignored},
            )

    def test_quantile_and_bootstrap_are_deterministic(self) -> None:
        values = [0.1, 0.2, 0.3, 0.4]
        self.assertAlmostEqual(RUNNER.quantile(values, 0.25), 0.175)
        self.assertEqual(
            RUNNER.bootstrap_median_ci(values, 9),
            RUNNER.bootstrap_median_ci(values, 9),
        )

    def test_amdahl_closed_at_or_below_point_nine(self) -> None:
        metric = {
            "bootstrap_median_ci95": {"lower": 0.90, "upper": 0.92},
        }
        stats = {
            "workloads": {
                "large_h19_chr21": {
                    "steady_state": {"p_backend_addressable": metric},
                },
                "large_h19_chr22": {
                    "steady_state": {"p_backend_addressable": metric},
                },
            }
        }
        decision = RUNNER.build_decision(stats)
        self.assertEqual(decision["bioinformatics_b3_track"], "closed_amdahl")
        self.assertEqual(decision["maximum_speedup_infinite"], 10.000000000000002)
        self.assertIsNone(decision["required_backend_speedup"])

    def test_amdahl_open_above_point_nine(self) -> None:
        maximum, required = RUNNER.amdahl_projection(0.91)
        self.assertAlmostEqual(maximum, 1.0 / 0.09)
        self.assertAlmostEqual(required, 91.0)

    def test_instrumentation_is_default_off_and_has_all_stages(self) -> None:
        main_source = (ROOT / "fasim/Fasim-LongTarget.cpp").read_text(encoding="utf-8")
        ssw_header = (ROOT / "fasim/ssw.h").read_text(encoding="utf-8")
        self.assertIn('getenv("FASIM_SSW_CUDA_PHASE1_PROFILE")', main_source)
        for stage in (
            "PRE_ALIGN",
            "SELECTION",
            "FORWARD_ALIGNMENT",
            "REVERSE_ALIGNMENT",
            "BANDED_TRACEBACK",
            "BACKEND_BRIDGE",
            "TRIPLEX_CONVERSION",
            "STABILITY_IDENTITY_NT",
            "CLUSTER_RANK_SORT",
            "SERIALIZATION_IO",
        ):
            self.assertIn(f"FASIM_AUTHORITY_STAGE_{stage}", ssw_header)


if __name__ == "__main__":
    unittest.main()
