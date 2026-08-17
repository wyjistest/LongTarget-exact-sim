#!/usr/bin/env python3
"""Unit tests for the Phase 2 mismatch traceback replay."""

from __future__ import annotations

import importlib.util
import csv
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "reproduce/bioinformatics/replay_phase2_traceback_cases.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("phase2_traceback_replay", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load traceback replay runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReplayPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()
        cls.plan = cls.runner.read_plan()

    def test_plan_is_bounded_diagnostic_and_preserves_decisions(self) -> None:
        self.assertFalse(self.plan["promotion_eligible"])
        self.assertEqual(self.plan["execution"]["retry_policy"], "none")
        self.assertEqual(
            self.plan["historical_contract"]["phase2_decision"],
            "verified_only_contract",
        )
        self.assertEqual(
            self.plan["historical_contract"]["phase3_b3_decision"],
            "no_go_for_sequential_verified_v1",
        )
        self.assertFalse(self.plan["historical_contract"]["rewrites_historical_decisions"])

    def test_plan_contains_only_two_known_mismatches_and_three_fixed_modes(self) -> None:
        self.assertEqual(
            [case["attempt_id"] for case in self.plan["cases"]],
            ["hq10_ht02__repeat00", "hq11_ht02__repeat00"],
        )
        self.assertEqual(
            [mode["mode_id"] for mode in self.plan["modes"]],
            ["gpu_traceback", "gpu_traceback_no_staged_prune", "strict_cpu_traceback"],
        )
        strict = self.plan["modes"][2]
        self.assertEqual(strict["expected_output"], "authority")
        self.assertEqual(
            strict["set_environment"],
            {
                "FASIM_ALIGN_GASAL2_CPU_TRACEBACK": "1",
                "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_STRICT": "1",
            },
        )

    def test_plan_does_not_generalize_two_cases_into_a_promotion_rate(self) -> None:
        encoded = str(self.plan).lower()
        self.assertNotIn("allowlist", encoded)
        self.assertNotIn("mismatch_rate", encoded)
        self.assertEqual(self.plan["purpose"], "post_hoc_root_cause_diagnostic_only")

    def test_environment_is_sanitized_and_mode_overrides_are_exact(self) -> None:
        inherited = {
            "PATH": os.environ.get("PATH", ""),
            "FASIM_UNRELATED_OWNER_VALUE": "must-not-leak",
            "FASIM_ALIGN_GASAL2_CPU_TRACEBACK": "must-not-leak",
        }
        with mock.patch.dict(os.environ, inherited, clear=True):
            gpu_env, gpu_explicit = self.runner.replay_environment(
                self.plan, self.plan["modes"][0]
            )
            strict_env, strict_explicit = self.runner.replay_environment(
                self.plan, self.plan["modes"][2]
            )
        self.assertNotIn("FASIM_UNRELATED_OWNER_VALUE", gpu_env)
        self.assertNotIn("FASIM_ALIGN_GASAL2_CPU_TRACEBACK", gpu_explicit)
        self.assertEqual(strict_explicit["FASIM_ALIGN_GASAL2_CPU_TRACEBACK"], "1")
        self.assertEqual(
            gpu_explicit["CUDA_VISIBLE_DEVICES"],
            str(self.plan["replay_device"]["physical_index"]),
        )
        self.assertEqual(strict_env["PATH"], inherited["PATH"])

    def test_metric_parser_requires_exact_single_integer_values(self) -> None:
        stderr = "\n".join(
            f"{self.runner.METRIC_PREFIX}{name}={index}"
            for index, name in enumerate(self.runner.METRICS)
        )
        parsed = self.runner.parse_metrics(stderr)
        self.assertEqual(tuple(parsed), self.runner.METRICS)
        with self.assertRaisesRegex(self.runner.ReplayError, "missing telemetry"):
            self.runner.parse_metrics(stderr.splitlines()[0])
        with self.assertRaisesRegex(self.runner.ReplayError, "duplicate telemetry"):
            self.runner.parse_metrics(stderr + "\n" + stderr.splitlines()[0])

    def test_plan_only_is_stable_and_does_not_require_raw_artifacts(self) -> None:
        first = self.runner.plan_summary(self.plan)
        second = self.runner.plan_summary(self.plan)
        self.assertEqual(first, second)
        self.assertEqual(first["run_count"], 6)
        self.assertFalse(first["promotion_eligible"])


class ReplayEvidenceTests(unittest.TestCase):
    def test_checked_in_evidence_is_complete_when_present(self) -> None:
        table = ROOT / "paper/bioinformatics/phase2_traceback_replay.tsv"
        receipt_path = ROOT / "paper/bioinformatics/phase2_traceback_replay_receipt.json"
        if not table.is_file() or not receipt_path.is_file():
            self.skipTest("replay evidence is created only after preexecution freeze")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        with table.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 6)
        self.assertEqual(receipt["run_count"], 6)
        self.assertTrue(receipt["all_outputs_byte_equal"])
        self.assertFalse(receipt["promotion_eligible"])
        self.assertFalse(receipt["dp_tie_cell_localized"])
        self.assertFalse(receipt["cross_gpu_architecture_generalized"])
        strict = [row for row in rows if row["replay_mode"] == "strict_cpu_traceback"]
        self.assertEqual(
            [(row["attempt_id"], row["cpu_traceback_align_calls"]) for row in strict],
            [("hq10_ht02__repeat00", "641"), ("hq11_ht02__repeat00", "827")],
        )
        self.assertTrue(all(row["expected_output_side"] == "authority" for row in strict))


if __name__ == "__main__":
    unittest.main()
