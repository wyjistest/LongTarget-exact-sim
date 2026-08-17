from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reproduce.biological_topk import freeze_fresh_holdout as frozen
from reproduce.biological_topk import run_fresh_holdout_repair1 as repair


ROOT = Path(__file__).resolve().parents[2]
RUNNER_SHA256 = "82d88b6687b5ad67e7f8c5e3e58f276bd31b2a042f6872f9289e11566d3f0d2b"
ANALYZER_SHA256 = "05f68a62727d342b3abf168f3d892cb430763031351e7c21ca62f49b1c396cbe"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Phase4RepairFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.attempts, cls.plan, _ = repair.validate_repair_plan()
        cls.original = repair.read_tsv(repair.ORIGINAL_ATTEMPT_PLAN_PATH, frozen.ATTEMPT_FIELDS)

    def test_repair_freeze_artifacts_reproduce_byte_for_byte(self) -> None:
        for path, payload in repair.build_repair_artifacts().items():
            self.assertEqual(path.read_bytes(), payload, path)

    def test_repair_is_the_only_full_panel_infrastructure_epoch(self) -> None:
        self.assertEqual(len(self.manifest), 178)
        self.assertEqual(len(self.original), len(self.attempts), 368)
        self.assertEqual(self.plan["repair_epoch"], 1)
        self.assertEqual(self.plan["repair_epoch_limit"], 1)
        self.assertTrue(self.plan["full_panel_rerun"])
        self.assertTrue(self.plan["original_evidence_retained"])
        self.assertFalse(self.plan["scientific_input_changed"])
        self.assertFalse(self.plan["scientific_contract_changed"])
        self.assertFalse(self.plan["runtime_binary_changed"])
        self.assertFalse(self.plan["panel_or_attempt_order_changed"])

    def test_repair_preserves_every_frozen_scientific_and_execution_identity(self) -> None:
        identity_fields = (
            "execution_index",
            "workload_id",
            "repeat_id",
            "primary_instance",
            "independent_sample",
            "arm",
            "pair_order",
            "arm_launch_order",
            "worker_index",
            "query_ordinal_namespace",
            "query_source_ordinal",
            "query_sequence_sha256",
            "target_ordinal_namespace",
            "target_source_ordinal",
            "target_sequence_sha256",
            "assembly",
            "target_coordinate_namespace",
            "query_extraction_recipe_id",
            "target_extraction_recipe_id",
            "input_pair_digest",
            "parameter_bundle_sha256",
            "binary_path",
            "binary_sha256",
            "gpu_physical_index",
            "cpu_affinity",
            "timeout_seconds",
            "retry_policy",
            "comparison_policy",
        )
        for source, row in zip(self.original, self.attempts):
            self.assertEqual(row["attempt_id"], f"r1_{source['attempt_id']}")
            self.assertEqual(row["validation_instance_id"], f"r1_{source['validation_instance_id']}")
            self.assertEqual(row["supersedes_attempt_id"], source["attempt_id"])
            self.assertEqual(row["repair_epoch"], "1")
            for field in identity_fields:
                self.assertEqual(row[field], source[field], (source["attempt_id"], field))

    def test_incident_retains_failures_and_forbids_scientific_retry(self) -> None:
        incident = json.loads(repair.INCIDENT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(incident["terminal_attempt_count"], 3)
        self.assertEqual(incident["successful_attempt_count"], 1)
        self.assertEqual(incident["budget_stop_technical_failure_count"], 2)
        self.assertFalse(incident["comparison_started"])
        self.assertFalse(incident["automatic_retry_used"])
        self.assertEqual(incident["repair_epoch_authorized"], 1)
        self.assertEqual(incident["repair_epoch_limit"], 1)
        self.assertTrue(incident["old_evidence_retention"].startswith("all terminal receipts"))

    def test_repair_runner_and_analyzer_remain_pinned(self) -> None:
        self.assertEqual(sha256_file(Path(repair.__file__).resolve()), RUNNER_SHA256)
        self.assertEqual(sha256_file(repair.REPAIR_ANALYZER_PATH), ANALYZER_SHA256)
        self.assertEqual(self.plan["runner_sha256"], RUNNER_SHA256)
        self.assertEqual(self.plan["analyzer_sha256"], ANALYZER_SHA256)

    def test_g_attempt_is_rejected_before_launch_without_raw_reservation(self) -> None:
        called = False

        def forbidden_launch(*_args, **_kwargs):
            nonlocal called
            called = True
            raise AssertionError("G attempt launched after the storage guard failed")

        with (
            mock.patch.object(
                repair,
                "directory_bytes",
                side_effect=(frozen.MAX_STORAGE_BYTES, 0),
            ),
            mock.patch.object(repair, "ORIGINAL_EXECUTE_ATTEMPT", forbidden_launch),
        ):
            with self.assertRaisesRegex(
                repair.RepairError,
                "fixed storage quota cannot reserve one raw telemetry attempt",
            ):
                repair.execute_attempt(
                    {"arm": "G"},
                    {},
                    mock.sentinel.inputs,
                    mock.sentinel.snapshot,
                    "0" * 40,
                )
        self.assertFalse(called)

    def test_telemetry_gzip_is_deterministic_and_lossless(self) -> None:
        raw = (b"batch_id\tattempt_index\n" + b"0\t0\n" * 4096)
        compressed_payloads = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory_name:
                destination = Path(directory_name)
                (destination / "telemetry.json").write_bytes(raw)
                (destination / "attempt-complete.json").write_text(
                    json.dumps({"artifact_manifest_sha256": "uncompressed"}),
                    encoding="utf-8",
                )
                repair.gzip_telemetry(destination)
                compressed = destination / "attempt-telemetry.tsv.gz"
                compressed_payloads.append(compressed.read_bytes())
                self.assertFalse((destination / "telemetry.json").exists())
                with gzip.open(compressed, "rb") as handle:
                    self.assertEqual(handle.read(), raw)
                receipt = json.loads(
                    (destination / "attempt-complete.json").read_text(encoding="utf-8")
                )
                self.assertEqual(receipt["telemetry_uncompressed_size_bytes"], len(raw))
                self.assertEqual(
                    receipt["telemetry_uncompressed_sha256"],
                    hashlib.sha256(raw).hexdigest(),
                )
                self.assertEqual(receipt["telemetry_compressed_sha256"], sha256_file(compressed))
                self.assertEqual(receipt["telemetry_storage_policy"], repair.TELEMETRY_STORAGE_POLICY)
        self.assertEqual(compressed_payloads[0], compressed_payloads[1])
        self.assertEqual(compressed_payloads[0][4:8], b"\x00\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
