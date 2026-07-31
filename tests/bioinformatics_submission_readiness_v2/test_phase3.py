from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
SCRIPT_ROOT = ROOT / "reproduce/bioinformatics_submission_readiness_v2"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PREPARE = load_module("v2_prepare_phase3_inputs", SCRIPT_ROOT / "prepare_phase3_inputs.py")
RUNNER = load_module("run_phase4", SCRIPT_ROOT / "run_phase4.py")
ANALYZER = load_module("v2_analyze_phase4", SCRIPT_ROOT / "analyze_phase4.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Phase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (PAPER / "phase_3_input_manifest.tsv").open(newline="", encoding="utf-8") as handle:
            cls.inputs = list(csv.DictReader(handle, delimiter="\t"))
        with (PAPER / "phase_3_attempt_manifest.tsv").open(newline="", encoding="utf-8") as handle:
            cls.attempts = list(csv.DictReader(handle, delimiter="\t"))

    def test_input_panel_is_complete_acgt_and_digest_bound(self) -> None:
        self.assertEqual(len(self.inputs), 10)
        selected = set()
        for row in self.inputs:
            query = PREPARE.read_single_fasta_sequence(ROOT / row["query_path"])
            target = PREPARE.read_single_fasta_sequence(ROOT / row["target_path"])
            self.assertLessEqual(set(query), set("ACGT"))
            self.assertLessEqual(set(target), set("ACGT"))
            self.assertEqual(len(query), int(row["query_sequence_length"]))
            self.assertEqual(len(target), 20_000_001)
            self.assertEqual(PREPARE.sequence_sha256(query), row["query_sequence_sha256"])
            self.assertEqual(PREPARE.sequence_sha256(target), row["target_sequence_sha256"])
            self.assertEqual(int(row["target_region_end0"]) - int(row["target_region_start0"]), 20_000_001)
            selected.update((row["query_sequence_sha256"], row["target_sequence_sha256"]))
        self.assertEqual(len(selected), 20)

    def test_attempt_manifest_is_balanced_and_terminally_preregistered(self) -> None:
        self.assertEqual(len(self.attempts), 100)
        self.assertEqual(
            [int(row["attempt_sequence_index"]) for row in self.attempts],
            list(range(1, 101)),
        )
        pairs = {}
        for row in self.attempts:
            pairs.setdefault(row["pair_id"], []).append(row)
            self.assertEqual(row["attempt_generation"], "1")
            self.assertEqual(row["formal_status"], "preregistered_not_run")
        self.assertEqual(len(pairs), 50)
        self.assertEqual(sum(rows[0]["arm_order"] == "AG" for rows in pairs.values()), 25)
        self.assertEqual(sum(rows[0]["arm_order"] == "GA" for rows in pairs.values()), 25)
        for rows in pairs.values():
            self.assertEqual({row["arm"] for row in rows}, {"A", "G"})

    def test_primary_plan_has_one_gate_and_paired_bootstrap(self) -> None:
        plan = load_json(PAPER / "phase_3_performance_plan.json")
        self.assertEqual(plan["primary_estimand"]["name"], "validated_24_hour_capacity_ratio")
        self.assertEqual(plan["primary_gate"]["capacity_ratio_lcb_minimum"], 10.0)
        self.assertFalse(plan["primary_gate"]["point_estimate_is_second_independent_gate"])
        estimator = plan["capacity_estimator"]
        self.assertEqual(estimator["outer_resampling_unit"], "paired workload")
        self.assertEqual(estimator["inner_resampling_unit"], "paired repeat index within sampled workload")
        self.assertTrue(estimator["scheduler_replayed_per_bootstrap_replicate"])
        self.assertEqual(estimator["bootstrap_replicates"], 100000)
        self.assertEqual(plan["failure_denominator"]["planned_pair_rows"], 50)

    def test_runner_commands_bind_frozen_resources(self) -> None:
        row = self.attempts[0]
        query = ROOT / row["query_path"]
        target = ROOT / row["target_path"]
        gpu_row = next(item for item in self.attempts if item["arm"] == "G")
        gpu = RUNNER.gpu_command(gpu_row, Path("/attempt"), query, target)
        self.assertIn(RUNNER.IMAGE_TAG, gpu)
        self.assertIn(f"GASAL2_GPU_SCREEN_CONTAINER_DIGEST={RUNNER.IMAGE_DIGEST}", gpu)
        self.assertNotIn("--gpus", gpu)
        for device in (
            "/dev/nvidia0",
            "/dev/nvidiactl",
            "/dev/nvidia-uvm",
            "/dev/nvidia-uvm-tools",
        ):
            self.assertIn(device, gpu)
        cpu_row = next(item for item in self.attempts if item["arm"] == "A")
        cpu = RUNNER.cpu_command(cpu_row, Path("/attempt"), query, target)
        self.assertIn(str(RUNNER.CPU_RUNNER), cpu)
        self.assertIn("0-4,10-14", cpu)

    def test_runner_enforces_total_and_phase4_artifact_quotas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            phase4 = root / "phase4"
            phase4.mkdir()
            (root / "preexisting.bin").write_bytes(b"12345")
            (phase4 / "new.bin").write_bytes(b"123")
            plan = {
                "budgets": {
                    "total_v2_artifact_bytes": 9,
                    "phase4_max_new_artifact_bytes": 3,
                }
            }
            with (
                mock.patch.object(RUNNER, "V2_ARTIFACT_ROOT", root),
                mock.patch.object(RUNNER, "PHASE4_ROOT", phase4),
            ):
                self.assertEqual(
                    RUNNER.check_artifact_budgets(plan),
                    {"total_v2_artifact_bytes": 8, "phase4_new_artifact_bytes": 3},
                )
                (phase4 / "overflow.bin").write_bytes(b"x")
                with self.assertRaises(RUNNER.Phase4Error):
                    RUNNER.check_artifact_budgets(plan)
                (phase4 / "overflow.bin").unlink()
                plan["budgets"]["total_v2_artifact_bytes"] = 7
                with self.assertRaises(RUNNER.Phase4Error):
                    RUNNER.check_artifact_budgets(plan)

    def test_external_panel_is_region_level_and_label_blind(self) -> None:
        with (PAPER / "phase_3_external_attempt_manifest.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 10)
        self.assertEqual({row["tool_role"] for row in rows}, {
            "primary_current_executable",
            "legacy_executable",
        })
        for row in rows:
            target = ROOT / row["target_path"]
            self.assertEqual(sha256(target), row["target_fasta_sha256"])
            headers = [line[1:] for line in target.read_text().splitlines() if line.startswith(">")]
            self.assertEqual(len(headers), 1000)
            self.assertTrue(all(header.startswith("bt5_") for header in headers))
            self.assertEqual(row["labels_visible_to_backend"], "0")
            self.assertIn("# Duplex-ID", row["region_score_mapping"])
            self.assertEqual(row["formal_status"], "preregistered_not_run")

    def test_phase4_artifacts_do_not_exist_before_freeze(self) -> None:
        self.assertFalse((ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase4").exists())


if __name__ == "__main__":
    unittest.main()
