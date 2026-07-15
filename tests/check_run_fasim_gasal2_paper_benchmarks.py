#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "run_fasim_gasal2_paper_benchmarks.sh"
COLLECTOR = ROOT / "scripts" / "collect_fasim_gasal2_paper_run.py"

FIELDS = [
    "workload_id",
    "claim_id",
    "family",
    "role",
    "query_id",
    "query_path",
    "query_sha256",
    "query_start_nt",
    "query_end_nt",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_path",
    "target_sha256",
    "target_region",
    "rule",
    "baseline_mode",
    "candidate_mode",
    "output_contract",
    "required_pairs",
    "requires_gpu_count",
    "max_wall_seconds",
    "preset_id",
    "preregistered",
    "adapter_id",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PaperHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.binary = self.work / "fake-binary"
        self.query.write_text(">query\nACGTACGT\n", encoding="utf-8")
        self.target.write_text(">chrTest\n" + "ACGT" * 32 + "\n", encoding="utf-8")
        self.binary.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        self.binary.chmod(0o755)
        self.manifest = self.work / "manifest.tsv"
        self.write_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self) -> None:
        rows = [
            {
                "workload_id": "synthetic_cpu",
                "claim_id": "C1",
                "family": "test",
                "role": "core",
                "query_id": "query",
                "query_path": str(self.query),
                "query_sha256": digest(self.query),
                "query_start_nt": "0",
                "query_end_nt": "8",
                "query_length_nt": "8",
                "fragment_position": "full",
                "target_id": "target",
                "target_path": str(self.target),
                "target_sha256": digest(self.target),
                "target_region": "full",
                "rule": "0",
                "baseline_mode": "synthetic_baseline",
                "candidate_mode": "synthetic_candidate",
                "output_contract": "fast_topk_score_stability_nt",
                "required_pairs": "2",
                "requires_gpu_count": "0",
                "max_wall_seconds": "1",
                "preset_id": "test_v1",
                "preregistered": "1",
                "adapter_id": "synthetic_test",
            },
            {
                "workload_id": "synthetic_gpu",
                "claim_id": "C4",
                "family": "test",
                "role": "breadth",
                "query_id": "query",
                "query_path": str(self.query),
                "query_sha256": digest(self.query),
                "query_start_nt": "0",
                "query_end_nt": "8",
                "query_length_nt": "8",
                "fragment_position": "full",
                "target_id": "target",
                "target_path": str(self.target),
                "target_sha256": digest(self.target),
                "target_region": "slice:0-64",
                "rule": "0",
                "baseline_mode": "synthetic_baseline",
                "candidate_mode": "synthetic_candidate",
                "output_contract": "fast_topk_score_stability_nt",
                "required_pairs": "1",
                "requires_gpu_count": "1",
                "max_wall_seconds": "30",
                "preset_id": "test_v1",
                "preregistered": "1",
                "adapter_id": "synthetic_test",
            },
        ]
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

    def run_harness(self, *args: str, gpu_count: str = "0") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["FASIM_PAPER_HARNESS_TEST_MODE"] = "1"
        env["FASIM_PAPER_TEST_GPU_COUNT"] = gpu_count
        return subprocess.run(
            [
                "bash",
                str(HARNESS),
                "--manifest",
                str(self.manifest),
                "--binary",
                str(self.binary),
                *args,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_dry_run_expands_all_rows_and_is_seed_reproducible(self) -> None:
        first = self.run_harness("--dry-run", "--seed", "20260715")
        second = self.run_harness("--dry-run", "--seed", "20260715")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        plan = json.loads(first.stdout)
        self.assertEqual(plan["schema_version"], 1)
        self.assertEqual(plan["workload_count"], 2)
        self.assertEqual(plan["run_count"], 6)
        run_ids = {row["run_id"] for row in plan["runs"]}
        self.assertIn("synthetic_cpu__pair01__baseline__0", run_ids)
        self.assertIn("synthetic_cpu__pair02__candidate__0", run_ids)
        self.assertIn("synthetic_gpu__pair01__baseline__0", run_ids)
        pair_orders = {
            (row["workload_id"], row["pair_id"]): row["pair_order"]
            for row in plan["runs"]
        }
        self.assertEqual(len(pair_orders), 3)
        self.assertTrue(all(value in {"AB", "BA"} for value in pair_orders.values()))

    def test_duplicate_resume_and_config_drift_fail_closed(self) -> None:
        artifacts = self.work / "artifacts"
        args = (
            "--artifact-root",
            str(artifacts),
            "--workload-id",
            "synthetic_cpu",
            "--pair-id",
            "1",
            "--mode",
            "baseline",
        )
        first = self.run_harness(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        duplicate = self.run_harness(*args)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("duplicate run ID", duplicate.stderr)
        resumed = self.run_harness(*args, "--resume")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertIn("reused", resumed.stdout)

        self.binary.write_text("#!/usr/bin/env bash\n# changed\nexit 0\n", encoding="utf-8")
        self.binary.chmod(0o755)
        drift = self.run_harness(*args, "--resume")
        self.assertNotEqual(drift.returncode, 0)
        self.assertIn("config digest mismatch", drift.stderr)

    def test_incomplete_receipt_cannot_resume(self) -> None:
        artifacts = self.work / "artifacts"
        run_dir = artifacts / "synthetic_cpu__pair01__candidate__0"
        run_dir.mkdir(parents=True)
        result = self.run_harness(
            "--artifact-root",
            str(artifacts),
            "--workload-id",
            "synthetic_cpu",
            "--pair-id",
            "1",
            "--mode",
            "candidate",
            "--resume",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete receipt", result.stderr)

    def test_warmup_has_a_separate_receipt(self) -> None:
        artifacts = self.work / "artifacts"
        result = self.run_harness(
            "--artifact-root",
            str(artifacts),
            "--workload-id",
            "synthetic_cpu",
            "--mode",
            "baseline",
            "--warmup",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = artifacts / "synthetic_cpu__warmup__baseline__0"
        receipt = json.loads((run_dir / "run-complete.json").read_text(encoding="utf-8"))
        config = json.loads((run_dir / "run-config.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "complete")
        self.assertTrue(config["warmup"])
        self.assertEqual(config["pair_id"], 0)

    def test_collector_rejects_missing_required_files(self) -> None:
        run_dir = self.work / "incomplete"
        run_dir.mkdir()
        result = subprocess.run(
            [
                "python3",
                str(COLLECTOR),
                "--run-dir",
                str(run_dir),
                "--output",
                str(self.work / "summary.json"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing collector input", result.stderr)

    def test_collector_reports_peak_gpu_resources(self) -> None:
        run_dir = self.work / "complete"
        run_dir.mkdir()
        payloads = {
            "run-config.json": {
                "run_id": "synthetic_cpu__pair01__baseline__0",
                "workload_id": "synthetic_cpu",
                "pair_id": 1,
                "mode": "baseline",
                "runtime_epoch": 0,
                "config_digest_sha256": "a" * 64,
            },
            "environment.json": {"schema_version": 1},
            "execution.json": {
                "returncode": 0,
                "wall_seconds": 1.25,
                "timed": True,
                "command": ["synthetic"],
            },
            "correctness.json": {"status": "synthetic_clean"},
        }
        for name, payload in payloads.items():
            (run_dir / name).write_text(json.dumps(payload) + "\n", encoding="utf-8")
        (run_dir / "stdout.log").write_text("", encoding="utf-8")
        (run_dir / "stderr.log").write_text("", encoding="utf-8")
        (run_dir / "time.txt").write_text(
            "Maximum resident set size (kbytes): 1234\n", encoding="utf-8"
        )
        (run_dir / "gpu-memory.csv").write_text(
            (
                "timestamp,measurement_status,gpu_index,memory_used_mib,memory_total_mib,"
                "utilization_gpu_percent,temperature_gpu_c,power_draw_w,clocks_sm_mhz\n"
                "t0,available,0,10,100,20,30,40.5,50\n"
                "t1,available,0,25,100,80,60,90.5,100\n"
            ),
            encoding="utf-8",
        )
        output = self.work / "summary.json"
        result = subprocess.run(
            ["python3", str(COLLECTOR), "--run-dir", str(run_dir), "--output", str(output)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(summary["gpu_measurement_status"], "available")
        self.assertEqual(summary["gpu_memory_peak_mib"], 25.0)
        self.assertEqual(summary["gpu_utilization_peak_percent"], 80.0)
        self.assertEqual(summary["gpu_temperature_peak_c"], 60.0)
        self.assertEqual(summary["gpu_power_peak_w"], 90.5)
        self.assertEqual(summary["gpu_sm_clock_peak_mhz"], 100.0)

    def test_gpu_unavailable_reports_blocked_reason(self) -> None:
        result = self.run_harness(
            "--artifact-root",
            str(self.work / "artifacts"),
            "--workload-id",
            "synthetic_gpu",
            "--pair-id",
            "1",
            "--mode",
            "baseline",
            gpu_count="0",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("blocked_reason=insufficient_visible_gpus", result.stderr)
        self.assertNotIn("gpu_memory_bytes=0", result.stderr)

    def test_timeout_is_preserved_as_a_typed_failed_run(self) -> None:
        artifacts = self.work / "artifacts"
        with mock.patch.dict(os.environ, {"FASIM_PAPER_TEST_SLEEP_SECONDS": "2"}):
            result = self.run_harness(
                "--artifact-root",
                str(artifacts),
                "--workload-id",
                "synthetic_cpu",
                "--pair-id",
                "1",
                "--mode",
                "candidate",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("paper benchmark command timed out", result.stderr)
        failed = list(artifacts.glob("synthetic_cpu__pair01__candidate__0.failed.*"))
        self.assertEqual(len(failed), 1)
        execution = json.loads((failed[0] / "execution.json").read_text(encoding="utf-8"))
        correctness = json.loads((failed[0] / "correctness.json").read_text(encoding="utf-8"))
        self.assertEqual(execution["returncode"], 124)
        self.assertTrue(execution["timed_out"])
        self.assertEqual(correctness["status"], "technical_failure")
        self.assertEqual(correctness["reason"], "timeout")
        self.assertFalse(any(artifacts.glob(".*.partial.*")))

    def test_gpu_sample_schema_supports_peak_resource_collection(self) -> None:
        artifacts = self.work / "artifacts"
        result = self.run_harness(
            "--artifact-root",
            str(artifacts),
            "--workload-id",
            "synthetic_cpu",
            "--pair-id",
            "1",
            "--mode",
            "baseline",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        sample = (
            artifacts / "synthetic_cpu__pair01__baseline__0" / "gpu-memory.csv"
        ).read_text(encoding="utf-8")
        header = sample.splitlines()[0].split(",")
        self.assertEqual(
            header,
            [
                "timestamp",
                "measurement_status",
                "gpu_index",
                "memory_used_mib",
                "memory_total_mib",
                "utilization_gpu_percent",
                "temperature_gpu_c",
                "power_draw_w",
                "clocks_sm_mhz",
            ],
        )


if __name__ == "__main__":
    unittest.main()
