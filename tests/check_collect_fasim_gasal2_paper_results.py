#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reproduce/collect_results.py"


def load_module():
    if not SCRIPT.is_file():
        raise AssertionError("paper result collector is missing")
    spec = importlib.util.spec_from_file_location("paper_result_collector", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load paper result collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PaperResultCollectorTests(unittest.TestCase):
    def test_machine_id_ignores_dynamic_nvidia_timestamp_and_utilization(self) -> None:
        module = load_module()
        base = {
            "platform": "Linux-test",
            "lscpu": {
                "stdout": "Model name: Test CPU\nCPU MHz: 1200\n",
            },
            "nvidia_smi": {
                "stdout": (
                    "Timestamp : first\nDriver Version : 555.42.06\n"
                    "Product Name : NVIDIA GeForce RTX 4090\nGpu : 99 %\n"
                )
            },
        }
        changed = {
            **base,
            "lscpu": {"stdout": "Model name: Test CPU\nCPU MHz: 4700\n"},
            "nvidia_smi": {
                "stdout": (
                    "Timestamp : second\nDriver Version : 555.42.06\n"
                    "Product Name : NVIDIA GeForce RTX 4090\nGpu : 0 %\n"
                )
            },
        }

        self.assertEqual(module.machine_id(base), module.machine_id(changed))
        self.assertTrue(module.machine_id(base).startswith("machine-"))

    def test_pair_normalization_retains_mismatch_without_excluding_it(self) -> None:
        module = load_module()
        row = {
            "pair_id_text": "g02__pair01__0",
            "workload_id": "g02",
            "claim_id": "C2",
            "pair_id": "1",
            "pair_order": "AB",
            "runtime_epoch": "0",
            "runtime_commit": module.RUNTIME_COMMIT,
            "preset_id": "preset-v1",
            "output_contract": "fast_topk_score_stability_nt",
            "baseline_wall_seconds": "10",
            "candidate_wall_seconds": "2",
            "paired_speedup": "5",
            "status": "mismatch",
            "decision": "contract_mismatch",
            "pair_summary_path": "pairs-v1/g02/pair-summary.json",
        }
        manifest = {
            "g02": {
                "role": "generalization_core",
                "query_id": "MALAT1",
                "query_length_nt": "2048",
                "target_id": "chr21",
                "preset_id": "preset-v1",
            }
        }

        normalized = module.normalize_pair(
            row,
            manifest,
            data_freeze_id="freeze-test",
            machine="machine-test",
            artifact_sha256="a" * 64,
        )

        self.assertEqual(normalized["status"], "mismatch")
        self.assertEqual(normalized["excluded"], 0)
        self.assertEqual(normalized["exclusion_reason"], "NA")
        self.assertEqual(normalized["data_freeze_id"], "freeze-test")

    def test_pair_normalization_rejects_manifest_preset_drift(self) -> None:
        module = load_module()
        row = {
            "pair_id_text": "w__pair01__0",
            "workload_id": "w",
            "claim_id": "C1",
            "pair_id": "1",
            "pair_order": "AB",
            "runtime_epoch": "0",
            "runtime_commit": module.RUNTIME_COMMIT,
            "preset_id": "observed",
            "output_contract": "contract",
            "baseline_wall_seconds": "10",
            "candidate_wall_seconds": "5",
            "paired_speedup": "2",
            "status": "clean",
            "decision": "clean",
            "pair_summary_path": "pair.json",
        }
        manifest = {
            "w": {
                "role": "core",
                "query_id": "H19",
                "query_length_nt": "2812",
                "target_id": "chr22",
                "preset_id": "frozen",
            }
        }

        with self.assertRaisesRegex(ValueError, "preset drift"):
            module.normalize_pair(
                row,
                manifest,
                data_freeze_id="freeze-test",
                machine="machine-test",
                artifact_sha256="a" * 64,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
