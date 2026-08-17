#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "decode_promoter_case",
    SCRIPTS / "decode_exact_long_query_hybrid_promoter_case_v1.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fasta(path: Path, header: str, sequence: str) -> None:
    path.write_text(f">{header}\n{sequence}\n", encoding="ascii")


def write_tsv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_zstd_tsv(path: Path) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["zstd", "-q", "-d", "-c", str(path)],
        check=True,
        stdout=subprocess.PIPE,
    )
    lines = completed.stdout.decode("utf-8").splitlines()
    return list(csv.DictReader(lines, delimiter="\t"))


class DecodePromoterCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="decode-promoter-case-")
        self.root = Path(self.temporary.name)
        self.promoters = self.root / "promoters"
        self.promoters.mkdir()
        self.shards = self.promoters / "shards"
        self.shards.mkdir()
        self.query = self.root / "query.fa"
        self.full = self.promoters / "promoter_components_concat.fa"
        self.shard1 = self.shards / "shard_0001.fa"
        self.shard2 = self.shards / "shard_0002.fa"
        write_fasta(self.query, "ENSGTEST", "AAAAAAAAAA")
        write_fasta(self.shard1, "shard_0001", "TTTT")
        write_fasta(self.shard2, "shard_0002", "ACGTACGTNACG")
        write_fasta(self.full, "full", "TTTTACGTACGTNACG")
        component_fields = (
            "component_id", "chromosome", "genomic_start0", "genomic_end0",
            "logical_concat_start0", "logical_concat_end0", "shard_id",
            "shard_start0", "shard_end0", "n_count",
        )
        write_tsv(self.promoters / "promoter_components.tsv", component_fields, [
            dict(zip(component_fields, ("C0", "chr1", 100, 104, 0, 4, "shard_0001", 0, 4, 0))),
            dict(zip(component_fields, ("C1", "chr1", 200, 206, 4, 10, "shard_0002", 0, 6, 0))),
            dict(zip(component_fields, ("C2", "chr1", 300, 306, 10, 16, "shard_0002", 6, 12, 1))),
        ])
        membership_fields = (
            "component_id", "promoter_id", "gene_id", "gene_name", "biotype",
            "gene_strand", "tss1", "promoter_genomic_start0", "promoter_genomic_end0",
        )
        write_tsv(self.promoters / "promoter_membership.tsv", membership_fields, [
            dict(zip(membership_fields, ("C0", "P0", "G0", "G0", "pc", "+", 102, 100, 104))),
            dict(zip(membership_fields, ("C1", "P1", "G1", "G1", "pc", "+", 203, 200, 206))),
            dict(zip(membership_fields, ("C2", "P2", "G2", "G2", "pc", "-", 303, 300, 306))),
        ])
        shard_fields = (
            "shard_id", "first_component_id", "last_component_id", "fasta_path",
            "file_sha256", "shard_length_bp", "logical_concat_start0",
        )
        write_tsv(self.promoters / "shards.tsv", shard_fields, [
            dict(zip(shard_fields, ("shard_0001", "C0", "C0", "shards/shard_0001.fa", sha256(self.shard1), 4, 0))),
            dict(zip(shard_fields, ("shard_0002", "C1", "C2", "shards/shard_0002.fa", sha256(self.shard2), 12, 4))),
        ])
        self.case = self.root / "case"
        runtime = self.case / "runtime_output"
        runtime.mkdir(parents=True)
        self.tfosorted = runtime / "synthetic-TFOsorted"
        accepted = self.row(1, 3, 2, 4, "AAA", "CGT")
        cross_component = self.row(1, 4, 5, 8, "AAAA", "ACGT")
        overlaps_n = self.row(1, 3, 8, 10, "AAA", "TNA")
        write_tsv(
            self.tfosorted,
            MODULE.TFOSORTED_COLUMNS,
            [accepted, cross_component, overlaps_n, accepted],
        )
        query_sequence_sha = hashlib.sha256(b"AAAAAAAAAA").hexdigest()
        receipt = {
            "status": "complete",
            "technical_contract_pass": True,
            "query": {
                "gene_id": "ENSGTEST",
                "gene_symbol": "TEST",
                "path": str(self.query),
                "file_sha256": sha256(self.query),
                "sequence_sha256": query_sequence_sha,
                "length_nt": 10,
            },
            "target": {
                "artifact_id": "shard_0002",
                "path": str(self.shard2),
                "file_sha256": sha256(self.shard2),
                "length_bp": 12,
                "logical_offset0": 4,
            },
            "artifacts": [{
                "role": "complete_tfosorted",
                "path": str(self.tfosorted),
                "bytes": self.tfosorted.stat().st_size,
                "sha256": sha256(self.tfosorted),
            }],
        }
        (self.case / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def row(
        query_start: int,
        query_end: int,
        target_start: int,
        target_end: int,
        tfo: str,
        tts: str,
    ) -> dict[str, object]:
        return {
            "QueryStart": query_start,
            "QueryEnd": query_end,
            "StartInSeq": target_start,
            "EndInSeq": target_end,
            "Direction": "R",
            "Chr": "",
            "StartInGenome": target_start,
            "EndInGenome": target_end,
            "MeanStability": "1.5",
            "MeanIdentity(%)": "75",
            "Strand": "ParaPlus",
            "Rule": "2",
            "Score": "10",
            "Nt(bp)": len(tts),
            "Class": "0",
            "MidPoint": (query_start + query_end) // 2,
            "Center": (query_start + query_end) // 2,
            "TFO sequence": tfo,
            "TTS sequence": tts,
        }

    def test_decodes_shard_coordinates_and_rejects_invalid_hits(self) -> None:
        output = self.root / "decoded" / "ENSGTEST"
        result = MODULE.decode_case(self.case, output, self.promoters)
        self.assertEqual(result["raw_source_rows"], 4)
        self.assertEqual(result["decoded_unique_source_hits"], 3)
        self.assertEqual(result["exact_duplicate_rows_removed"], 1)
        self.assertEqual(result["retained_source_hits"], 1)
        self.assertEqual(result["rejected_source_hits"], 2)
        self.assertEqual(
            result["rejection_reason_counts"],
            {"cross_component_boundary": 1, "overlaps_reference_N": 1},
        )
        decoded = read_zstd_tsv(output / "decoded-TFOsorted.tsv.zst")
        self.assertEqual([row["StartInSeq"] for row in decoded], ["6", "9", "12"])
        self.assertEqual([row["EndInGenome"] for row in decoded], ["8", "12", "14"])
        retained = list(csv.DictReader((output / "retained-TFOsorted").read_text().splitlines(), delimiter="\t"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]["StartInSeq"], "6")
        mapped = read_zstd_tsv(output / "mapped_promoter_associations.tsv.zst")
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["component_id"], "C1")
        self.assertEqual(mapped[0]["promoter_id"], "P1")
        self.assertEqual(mapped[0]["logical_concat_start0"], "5")

    def test_logicalize_row_rejects_bad_coordinate(self) -> None:
        row = {field: "0" for field in MODULE.TFOSORTED_COLUMNS}
        row["StartInSeq"] = "bad"
        with self.assertRaises(MODULE.DecodeError):
            MODULE.logicalize_row(row, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
