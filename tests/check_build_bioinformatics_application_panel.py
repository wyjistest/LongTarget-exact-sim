#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "reproduce/bioinformatics/build_application_panel.py"


class ApplicationPanelBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not BUILDER.is_file():
            raise AssertionError(f"application builder is missing: {BUILDER}")
        spec = importlib.util.spec_from_file_location("build_application_panel", BUILDER)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load application builder")
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        try:
            spec.loader.exec_module(cls.module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bioinformatics-application-builder-")
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_text(self, name: str, text: str) -> Path:
        path = self.work / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_bytes(self, name: str, content: bytes) -> Path:
        path = self.work / name
        path.write_bytes(content)
        return path

    def write_gzip(self, name: str, text: str) -> Path:
        path = self.work / name
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    @staticmethod
    def transcript_row(
        *,
        chromosome: str = "chr21",
        start: str = "100",
        end: str = "900",
        strand: str = "+",
        attributes: str | None = None,
    ) -> str:
        attribute_text = attributes or (
            'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "QUERY"; '
            'gene_type "lncRNA"; level 2; tag "basic";'
        )
        return (
            f"{chromosome}\tHAVANA\ttranscript\t{start}\t{end}\t.\t{strand}\t.\t"
            f"{attribute_text}\n"
        )

    def test_source_contract_is_fixed(self) -> None:
        self.assertEqual(
            self.module.SELECTION_SEED,
            "gasal2-longtarget-phase3-application-v1-20260724",
        )
        self.assertEqual(self.module.ASSEMBLY, "GRCh38")
        self.assertEqual(self.module.ANNOTATION_RELEASE, "GENCODE v49")
        self.assertEqual(
            self.module.PRIMARY_CHROMOSOMES,
            {f"chr{i}" for i in range(1, 23)} | {"chrX"},
        )
        self.assertEqual(self.module.TARGET_CHROMOSOMES, ("chr21", "chr22"))
        self.assertEqual(
            self.module.MANIFEST_FIELDS,
            (
                "record_id",
                "record_role",
                "source_release",
                "assembly",
                "original_gene_id",
                "original_gene_name",
                "original_transcript_id",
                "selection_rule",
                "sequence_length",
                "chromosome",
                "strand",
                "tss",
                "region_start",
                "region_end",
                "sequence_sha256",
                "file_sha256",
                "path",
                "license_note",
                "split",
                "status",
            ),
        )

    def test_transcript_records_are_frozen(self) -> None:
        transcript = self.module.Transcript(
            transcript_id="ENSTQ.1",
            gene_id="ENSGQ.1",
            gene_name="QUERY",
            gene_type="lncRNA",
            chromosome="chr21",
            start=100,
            end=900,
            strand="+",
            level=2,
            tags=frozenset({"basic"}),
        )
        with self.assertRaises(FrozenInstanceError):
            transcript.level = 1

    def test_hash_helpers_are_deterministic(self) -> None:
        content = b"strict-source\x00bytes\n"
        path = self.write_bytes("source.bin", content)
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(self.module.sha256_file(path), expected)
        self.assertEqual(self.module.sha256_stream(io.BytesIO(content)), expected)
        self.assertEqual(
            self.module.sequence_sha256("ACGT"),
            hashlib.sha256(b"ACGT").hexdigest(),
        )

    def test_stable_id_strips_only_the_version_suffix(self) -> None:
        self.assertEqual(self.module.stable_id("ENST000001.17"), "ENST000001")
        self.assertEqual(self.module.stable_id("ENST000001"), "ENST000001")

    def test_open_text_reads_plain_and_gzip_sources(self) -> None:
        plain = self.write_text("source.txt", "alpha\nbeta\n")
        compressed = self.write_gzip("source.txt.gz", "alpha\nbeta\n")
        for path in (plain, compressed):
            with self.subTest(path=path.name), self.module.open_text(path) as handle:
                self.assertEqual(handle.read(), "alpha\nbeta\n")

    def test_parse_attributes_preserves_repeated_and_unquoted_values(self) -> None:
        attributes = self.module.parse_attributes(
            'gene_id "ENSGQ.1"; level 2; tag "basic"; tag "MANE_Select";'
        )
        self.assertEqual(attributes["gene_id"], ("ENSGQ.1",))
        self.assertEqual(attributes["level"], ("2",))
        self.assertEqual(attributes["tag"], ("basic", "MANE_Select"))

    def test_gtf_parser_retains_required_tags_and_strand(self) -> None:
        gtf = self.write_text(
            "fixture.gtf",
            "chr21\tHAVANA\ttranscript\t100\t900\t.\t+\t.\t"
            'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "Q"; '
            'gene_type "lncRNA"; level 2; tag "basic";\n'
            "chr22\tHAVANA\ttranscript\t2000\t4000\t.\t-\t.\t"
            'gene_id "ENSGT.1"; transcript_id "ENSTT.1"; gene_name "T"; '
            'gene_type "protein_coding"; tag "MANE_Select"; '
            'tag "Ensembl_canonical";\n',
        )

        transcripts = self.module.parse_gtf(gtf)

        self.assertEqual(transcripts["ENSTQ.1"].tags, frozenset({"basic"}))
        self.assertEqual(transcripts["ENSTQ.1"].level, 2)
        self.assertEqual(transcripts["ENSTT.1"].strand, "-")
        self.assertEqual(transcripts["ENSTT.1"].level, 99)
        self.assertEqual(
            transcripts["ENSTT.1"].tags,
            frozenset({"MANE_Select", "Ensembl_canonical"}),
        )

    def test_fasta_parser_uppercases_records_deterministically(self) -> None:
        fasta = self.write_gzip(
            "records.fa.gz",
            ">record one\nac\ngt\n>record two\nttaa\n",
        )
        self.assertEqual(
            self.module.parse_fasta(fasta),
            [("record one", "ACGT"), ("record two", "TTAA")],
        )

    def test_fasta_parser_rejects_sequence_before_header(self) -> None:
        fasta = self.write_text("bad.fa", "ACGT\n")
        with self.assertRaisesRegex(ValueError, "before FASTA header"):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_invalid_utf8(self) -> None:
        fasta = self.write_bytes("bad-utf8.fa", b">record\nAC\xffGT\n")
        with self.assertRaises(UnicodeDecodeError):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_duplicate_full_headers(self) -> None:
        fasta = self.write_text(
            "duplicate.fa",
            ">record full description\nACGT\n>record full description\nTGCA\n",
        )
        with self.assertRaisesRegex(ValueError, "duplicate FASTA header"):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_empty_records(self) -> None:
        fixtures = {
            "empty-file.fa": "",
            "empty-middle.fa": ">empty\n>nonempty\nACGT\n",
            "empty-final.fa": ">nonempty\nACGT\n>empty\n",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                fasta = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "empty FASTA record"):
                    self.module.parse_fasta(fasta)

    def test_gtf_parser_rejects_invalid_utf8(self) -> None:
        gtf = self.write_bytes("bad-utf8.gtf", self.transcript_row().encode() + b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_requires_exactly_nine_columns(self) -> None:
        valid_fields = self.transcript_row().rstrip("\n").split("\t")
        fixtures = {
            "eight.gtf": "\t".join(valid_fields[:-1]) + "\n",
            "ten.gtf": "\t".join([*valid_fields, "extra"]) + "\n",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                gtf = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "exactly 9 columns"):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_nonpositive_and_reversed_coordinates(self) -> None:
        fixtures = {
            "zero-start.gtf": self.transcript_row(start="0"),
            "negative-end.gtf": self.transcript_row(end="-1"),
            "reversed.gtf": self.transcript_row(start="901", end="900"),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                gtf = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "invalid GTF coordinates"):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_invalid_transcript_strand(self) -> None:
        gtf = self.write_text("invalid-strand.gtf", self.transcript_row(strand="."))
        with self.assertRaisesRegex(ValueError, "invalid transcript strand"):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_requires_identity_and_type_attributes(self) -> None:
        required = {
            "gene_id": 'gene_id "ENSGQ.1";',
            "transcript_id": 'transcript_id "ENSTQ.1";',
            "gene_name": 'gene_name "QUERY";',
            "gene_type": 'gene_type "lncRNA";',
        }
        complete = " ".join(required.values())
        for missing, clause in required.items():
            with self.subTest(missing=missing):
                attributes = complete.replace(clause, "")
                gtf = self.write_text(
                    f"missing-{missing}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"missing required GTF attribute {missing}",
                ):
                    self.module.parse_gtf(gtf)

        for empty, clause in required.items():
            with self.subTest(empty=empty):
                attributes = complete.replace(clause, f'{empty} " ";')
                gtf = self.write_text(
                    f"empty-{empty}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"missing required GTF attribute {empty}",
                ):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_differing_duplicate_transcript_metadata(self) -> None:
        gtf = self.write_text(
            "duplicate.gtf",
            self.transcript_row() + self.transcript_row(end="901"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate transcript ID ENSTQ.1 has differing metadata",
        ):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_accepts_identical_duplicate_transcript_metadata(self) -> None:
        row = self.transcript_row()
        gtf = self.write_text("identical-duplicate.gtf", row + row)
        transcripts = self.module.parse_gtf(gtf)
        self.assertEqual(list(transcripts), ["ENSTQ.1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
