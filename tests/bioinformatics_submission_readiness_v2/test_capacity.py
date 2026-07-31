from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "reproduce/bioinformatics_submission_readiness_v2/capacity.py"
SPEC = importlib.util.spec_from_file_location("v2_capacity", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {PATH}")
CAPACITY = importlib.util.module_from_spec(SPEC)
sys.modules["v2_capacity"] = CAPACITY
SPEC.loader.exec_module(CAPACITY)


class CapacityTests(unittest.TestCase):
    def test_scheduler_is_stable_list_scheduling(self) -> None:
        self.assertEqual(CAPACITY.scheduled_makespan([4.0, 3.0, 2.0], 2), 5.0)

    def test_capacity_ratio_uses_makespans(self) -> None:
        result = CAPACITY.capacity_summary(
            [10.0, 1.0, 1.0],
            [2.0, 2.0, 2.0],
            authority_workers=2,
            gpu_workers=2,
        )
        self.assertEqual(result["authority_makespan_seconds"], 10.0)
        self.assertEqual(result["gpu_makespan_seconds"], 4.0)
        self.assertEqual(result["capacity_ratio"], 2.5)

    def test_bootstrap_is_paired_and_deterministic(self) -> None:
        rows = [
            CAPACITY.WorkloadTimings("w1", (20.0, 22.0), (2.0, 2.2)),
            CAPACITY.WorkloadTimings("w2", (40.0, 44.0), (4.0, 4.4)),
        ]
        first = CAPACITY.paired_hierarchical_bootstrap(
            rows, authority_workers=1, gpu_workers=1, replicates=100, seed=7
        )
        second = CAPACITY.paired_hierarchical_bootstrap(
            rows, authority_workers=1, gpu_workers=1, replicates=100, seed=7
        )
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["point_estimate"]["capacity_ratio"], 10.0)
        self.assertAlmostEqual(first["bootstrap"]["one_sided_95_lcb"], 10.0)

    def test_unpaired_or_nonpositive_timings_fail(self) -> None:
        with self.assertRaises(CAPACITY.CapacityError):
            CAPACITY.WorkloadTimings("w", (1.0,), (1.0, 2.0)).validate()
        with self.assertRaises(CAPACITY.CapacityError):
            CAPACITY.scheduled_makespan([0.0], 1)


if __name__ == "__main__":
    unittest.main()
