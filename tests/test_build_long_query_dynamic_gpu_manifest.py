#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_long_query_dynamic_gpu_manifest.py"
SPEC = importlib.util.spec_from_file_location("build_long_query_dynamic_gpu_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


BINARY_SHA = "1" * 64
HISTORICAL_BINARY_SHA = "2" * 64
TARGET_SHA = "3" * 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DynamicGpuManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="longtarget-manifest-test-")
        self.base = Path(self.temporary.name)
        self.output = self.base / "dynamic.tsv"
        self.receipt = self.base / "receipt.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_row(self, gene_id: str, rank: int) -> dict[str, str]:
        query = self.base / f"{gene_id}.fa"
        sequence = "ACGT" * rank
        query.write_text(f">{gene_id}\n{sequence}\n", encoding="ascii")
        return {
            "original_rank": str(rank),
            "gene_id": gene_id,
            "gene_symbol": f"symbol{rank}",
            "listing_gene_symbol": f"listing{rank}",
            "query_length_nt": str(len(sequence)),
            "estimated_seconds": str(100.0 - rank),
            "query_path": str(query),
            "query_file_sha256": sha256(query),
            "query_sequence_sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
            "output_dir": str(self.base / "source-results" / gene_id),
        }

    def write_manifest(self, name: str, rows: list[dict[str, str]]) -> Path:
        path = self.base / name
        fields = list(BUILDER.REQUIRED_INPUT_FIELDS)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def build(
        self,
        inputs: list[Path],
        reserved: list[Path] | None = None,
        allowed: set[str] | None = None,
    ) -> dict[str, object]:
        return BUILDER.build_manifest(
            inputs,
            reserved or [],
            self.output,
            self.receipt,
            BINARY_SHA,
            allowed or {BINARY_SHA},
            TARGET_SHA,
        )

    def write_completed(self, row: dict[str, str], binary_sha: str = BINARY_SHA) -> None:
        output = Path(row["output_dir"])
        completed = output / "completed"
        runtime_output = completed / "runtime_output"
        runtime_output.mkdir(parents=True)
        artifact = runtime_output / f"target-{row['gene_id']}-TFOsorted"
        artifact.write_bytes(b"byte-identical\n")
        (completed / "stdout.log").write_text("finished normally\n", encoding="utf-8")
        markers = (
            "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_active=1",
            "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_failures=0",
            "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches=0",
            "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0",
            "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0",
            "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_fallbacks=0",
        )
        (completed / "stderr.log").write_text("\n".join(markers) + "\n", encoding="utf-8")
        (completed / "f1.tsv").write_text(
            "ok\tcpu_continuation_failures\n1\t0\n", encoding="utf-8"
        )
        (output / "status.tsv").write_text("field\tvalue\nstatus\tcomplete\n", encoding="utf-8")
        (output / "run-plan.tsv").write_text(
            "field\tvalue\n"
            f"gene_id\t{row['gene_id']}\n"
            f"query_file_sha256\t{row['query_file_sha256']}\n"
            f"query_sequence_sha256\t{row['query_sequence_sha256']}\n"
            f"binary_sha256\t{binary_sha}\n"
            f"target_sha256\t{TARGET_SHA}\n"
            "source_commit\ta438ccf-test\n",
            encoding="utf-8",
        )
        (output / "summary.tsv").write_text(
            "field\tvalue\n"
            "status\tcomplete\n"
            f"gene_id\t{row['gene_id']}\n"
            f"artifact_path\t{artifact}\n"
            f"artifact_sha256\t{sha256(artifact)}\n"
            f"artifact_bytes\t{artifact.stat().st_size}\n"
            "wall_seconds\t12.5\n",
            encoding="utf-8",
        )

    def test_pending_manifest_is_deterministic_and_rank_ordered(self) -> None:
        high_rank = self.make_row("ENSG00000000002", 2)
        low_rank = self.make_row("ENSG00000000001", 1)
        receipt = self.build([self.write_manifest("gpu.tsv", [high_rank, low_rank])])
        self.assertEqual(receipt["source_gpu_jobs"], 2)
        self.assertEqual(receipt["pending_jobs"], 2)
        self.assertEqual(receipt["validated_completed_jobs"], 0)
        with self.output.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual([row["gene_id"] for row in rows], ["ENSG00000000001", "ENSG00000000002"])
        self.assertEqual(sha256(self.output), receipt["output_manifest_sha256"])

    def test_allowed_historical_completion_is_excluded_with_receipt(self) -> None:
        completed = self.make_row("ENSG00000000001", 1)
        pending = self.make_row("ENSG00000000002", 2)
        self.write_completed(completed, HISTORICAL_BINARY_SHA)
        receipt = self.build(
            [self.write_manifest("gpu.tsv", [completed, pending])],
            allowed={BINARY_SHA, HISTORICAL_BINARY_SHA},
        )
        self.assertEqual(receipt["validated_completed_jobs"], 1)
        self.assertEqual(receipt["pending_gene_ids"], [pending["gene_id"]])
        self.assertEqual(receipt["completed"][0]["binary_sha256"], HISTORICAL_BINARY_SHA)

    def test_unapproved_completed_binary_fails_closed(self) -> None:
        row = self.make_row("ENSG00000000001", 1)
        self.write_completed(row, HISTORICAL_BINARY_SHA)
        with self.assertRaisesRegex(BUILDER.ManifestError, "binary digest is not allowed"):
            self.build([self.write_manifest("gpu.tsv", [row])])

    def test_query_sequence_digest_drift_fails_closed(self) -> None:
        row = self.make_row("ENSG00000000001", 1)
        row["query_sequence_sha256"] = "4" * 64
        with self.assertRaisesRegex(BUILDER.ManifestError, "query sequence digest drift"):
            self.build([self.write_manifest("gpu.tsv", [row])])

    def test_reserved_overlap_fails_closed(self) -> None:
        row = self.make_row("ENSG00000000001", 1)
        source = self.write_manifest("gpu.tsv", [row])
        reserved = self.write_manifest("openmp.tsv", [row])
        with self.assertRaisesRegex(BUILDER.ManifestError, "GPU/OpenMP ownership overlap"):
            self.build([source], reserved=[reserved])

    def test_tampered_completed_artifact_fails_closed(self) -> None:
        row = self.make_row("ENSG00000000001", 1)
        self.write_completed(row)
        artifact = next((Path(row["output_dir"]) / "completed" / "runtime_output").iterdir())
        artifact.write_bytes(b"tampered\n")
        with self.assertRaisesRegex(BUILDER.ManifestError, "artifact (size|digest) drift"):
            self.build([self.write_manifest("gpu.tsv", [row])])


if __name__ == "__main__":
    unittest.main()
