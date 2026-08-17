#!/usr/bin/env python3
"""Unit tests for deterministic GASAL2 paper source-data freezing."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reproduce/freeze_results.py"


def load_module():
    spec = importlib.util.spec_from_file_location("freeze_results", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load freeze_results module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


class PaperResultFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.freeze = load_module()

    def test_manifest_is_deterministic_and_does_not_hash_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            freeze_id = "paper-data-v1-test-20260716"
            write_tsv(
                source / "benchmark_runs.tsv",
                [{"data_freeze_id": freeze_id, "run_id": "r1"}],
            )
            write_tsv(
                source / "paired_speedups.tsv",
                [{"data_freeze_id": freeze_id, "pair_id_text": "p1"}],
            )

            first = self.freeze.build_source_manifest(source, freeze_id)
            second = self.freeze.build_source_manifest(source, freeze_id)

            self.assertEqual(first, second)
            self.assertEqual(
                [row["path"] for row in first],
                ["benchmark_runs.tsv", "paired_speedups.tsv"],
            )
            self.assertTrue(all(len(row["sha256"]) == 64 for row in first))
            self.assertTrue(all(row["row_count"] == 1 for row in first))
            self.assertNotIn("source_data_manifest.tsv", {row["path"] for row in first})
            self.assertNotIn("DATA_FREEZE.md", {row["path"] for row in first})

    def test_manifest_rejects_mixed_freeze_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            write_tsv(
                source / "benchmark_runs.tsv",
                [{"data_freeze_id": "wrong-freeze", "run_id": "r1"}],
            )
            with self.assertRaisesRegex(ValueError, "data freeze ID mismatch"):
                self.freeze.build_source_manifest(source, "expected-freeze")

    def test_freeze_document_records_provenance_and_limitations(self) -> None:
        rows = [
            {
                "data_freeze_id": "paper-data-v1-test-20260716",
                "path": "benchmark_runs.tsv",
                "kind": "tsv",
                "row_count": 1,
                "size_bytes": 123,
                "sha256": "a" * 64,
            }
        ]
        document = self.freeze.render_freeze_document(
            data_freeze_id="paper-data-v1-test-20260716",
            manifest_rows=rows,
            workload_manifest_sha256="b" * 64,
            artifact_manifest_sha256={"phase2": "c" * 64},
            collector_sha256="d" * 64,
            analyzer_sha256="e" * 64,
            collector_parent_commit="deadbeef",
            analysis_seed=20260715,
            bootstrap_resamples=10000,
        )
        for phrase in (
            "paper-data-v1-test-20260716",
            self.freeze.RUNTIME_COMMIT,
            "paper_runtime_epoch = 0",
            "analysis_seed = 20260715",
            "bootstrap_resamples = 10000",
            "Full KCNQ1OT1 transcript coverage was not run.",
            "Full hg38 was not run.",
            "benchmark_runs.tsv",
            "a" * 64,
        ):
            self.assertIn(phrase, document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
