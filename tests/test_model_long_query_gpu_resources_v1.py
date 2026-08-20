#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "model_long_query_gpu_resources_v1.py"
SPEC = importlib.util.spec_from_file_location("gpu_resource_model", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class LongQueryGpuResourceModelTests(unittest.TestCase):
    def kernel(self, query_length, name):
        payload = MODULE.build_model([query_length])
        return payload["queries"][0]["kernels"][name]

    def test_main_scoreinfo_11498_is_shared_memory_limited(self):
        current = self.kernel(11498, "main_scoreinfo_current_int16_3state")
        self.assertEqual(current["dynamic_shared_bytes_per_block"], 69024)
        self.assertEqual(current["predicted_resident_blocks_per_sm"], 1)
        self.assertTrue(current["uses_optin_shared_memory"])
        self.assertGreater(current["blocks_by_registers"], 24)

    def test_main_uint8_two_state_candidate_reduces_footprint_by_two_thirds(self):
        payload = MODULE.build_model([11498])
        query = payload["queries"][0]
        candidate = query["kernels"]["main_scoreinfo_uint8_2state_candidate"]
        self.assertEqual(candidate["dynamic_shared_bytes_per_block"], 23008)
        self.assertEqual(candidate["predicted_resident_blocks_per_sm"], 4)
        self.assertAlmostEqual(
            query["derived"]["main_uint8_2state_shared_reduction"], 2.0 / 3.0
        )

    def test_f1_two_state_candidate_passes_only_static_footprint_gate(self):
        payload = MODULE.build_model([8000, 12397])
        short, long = payload["queries"]
        self.assertEqual(
            short["kernels"]["f1_forward_current_uint8_3state"]
            ["predicted_resident_blocks_per_sm"],
            4,
        )
        self.assertEqual(
            long["kernels"]["f1_forward_current_uint8_3state"]
            ["predicted_resident_blocks_per_sm"],
            2,
        )
        self.assertEqual(
            long["kernels"]["f1_forward_uint8_2state_candidate"]
            ["predicted_resident_blocks_per_sm"],
            4,
        )
        self.assertEqual(
            payload["decisions"]["f1_kernel_implementation"],
            "not_authorized_until_runtime_traffic_or_stall_evidence",
        )

    def test_invalid_query_length_fails_closed(self):
        with self.assertRaises(ValueError):
            MODULE.build_model([0])


if __name__ == "__main__":
    unittest.main()
