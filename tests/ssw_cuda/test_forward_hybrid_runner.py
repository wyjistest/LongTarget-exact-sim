#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_runner():
    path = ROOT / "reproduce/ssw_cuda/run_forward_hybrid.py"
    spec = importlib.util.spec_from_file_location("ssw_cuda_phase7_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P7 = load_runner()


def clean_telemetry() -> dict[str, str]:
    row = {field: "0" for field in P7.TELEMETRY_FIELDS}
    row.update(
        schema_version="1",
        backend="cuda-forward-hybrid",
        status="complete",
        device="0",
        flushes="1",
        tasks="2",
        scoreinfos="3",
        attempts="12",
        selected="4",
        cpu_prealign_calls="0",
        cpu_forward_calls="0",
        cpu_reverse_calls="4",
        cpu_banded_sw_calls="4",
        cpu_continuation_calls="4",
        cpu_failures="0",
        fallback_calls="0",
        error="none",
    )
    return row


class ForwardHybridRunnerTests(unittest.TestCase):
    def test_plan_is_exactly_24_regressions_plus_25_new_f_observations(self) -> None:
        rows = P7.check_plan()
        self.assertEqual(len(rows), 49)
        self.assertEqual({row["arm"] for row in rows}, {"F"})
        self.assertEqual(
            sum(row["execution_stage"] == "correctness_regression" for row in rows),
            24,
        )
        self.assertEqual(
            sum(row["execution_stage"] == "fixed_development_pilot" for row in rows),
            25,
        )
        for workload_id in P7.PERFORMANCE_WORKLOADS:
            selected = [
                row
                for row in rows
                if row["workload_id"] == workload_id
                and row["execution_stage"] == "fixed_development_pilot"
            ]
            self.assertEqual({row["observation_id"] for row in selected}, {"1", "2", "3", "4", "5"})
        self.assertTrue(all(row["retry_policy"] == "none" for row in rows))
        self.assertTrue(all(row["maximum_tasks"] == "16" for row in rows))
        self.assertTrue(all(row["attempt_id"].startswith("p7v2") for row in rows))
        self.assertTrue(all("/formal-v2/" in row["artifact_root"] for row in rows))

    def test_fasta_digest_uses_the_frozen_uppercase_normalization(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssw-cuda-p7-fasta-") as directory:
            path = Path(directory) / "masked.fa"
            path.write_bytes(b">masked\nacgtn\nAcGtN\n")
            self.assertEqual(P7.read_fasta(path), b"ACGTNACGTN")

            path.write_bytes(b">invalid\nACGTX\n")
            with self.assertRaises(P7.Phase7Error):
                P7.read_fasta(path)

    def test_telemetry_schema_and_cpu_call_contract_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssw-cuda-p7-telemetry-") as directory:
            path = Path(directory) / "telemetry.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=P7.TELEMETRY_FIELDS,
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow(clean_telemetry())
            parsed = P7.parse_telemetry(path)
            self.assertTrue(P7.telemetry_contract_clean(parsed))

            dirty = dict(parsed)
            dirty["cpu_forward_calls"] = "1"
            self.assertFalse(P7.telemetry_contract_clean(dirty))
            dirty = dict(parsed)
            dirty["cpu_banded_sw_calls"] = "3"
            self.assertFalse(P7.telemetry_contract_clean(dirty))
            dirty = dict(parsed)
            dirty["gpu_h2d_seconds"] = "nan"
            self.assertFalse(P7.telemetry_contract_clean(dirty))

    def test_reference_output_digests_are_bound_without_execution(self) -> None:
        rows = P7.check_plan()
        for row in rows:
            reference = ROOT / row["reference_artifact_root"]
            observed, _ = P7.output_digest(reference)
            self.assertEqual(observed, row["reference_output_digest"], row["attempt_id"])

    def test_comparator_gate_does_not_promote_full_output(self) -> None:
        metrics = {field: 1 for field in P7.COMPARATOR_BINARY_FIELDS}
        metrics.update({field: 0 for field in P7.COMPARATOR_COUNT_FIELDS})
        self.assertTrue(P7.comparison_clean(metrics))
        metrics["full_missing_rows"] = 2
        metrics["full_extra_rows"] = 2
        self.assertTrue(P7.comparison_clean(metrics))
        metrics["clustered_score_top5_equal"] = 0
        self.assertFalse(P7.comparison_clean(metrics))

    def test_cpu_continuation_failure_is_an_implementation_no_go(self) -> None:
        source = [
            {"status": "complete", "cpu_failures": "0"},
            {"status": "technical_failure", "cpu_failures": "1"},
            {"status": "not_started", "cpu_failures": ""},
        ]
        self.assertEqual(P7.implementation_failure_rows(source), [source[1]])
        self.assertEqual(
            P7.classify_phase7(
                technical_complete=False,
                correctness_pass=False,
                implementation_failure_count=1,
            ),
            (
                "forward_hybrid_performance_futility_stop",
                "no_go",
                False,
                "forward_hybrid_implementation_contract_failure",
            ),
        )
        self.assertEqual(
            P7.classify_phase7(
                technical_complete=False,
                correctness_pass=False,
                implementation_failure_count=0,
            )[1],
            "blocked",
        )
        self.assertEqual(
            P7.classify_phase7(
                technical_complete=True,
                correctness_pass=False,
                implementation_failure_count=0,
            )[1],
            "no_go",
        )


if __name__ == "__main__":
    unittest.main()
