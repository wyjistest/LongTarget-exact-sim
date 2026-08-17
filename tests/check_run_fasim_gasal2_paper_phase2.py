#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "run_fasim_gasal2_paper_phase2.py"
DRIVER_SPEC = importlib.util.spec_from_file_location("paper_phase2_driver", DRIVER)
if DRIVER_SPEC is None or DRIVER_SPEC.loader is None:
    raise RuntimeError(f"cannot load {DRIVER}")
DRIVER_MODULE = importlib.util.module_from_spec(DRIVER_SPEC)
DRIVER_SPEC.loader.exec_module(DRIVER_MODULE)
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


class PaperPhase2DriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.binary = self.work / "fake-binary"
        self.manifest = self.work / "manifest.tsv"
        self.artifacts = self.work / "artifacts"
        self.query.write_text(">query\nACGTACGT\n", encoding="utf-8")
        self.target.write_text(">target\n" + "ACGT" * 32 + "\n", encoding="utf-8")
        self.binary.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        self.binary.chmod(0o755)
        row = {
            "workload_id": "synthetic_core",
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
            "max_wall_seconds": "10",
            "preset_id": "test_v1",
            "preregistered": "1",
            "adapter_id": "synthetic_test",
        }
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerow(row)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_driver(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["FASIM_PAPER_HARNESS_TEST_MODE"] = "1"
        env["FASIM_PAPER_TEST_GPU_COUNT"] = "0"
        return subprocess.run(
            [
                "python3",
                str(DRIVER),
                "--manifest",
                str(self.manifest),
                "--binary",
                str(self.binary),
                "--artifact-root",
                str(self.artifacts),
                "--workload-id",
                "synthetic_core",
                *args,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_dry_run_expands_warmups_and_balanced_pairs(self) -> None:
        first = self.run_driver("--dry-run")
        second = self.run_driver("--dry-run")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        plan = json.loads(first.stdout)
        self.assertEqual(plan["schema_version"], 1)
        self.assertEqual(plan["workload_count"], 1)
        self.assertEqual(plan["pair_count"], 2)
        self.assertEqual(plan["timed_run_count"], 4)
        self.assertEqual(plan["warmup_count"], 2)
        self.assertEqual(
            {pair["pair_order"] for pair in plan["pairs"]},
            {"AB", "BA"},
        )

    def test_executes_pairs_and_writes_digest_aware_receipts(self) -> None:
        result = self.run_driver()
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dirs = [
            path
            for path in self.artifacts.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and path.name != "pairs"
            and not path.name.startswith("pairs-v")
        ]
        self.assertEqual(len(run_dirs), 6)
        pair_receipts = sorted((self.artifacts / "pairs-v3").glob("*/pair-complete.json"))
        self.assertEqual(len(pair_receipts), 2)
        with (self.artifacts / "phase2-pairs.tsv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            self.assertTrue(
                {
                    "baseline_gpu_temperature_peak_c",
                    "candidate_gpu_temperature_peak_c",
                    "baseline_gpu_power_peak_w",
                    "candidate_gpu_power_peak_w",
                    "candidate_active_path",
                    "candidate_worker_count",
                    "candidate_gpu_ids",
                    "candidate_lifecycle_count",
                    "candidate_slot_rotation_clean",
                    "candidate_host_overlap_seconds",
                    "candidate_state_order_allocation_violations",
                    "archive_restore_clean",
                    "exact_work_equal",
                }.issubset(set(reader.fieldnames or []))
            )
            pairs = list(reader)
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(row["status"] == "clean" for row in pairs))
        self.assertTrue(all(row["top5_score_equal"] == "1" for row in pairs))
        self.assertEqual(
            (self.artifacts / "phase2-failures.tsv").read_text(encoding="utf-8").count("\n"),
            1,
        )
        for table in (
            "phase2-runs.tsv",
            "phase2-pairs.tsv",
            "phase2-failures.tsv",
            "phase2-artifacts.tsv",
        ):
            self.assertNotIn(b"\r\n", (self.artifacts / table).read_bytes())
        resumed = self.run_driver("--resume")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertIn("reused_pairs=2", resumed.stdout)

    def test_resume_rejects_pair_component_receipt_drift(self) -> None:
        first = self.run_driver()
        self.assertEqual(first.returncode, 0, first.stderr)
        receipt = self.artifacts / "synthetic_core__pair01__baseline__0" / "run-complete.json"
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        payload["status"] = "tampered"
        receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        resumed = self.run_driver("--resume")
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("pair component receipt digest mismatch", resumed.stderr)

    def test_new_comparator_receipts_preserve_and_ignore_v2_pair_tree(self) -> None:
        legacy = self.artifacts / "pairs-v2" / "legacy-pair"
        legacy.mkdir(parents=True)
        sentinel = legacy / "pair-summary.json"
        sentinel.write_text('{"status":"mismatch"}\n', encoding="utf-8")
        (legacy / "pair-complete.json").write_text(
            '{"status":"complete"}\n', encoding="utf-8"
        )
        failed = self.artifacts / "pairs-v2" / "legacy-pair.failed.1"
        failed.mkdir()
        (failed / "pair-config.json").write_text(
            '{"pair_id_text":"legacy-pair"}\n', encoding="utf-8"
        )
        (failed / "pair-failure.json").write_text(
            '{"status":"technical_failure","reason":"pair_comparator_failure"}\n',
            encoding="utf-8",
        )

        result = self.run_driver()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), '{"status":"mismatch"}\n')
        receipts = sorted((self.artifacts / "pairs-v3").glob("*/pair-complete.json"))
        self.assertEqual(len(receipts), 2)
        failures = (self.artifacts / "phase2-failures.tsv").read_text(encoding="utf-8")
        self.assertIn("pairs-v2/legacy-pair", failures)
        self.assertIn("superseded_derived_pair", failures)
        self.assertIn("pairs-v2/legacy-pair.failed.1", failures)
        self.assertNotIn("missing_run_config", failures)

    def test_two_slot_contract_uses_rotation_and_overlap_not_live_count_two(self) -> None:
        baseline = self.work / "baseline"
        candidate = self.work / "candidate"
        compare_work = self.work / "compare"
        (baseline / "output").mkdir(parents=True)
        (candidate / "output").mkdir(parents=True)
        compare_work.mkdir()
        header = (
            "Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\t"
            "StartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\tMeanStability\n"
        )
        row = "chr21\t1\t10\t+\t0\t1\t10\t1\t10\t+\t20\t10\t90\t5\n"
        for root in (baseline, candidate):
            (root / "output" / "result-TFOsorted.lite").write_text(
                header + row, encoding="utf-8"
            )
        metrics = {
            "requested": 1,
            "active": 1,
            "flushes_gpu_submitted": 97,
            "flushes_finalized": 97,
            "flushes_committed": 97,
            "slot0_submit_count": 49,
            "slot1_submit_count": 48,
            "max_live_slots": 1,
            "host_scheduling_overlap_seconds": 10.3,
            "legacy_fallback_flushes": 0,
            "state_transition_violations": 0,
            "order_violations": 0,
            "allocation_failures": 0,
        }
        lines = ["benchmark.fasim_gasal2_fallbacks=0"]
        lines.extend(
            f"benchmark.fasim_gasal2_flush_two_slot_overlap_{key}={value}"
            for key, value in metrics.items()
        )
        lines.append(
            "benchmark.fasim_gasal2_flush_two_slot_overlap_decision="
            "two_slot_active_clean_no_fallback"
        )
        (candidate / "stderr.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = DRIVER_MODULE.compare_two_slot(baseline, candidate, compare_work)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["candidate_max_live_slots"], 1)
        self.assertEqual(result["candidate_slot_rotation_clean"], 1)

    def test_relocates_published_topk_artifact_paths_without_changing_raw_report(self) -> None:
        self.assertTrue(
            hasattr(DRIVER_MODULE, "write_relocated_topk_report"),
            "Phase 2 driver must normalize stale atomic-publication paths",
        )
        run_dir = self.work / "published-run"
        output_dir = run_dir / "output"
        compare_dir = self.work / "compare"
        output_dir.mkdir(parents=True)
        compare_dir.mkdir()
        report_path = output_dir / "report.json"
        stale_root = self.work / ".published-run.partial.123" / "output"
        artifacts = {
            "topk_summary_output": "topk_summary.tsv",
            "topk_rows_output": "topk_rows.tsv",
            "topk_lite_output": "topk-TFOsorted.lite",
        }
        original = {field: str(stale_root / name) for field, name in artifacts.items()}
        report_path.write_text(json.dumps(original) + "\n", encoding="utf-8")
        for name in artifacts.values():
            (output_dir / name).write_text("fixture\n", encoding="utf-8")

        relocated = DRIVER_MODULE.write_relocated_topk_report(
            report_path,
            run_dir,
            compare_dir / "relocated-report.json",
        )

        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8")), original)
        normalized = json.loads(relocated.read_text(encoding="utf-8"))
        for field, name in artifacts.items():
            self.assertEqual(normalized[field], str(output_dir / name))

    def test_technical_pair_comparator_failure_is_preserved(self) -> None:
        workload_id = "broken_pair"
        for mode in ("baseline", "candidate"):
            run_dir = self.artifacts / f"{workload_id}__pair01__{mode}__0"
            (run_dir / "output").mkdir(parents=True)
            (run_dir / "run-complete.json").write_text(
                json.dumps({"status": "complete", "mode": mode}) + "\n",
                encoding="utf-8",
            )
        (
            self.artifacts
            / f"{workload_id}__pair01__baseline__0"
            / "output"
            / "result.txt"
        ).write_text("ok\n", encoding="utf-8")
        row = {
            "workload_id": workload_id,
            "claim_id": "C1",
            "output_contract": "fast_topk_score_stability_nt",
            "adapter_id": "synthetic_test",
        }
        pair = {"pair_id": 1, "pair_order": "AB"}

        with self.assertRaises(FileNotFoundError):
            DRIVER_MODULE.publish_pair(row, pair, self.artifacts, resume=False)

        pair_root = self.artifacts / "pairs-v3"
        self.assertEqual(len(list(pair_root.glob(f"{workload_id}__pair01__0.failed.*"))), 1)
        self.assertFalse(any(pair_root.glob(".*.partial.*")))


if __name__ == "__main__":
    unittest.main()
