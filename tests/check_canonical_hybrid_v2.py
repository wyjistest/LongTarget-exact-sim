#!/usr/bin/env python3
"""Tests for canonical-hybrid-v2 telemetry and orchestration contracts."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = ROOT / "scripts/canonical_hybrid_v2_telemetry.py"
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_canonical_hybrid_v2.py"
PROTOCOL_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_protocol.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CanonicalHybridTelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.telemetry = load(TELEMETRY_PATH, "canonical_hybrid_v2_telemetry_test")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.output = self.work / "result-TFOsorted"
        self.data_row = (
            "1\t50\t2\t51\tR\tchr1\t101\t150\t1.25\t70\tParaPlus\t1\t80\t50\t0\t25\t25\tACGT\tTGCA"
        )
        header = (
            "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
            "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\tStrand\t"
            "Rule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\tTFO sequence\tTTS sequence\n"
        )
        self.output.write_text(header + self.data_row + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def row(self, **changes):
        digest = self.telemetry.fnv1a64(self.data_row)
        row = {field: "0" for field in self.telemetry.FIELDS}
        row.update(
            batch_id="0",
            attempt_index="0",
            task_id="0",
            scoreinfo_index="0",
            scoreinfo_position="0",
            rule="1",
            strand="0",
            para="1",
            identity_round="6",
            start="2",
            cutlength="50",
            prealign_threshold="80",
            gpu_score="80",
            gpu_query_end="49",
            gpu_ref_end_global="51",
            selected="1",
            selection_reason="threshold",
            cpu_called="1",
            cpu_score="80",
            cpu_query_begin="0",
            cpu_query_end="49",
            cpu_ref_begin_local="0",
            cpu_ref_end_local="49",
            cpu_cigar="50M",
            cpu_emit_reason="threshold",
            converted_row_digest=digest,
            final_row_digest=digest,
            final_status="final_row",
        )
        row.update(changes)
        return row

    def stderr(self) -> str:
        values = {
            "benchmark.fasim_canonical_hybrid_v2_requested": 1,
            "benchmark.fasim_canonical_hybrid_v2_active": 1,
            "benchmark.fasim_canonical_hybrid_v2_telemetry_rows": 1,
            "benchmark.fasim_canonical_hybrid_v2_selected_rows": 1,
            "benchmark.fasim_canonical_hybrid_v2_cpu_traceback_rows": 1,
            "benchmark.fasim_canonical_hybrid_v2_final_row_mappings": 1,
            "benchmark.fasim_gasal2_fallbacks": 0,
            "benchmark.fasim_gasal2_score_selected_attempts": 1,
            "benchmark.fasim_gasal2_cpu_traceback_align_calls": 1,
        }
        values.update({name: 0.01 for name in self.telemetry.TIMING_NAMES})
        return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"

    def write_rows(self, rows) -> Path:
        path = self.work / "attempts.tsv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.telemetry.FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_valid_attempt_maps_every_output_digest(self) -> None:
        result = self.telemetry.validate_attempt(
            self.write_rows([self.row()]), self.output, self.stderr()
        )
        self.assertEqual(result["attempt_rows"], 1)
        self.assertEqual(result["selected_attempts"], 1)
        self.assertEqual(result["output_rows"], 1)

    def test_selected_attempt_without_cpu_traceback_fails(self) -> None:
        path = self.write_rows(
            [self.row(cpu_called="0", cpu_cigar="NA", cpu_emit_reason="not_selected")]
        )
        with self.assertRaisesRegex(ValueError, "exactly one CPU traceback"):
            self.telemetry.read_telemetry(path)

    def test_unmapped_or_mutated_final_digest_fails(self) -> None:
        path = self.write_rows(
            [self.row(converted_row_digest="fnv1a64:0000000000000000", final_row_digest="fnv1a64:0000000000000000")]
        )
        with self.assertRaisesRegex(ValueError, "digest set"):
            self.telemetry.validate_attempt(path, self.output, self.stderr())

    def test_attempt_indexes_must_be_contiguous_per_batch(self) -> None:
        path = self.write_rows([self.row(attempt_index="2")])
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            self.telemetry.read_telemetry(path)


class CanonicalHybridRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load(RUNNER_PATH, "canonical_hybrid_v2_runner_test")

    def row(self, arm="H"):
        return {
            field: "NA" for field in self.runner.PLAN_FIELDS
        } | {
            "arm": arm,
            "gpu_physical_index": "1",
        }

    def test_hybrid_environment_is_exact_and_strips_inherited_fasim(self) -> None:
        row = self.row("H")
        with mock.patch.dict(
            os.environ,
            {"PATH": os.environ.get("PATH", ""), "FASIM_OWNER_VALUE": "must-not-leak"},
            clear=True,
        ):
            environment, explicit = self.runner.sanitized_environment(
                row, Path("/tmp/literal telemetry.tsv")
            )
        self.assertNotIn("FASIM_OWNER_VALUE", environment)
        self.assertEqual(explicit["FASIM_CANONICAL_HYBRID_V2"], "1")
        self.assertEqual(explicit["FASIM_ALIGN_GASAL2_CPU_TRACEBACK"], "1")
        self.assertNotIn("FASIM_ALIGN_GASAL2_CPU_TRACEBACK_ALL", explicit)
        self.assertEqual(explicit["CUDA_VISIBLE_DEVICES"], "1")

    def test_hybrid_backend_command_contains_one_binary_and_no_authority(self) -> None:
        command = self.runner.backend_command(
            Path("/hybrid"), Path("/target"), Path("/query"), Path("/output")
        )
        self.assertEqual(command[0], "/hybrid")
        self.assertNotIn("authority", " ".join(command))
        self.assertEqual(command.count("-f1"), 1)
        self.assertEqual(command.count("-f2"), 1)

    def test_comparator_declared_contract_ignores_full_output_diagnostic(self) -> None:
        values = {
            "baseline_rows": 10,
            "candidate_rows": 10,
            "full_missing_rows": 1,
            "full_extra_rows": 1,
            "clustered_score_top5_equal": 1,
            "clustered_stability_top5_equal": 1,
            "clustered_nt_top5_equal": 1,
            "all_three_top5_equal": 1,
            "boundary_ties_equal": 1,
        }
        result = self.runner.parse_comparator(
            "\n".join(f"{key}={value}" for key, value in values.items()), 1
        )
        self.assertTrue(result["declared_contract_clean"])

    def test_scientific_mismatch_is_parseable_not_a_technical_failure(self) -> None:
        values = {
            "baseline_rows": 10,
            "candidate_rows": 10,
            "full_missing_rows": 1,
            "full_extra_rows": 1,
            "clustered_score_top5_equal": 0,
            "clustered_stability_top5_equal": 1,
            "clustered_nt_top5_equal": 1,
            "all_three_top5_equal": 0,
            "boundary_ties_equal": 1,
        }
        result = self.runner.parse_comparator(
            "\n".join(f"{key}={value}" for key, value in values.items()), 1
        )
        self.assertFalse(result["declared_contract_clean"])
        self.assertEqual(result["returncode"], 1)

    def test_boundary_tie_diagnostic_does_not_expand_declared_contract(self) -> None:
        values = {
            "baseline_rows": 10,
            "candidate_rows": 10,
            "full_missing_rows": 0,
            "full_extra_rows": 0,
            "clustered_score_top5_equal": 1,
            "clustered_stability_top5_equal": 1,
            "clustered_nt_top5_equal": 1,
            "all_three_top5_equal": 1,
            "boundary_ties_equal": 0,
        }
        result = self.runner.parse_comparator(
            "\n".join(f"{key}={value}" for key, value in values.items()), 1
        )
        self.assertTrue(result["declared_contract_clean"])

    def test_partial_attempt_cannot_be_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stage_root = Path(temporary)
            row = self.row("H") | {"attempt_id": "fixed-attempt"}
            (stage_root / ".fixed-attempt.partial.123").mkdir()
            with self.assertRaisesRegex(self.runner.RunnerError, "manual adjudication"):
                self.runner.execute_attempt(
                    row,
                    stage_root,
                    self.runner.ToolPaths(Path("/unused-h"), Path("/unused-a"), Path("/unused-c")),
                    resume=True,
                )

    def test_resume_revalidates_every_completed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = root / "plan.tsv"
            runtime = root / "runtime.json"
            plan.write_text("frozen plan\n", encoding="utf-8")
            runtime.write_text("frozen runtime\n", encoding="utf-8")
            row = self.row("A") | {
                "attempt_id": "complete-a",
                "stage": "regression",
                "validation_id": "v1",
                "runtime_commit": "1" * 40,
                "authority_binary_sha256": "2" * 64,
            }
            destination = root / row["attempt_id"]
            destination.mkdir()
            output = destination / "output.tsv"
            output.write_text("header\nvalue\n", encoding="utf-8")
            manifest_payload, artifact_count = self.runner.artifact_manifest(destination)
            manifest = destination / "artifact-manifest.tsv"
            manifest.write_bytes(manifest_payload)
            manifest_sha256 = self.runner.sha256_file(manifest)
            (destination / "artifact-manifest.sha256").write_text(
                f"{manifest_sha256}  artifact-manifest.tsv\n", encoding="ascii"
            )
            receipt = {
                "schema_version": 1,
                "status": "complete",
                "attempt_id": row["attempt_id"],
                "stage": row["stage"],
                "validation_id": row["validation_id"],
                "arm": "A",
                "config_sha256": self.runner.canonical_digest(row),
                "plan_sha256": self.runner.sha256_file(plan),
                "runtime_receipt_sha256": self.runner.sha256_file(runtime),
                "runtime_commit": row["runtime_commit"],
                "binary_sha256": row["authority_binary_sha256"],
                "retry_policy": "none",
                "replacement_retry_allowed": False,
                "artifact_manifest_sha256": manifest_sha256,
                "artifact_count": artifact_count,
                "output_path": output.name,
                "output_sha256": self.runner.sha256_file(output),
                "execution": {"returncode": 0, "timed_out": False, "oom_detected": False},
                "telemetry_summary": None,
            }
            (destination / "attempt-complete.json").write_text(
                json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8"
            )
            tools = self.runner.ToolPaths(Path("/unused-h"), Path("/unused-a"), Path("/unused-c"))
            with (
                mock.patch.object(self.runner, "PLAN_PATHS", {"regression": plan}),
                mock.patch.object(self.runner, "RUNTIME_RECEIPT_PATH", runtime),
            ):
                reused = self.runner.execute_attempt(row, root, tools, resume=True)
                self.assertEqual(reused["status"], "reused")
                output.write_text("header\nmutated\n", encoding="utf-8")
                with self.assertRaisesRegex(self.runner.RunnerError, "artifact (size|digest) drift"):
                    self.runner.execute_attempt(row, root, tools, resume=True)

    def test_gpu_metrics_are_limited_to_the_fixed_physical_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gpu.csv"
            path.write_text(
                "timestamp,measurement_status,gpu_index,memory_used_mib,memory_total_mib,"
                "utilization_gpu_percent,temperature_gpu_c,power_draw_w,clocks_sm_mhz\n"
                "t,available,0,999,1000,99,90,400,2500\n"
                "t,available,1,111,1000,22,40,100,1500\n",
                encoding="utf-8",
            )
            result = self.runner.gpu_metrics_for_index(path, 1)
            self.assertEqual(result["gpu_sample_count"], 1)
            self.assertEqual(result["gpu_memory_peak_mib"], 111.0)

    def test_protocol_preserves_old_decisions_and_tenfold_gate(self) -> None:
        text = PROTOCOL_PATH.read_text(encoding="utf-8")
        for phrase in (
            "verified_only_contract",
            "sequential verified-v1 Phase 3 B3 = no_go",
            "does not execute a complete CPU authority run",
            "regression evidence only",
            "fresh independent holdout",
            "H speedup versus A >= 10x",
            "No lower substitute threshold",
            "no automatic or replacement retry",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
