from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "reproduce/bioinformatics_submission_readiness_v2/run_development_harness.py"
SPEC = importlib.util.spec_from_file_location("v2_development_harness", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["v2_development_harness"] = MODULE
SPEC.loader.exec_module(MODULE)


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def row(query: str = "ACGT", target: str = "TGCA") -> dict[str, str]:
    return {
        "workload_id": "unit",
        "query_ordinal_namespace": "unit_query",
        "query_source_ordinal": "1",
        "target_ordinal_namespace": "unit_target",
        "target_source_ordinal": "1",
        "assembly": "unit",
        "target_coordinate_namespace": "unit_0_based_half_open",
        "target_region_start0": "100",
        "query_extraction_recipe_id": "unit_query_recipe",
        "target_extraction_recipe_id": "unit_target_recipe",
        "query_sequence_length": str(len(query)),
        "target_sequence_length": str(len(target)),
        "query_sequence_sha256": sequence_sha256(query),
        "target_sequence_sha256": sequence_sha256(target),
    }


def write_inputs(root: Path, query: str, target: str) -> None:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "query.fa").write_text(f">query\n{query}\n", encoding="ascii")
    (inputs / "target.fa").write_text(f">target\n{target}\n", encoding="ascii")


class DevelopmentHarnessTests(unittest.TestCase):
    def test_preflight_rejects_non_acgt_before_backend_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_inputs(root, "ACGN", "TGCA")
            with self.assertRaisesRegex(
                (MODULE.HarnessError, MODULE.candidate_sites.CandidateSitesError),
                "unsupported|non-ACGT",
            ):
                MODULE.validate_preflight(root, row("ACGN", "TGCA"))

    def test_gpu_command_binds_frozen_image_and_explicit_devices(self) -> None:
        command = MODULE.gpu_command(Path("/attempt"), row(), "unit", 60, "0-4")
        self.assertIn(MODULE.IMAGE_TAG, command)
        self.assertIn(
            f"GASAL2_GPU_SCREEN_CONTAINER_DIGEST={MODULE.IMAGE_DIGEST}",
            command,
        )
        self.assertNotIn("--gpus", command)
        for device in (
            "/dev/nvidia0",
            "/dev/nvidiactl",
            "/dev/nvidia-uvm",
            "/dev/nvidia-uvm-tools",
        ):
            self.assertIn(device, command)

    def test_preflight_failure_is_retained_as_terminal_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            source = temporary_root / "source"
            source.mkdir()
            query = source / "query.fa"
            target = source / "target.fa"
            query.write_text(">query\nACGN\n", encoding="ascii")
            target.write_text(">target\nTGCA\n", encoding="ascii")
            artifacts = temporary_root / "artifacts"
            with (
                mock.patch.object(MODULE, "ARTIFACT_ROOT", artifacts),
                mock.patch.object(MODULE, "source_inputs", return_value=(query, target)),
            ):
                result = MODULE.execute_pair(row("ACGN", "TGCA"), timeout=1, affinity="0")
            self.assertEqual(result["status"], "development_failure")
            self.assertRegex(result["failure_reason"], "unsupported|non-ACGT")
            receipt = artifacts / "phase2_dev_unit/pair-complete.json"
            self.assertTrue(receipt.is_file())
            self.assertEqual(json.loads(receipt.read_text())["status"], "development_failure")

    def test_existing_incomplete_attempt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary)
            (artifacts / "phase2_dev_unit").mkdir()
            with mock.patch.object(MODULE, "ARTIFACT_ROOT", artifacts):
                with self.assertRaisesRegex(MODULE.HarnessError, "terminal receipt"):
                    MODULE.execute_pair(row(), timeout=1, affinity="0")


if __name__ == "__main__":
    unittest.main()
