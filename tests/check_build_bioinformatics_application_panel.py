#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import inspect
import io
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "reproduce/bioinformatics/build_application_panel.py"
HOLDOUT_MANIFEST_FIELDS = (
    "workload_id",
    "query_id",
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
    "target_id",
    "target_gene_id",
    "target_gene_name",
    "target_chromosome",
    "target_strand",
    "target_tss",
    "target_region_start",
    "target_region_end",
    "target_length_bp",
    "target_sequence_sha256",
    "target_file_sha256",
    "target_path",
    "assembly",
    "annotation_release",
    "selection_seed",
    "requested_contract",
    "run_modes",
    "repeat_count",
    "status",
)
HOLDOUT_QUERY_FIELDS = (
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
)


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

    def write_tsv(
        self,
        name: str,
        fieldnames: tuple[str, ...],
        rows: list[dict[str, str]],
    ) -> Path:
        path = self.work / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def unique_query_sequence(index: int, length: int = 700) -> str:
        alphabet = "ACGT"
        value = index + 1
        prefix: list[str] = []
        for _ in range(12):
            prefix.append(alphabet[value % 4])
            value //= 4
        return "".join(prefix) + "A" * (length - len(prefix))

    def add_query_record(
        self,
        records: list[tuple[str, str]],
        transcripts: dict[str, object],
        *,
        transcript_id: str,
        gene_id: str,
        sequence: str,
        gene_name: str | None = None,
        gene_type: str = "lncRNA",
        chromosome: str = "chr1",
        level: int = 1,
        basic: bool = True,
        declared_length: str | None = None,
        description: str = "",
    ) -> None:
        name = gene_name or self.module.stable_id(gene_id)
        tags = frozenset({"basic"}) if basic else frozenset()
        transcripts[transcript_id] = self.module.Transcript(
            transcript_id=transcript_id,
            gene_id=gene_id,
            gene_name=name,
            gene_type=gene_type,
            chromosome=chromosome,
            start=100,
            end=100 + len(sequence) - 1,
            strand="+",
            level=level,
            tags=tags,
        )
        length_text = str(len(sequence)) if declared_length is None else declared_length
        records.append(
            (
                f"{transcript_id}|{gene_id}|-|-|{name}-201|{name}|{length_text}|{description}",
                sequence,
            )
        )

    def basic_query_fixture(
        self,
        count: int,
    ) -> tuple[list[tuple[str, str]], dict[str, object]]:
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        for index in range(1, count + 1):
            self.add_query_record(
                records,
                transcripts,
                transcript_id=f"ENSTQ{index:05d}.1",
                gene_id=f"ENSGQ{index:05d}.1",
                gene_name=f"QUERY{index:05d}",
                sequence=self.unique_query_sequence(index),
            )
        return records, transcripts

    @staticmethod
    def no_development_exclusions() -> dict[str, set[str]]:
        return {"gene_id": set(), "gene_name": set(), "sequence_sha256": set()}

    @staticmethod
    def holdout_row(
        *,
        workload_id: str = "hq01_ht01",
        query_id: str = "hq01",
        gene_id: str = "ENSGHOLD.3",
        query_sequence_sha256: str = "a" * 64,
    ) -> dict[str, str]:
        row = {field: "fixture" for field in HOLDOUT_MANIFEST_FIELDS}
        row.update(
            {
                "workload_id": workload_id,
                "query_id": query_id,
                "gene_id": gene_id,
                "gene_name": "HOLDOUT",
                "transcript_id": "ENSTHOLD.1",
                "query_length_nt": "700",
                "length_stratum": "le_800",
                "query_sequence_sha256": query_sequence_sha256,
                "query_file_sha256": "b" * 64,
                "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq01.fa",
                "target_id": "ht01",
                "target_gene_id": "ENSGTARGET.1",
                "target_gene_name": "TARGET",
                "target_chromosome": "chr1",
                "target_strand": "+",
                "target_tss": "1000",
                "target_region_start": "1",
                "target_region_end": "2501",
                "target_length_bp": "2501",
                "target_sequence_sha256": "c" * 64,
                "target_file_sha256": "d" * 64,
                "target_path": "reproduce/bioinformatics/holdout_inputs/targets/ht01.fa",
                "assembly": "GRCh38",
                "annotation_release": "GENCODE v49",
                "selection_seed": "gasal2-longtarget-phase2-holdout-v1-20260724",
                "requested_contract": "all-ranked-top5",
                "run_modes": "authority,candidate,verified",
                "repeat_count": "1",
                "status": "preregistered_not_run",
            }
        )
        return row

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

    def test_fasta_parser_preserves_padded_headers_for_selector_rejection(self) -> None:
        padded_headers = {
            "leading-after-marker": (
                " ENSTPARSER.1|ENSGPARSER.1|-|-|PARSER-201|PARSER|700|"
            ),
            "terminal-whitespace": (
                "ENSTPARSER.1|ENSGPARSER.1|-|-|PARSER-201|PARSER|700|   "
            ),
        }
        for name, padded_header in padded_headers.items():
            with self.subTest(name=name):
                records, transcripts = self.basic_query_fixture(50)
                self.add_query_record(
                    records,
                    transcripts,
                    transcript_id="ENSTPARSER.1",
                    gene_id="ENSGPARSER.1",
                    gene_name="PARSER",
                    sequence=self.unique_query_sequence(930),
                )
                records[-1] = (padded_header, records[-1][1])
                fasta = self.write_text(
                    f"padded-header-{name}.fa",
                    "".join(f">{header}\n{sequence}\n" for header, sequence in records),
                )

                parsed_records = self.module.parse_fasta(fasta)

                with self.assertRaisesRegex(ValueError, "GENCODE v49 FASTA"):
                    self.module.select_queries(
                        fasta_records=parsed_records,
                        transcripts=transcripts,
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_fasta_parser_requires_header_marker_in_first_column(self) -> None:
        fasta = self.write_text("indented-header.fa", "  >record\nACGT\n")
        with self.assertRaisesRegex(ValueError, "before FASTA header"):
            self.module.parse_fasta(fasta)

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
            "whitespace-header.fa": ">   \nACGT\n",
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

    def test_query_selection_public_signatures_are_explicit(self) -> None:
        expected_parameters = {
            "read_development_exclusions": ("path",),
            "read_holdout_exclusions": ("path",),
            "choose_query_representative": ("rows",),
            "query_representative_key": ("row",),
            "query_selection_hash": ("row",),
            "select_queries": (
                "fasta_records",
                "transcripts",
                "development_exclusions",
                "holdout_gene_ids",
                "holdout_sequence_sha256",
            ),
        }
        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                signature = inspect.signature(getattr(self.module, name))
                self.assertEqual(tuple(signature.parameters), parameters)
        select_signature = inspect.signature(self.module.select_queries)
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.KEYWORD_ONLY
                for parameter in select_signature.parameters.values()
            )
        )

    def test_development_exclusions_use_exact_schema_and_normalize_only_gene_ids(self) -> None:
        digest = "e" * 64
        path = self.write_text(
            "development.tsv",
            "exclusion_type\tvalue\treason\n"
            "gene_id\tENSGDEV.17\tused gene\n"
            "gene_name\tGENE.NAME.9\tused name\n"
            f"sequence_sha256\t{digest}\tused sequence\n",
        )

        exclusions = self.module.read_development_exclusions(path)

        self.assertEqual(
            exclusions,
            {
                "gene_id": {"ENSGDEV"},
                "gene_name": {"GENE.NAME.9"},
                "sequence_sha256": {digest},
            },
        )

    def test_development_exclusions_reject_wrong_schema_types_and_rows(self) -> None:
        fixtures = {
            "wrong-header.tsv": "type\tvalue\treason\ngene_id\tENSG1\tused\n",
            "unsupported-type.tsv": (
                "exclusion_type\tvalue\treason\ntranscript_id\tENST1\tused\n"
            ),
            "missing-column.tsv": "exclusion_type\tvalue\treason\ngene_id\tENSG1\n",
            "extra-column.tsv": (
                "exclusion_type\tvalue\treason\ngene_id\tENSG1\tused\textra\n"
            ),
            "blank-value.tsv": "exclusion_type\tvalue\treason\ngene_id\t\tused\n",
            "blank-reason.tsv": "exclusion_type\tvalue\treason\ngene_id\tENSG1\t\n",
            "padded-value.tsv": (
                "exclusion_type\tvalue\treason\ngene_name\t PADDED \tused\n"
            ),
            "padded-reason.tsv": (
                "exclusion_type\tvalue\treason\ngene_name\tPADDED\t used \n"
            ),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                path = self.write_text(name, content)
                with self.assertRaises(ValueError):
                    self.module.read_development_exclusions(path)

    def test_holdout_exclusions_parse_exact_phase2_schema_and_stable_ids(self) -> None:
        first = self.holdout_row()
        repeated = self.holdout_row(workload_id="hq01_ht02")
        second = self.holdout_row(
            workload_id="hq02_ht01",
            query_id="hq02",
            gene_id="ENSGSECOND.8",
            query_sequence_sha256="f" * 64,
        )
        path = self.write_tsv(
            "holdout.tsv",
            HOLDOUT_MANIFEST_FIELDS,
            [first, repeated, second],
        )

        gene_ids, sequence_digests = self.module.read_holdout_exclusions(path)

        self.assertEqual(gene_ids, {"ENSGHOLD", "ENSGSECOND"})
        self.assertEqual(sequence_digests, {"a" * 64, "f" * 64})

    def test_committed_holdout_manifest_satisfies_the_reader_contract(self) -> None:
        gene_ids, sequence_digests = self.module.read_holdout_exclusions(
            ROOT / "paper/bioinformatics/holdout_manifest.tsv"
        )
        self.assertEqual(len(gene_ids), 12)
        self.assertEqual(len(sequence_digests), 12)
        self.assertIn("ENSG00000276454", gene_ids)
        self.assertIn(
            "e6f49cc6e21c70f84017c331f2b1096a79befef92e2f90948ab60f8409e5b3fa",
            sequence_digests,
        )

    def test_holdout_exclusions_reject_whitespace_padding_before_normalization(self) -> None:
        for field in HOLDOUT_MANIFEST_FIELDS:
            with self.subTest(field=field):
                row = self.holdout_row()
                row[field] = f" {row[field]}"
                path = self.write_tsv(
                    f"padded-holdout-{field}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [row],
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "whitespace-padded holdout manifest field",
                ):
                    self.module.read_holdout_exclusions(path)

    def test_holdout_exclusions_requires_lowercase_query_file_sha256(self) -> None:
        invalid_digests = {
            "malformed": "not-a-sha256",
            "uppercase": "A" * 64,
        }
        for name, digest in invalid_digests.items():
            with self.subTest(name=name):
                row = {**self.holdout_row(), "query_file_sha256": digest}
                path = self.write_tsv(
                    f"invalid-query-file-sha256-{name}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [row],
                )
                with self.assertRaisesRegex(ValueError, "query_file_sha256"):
                    self.module.read_holdout_exclusions(path)

    def test_holdout_exclusions_reject_wrong_schema_and_malformed_rows(self) -> None:
        wrong_fields = (*HOLDOUT_MANIFEST_FIELDS[:-1], "result_status")
        wrong_schema = self.write_tsv(
            "wrong-holdout-schema.tsv",
            wrong_fields,
            [{field: "fixture" for field in wrong_fields}],
        )
        with self.assertRaisesRegex(ValueError, "holdout manifest.*columns"):
            self.module.read_holdout_exclusions(wrong_schema)

        header = "\t".join(HOLDOUT_MANIFEST_FIELDS) + "\n"
        valid_values = [self.holdout_row()[field] for field in HOLDOUT_MANIFEST_FIELDS]
        malformed_widths = {
            "missing-holdout-column.tsv": "\t".join(valid_values[:-1]) + "\n",
            "extra-holdout-column.tsv": "\t".join([*valid_values, "extra"]) + "\n",
        }
        for name, row_text in malformed_widths.items():
            with self.subTest(name=name):
                path = self.write_text(name, header + row_text)
                with self.assertRaisesRegex(ValueError, "holdout manifest row"):
                    self.module.read_holdout_exclusions(path)

        malformed_values = {
            "blank-holdout-gene.tsv": self.holdout_row(gene_id=""),
            "blank-holdout-query.tsv": {
                **self.holdout_row(),
                "query_id": "",
            },
            "invalid-holdout-digest.tsv": self.holdout_row(
                query_sequence_sha256="not-a-sha256"
            ),
        }
        for name, row in malformed_values.items():
            with self.subTest(name=name):
                path = self.write_tsv(name, HOLDOUT_MANIFEST_FIELDS, [row])
                with self.assertRaisesRegex(ValueError, "holdout manifest row"):
                    self.module.read_holdout_exclusions(path)

        alternate_query_values = {
            "gene_id": "ENSGHOLD.8",
            "gene_name": "HOLDOUT_ALTERNATE",
            "transcript_id": "ENSTHOLD.2",
            "query_length_nt": "701",
            "length_stratum": "801_1600",
            "query_sequence_sha256": "f" * 64,
            "query_file_sha256": "e" * 64,
            "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq01-alternate.fa",
        }
        self.assertEqual(tuple(alternate_query_values), HOLDOUT_QUERY_FIELDS)
        for field, alternate in alternate_query_values.items():
            with self.subTest(conflicting_query_field=field):
                repeated = self.holdout_row(workload_id="hq01_ht02")
                repeated.update(
                    target_id="ht02",
                    target_gene_id="ENSGTARGET2.1",
                    target_gene_name="TARGET2",
                    target_chromosome="chr2",
                    target_sequence_sha256="1" * 64,
                    target_file_sha256="2" * 64,
                    target_path="reproduce/bioinformatics/holdout_inputs/targets/ht02.fa",
                )
                repeated[field] = alternate
                conflict = self.write_tsv(
                    f"conflicting-holdout-{field}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [self.holdout_row(), repeated],
                )
                with self.assertRaisesRegex(ValueError, "conflicting holdout query"):
                    self.module.read_holdout_exclusions(conflict)

        distinct_query = {
            **self.holdout_row(
                workload_id="hq02_ht01",
                query_id="hq02",
                gene_id="ENSGSECOND.1",
                query_sequence_sha256="f" * 64,
            ),
            "gene_name": "SECOND",
            "transcript_id": "ENSTSECOND.1",
            "query_file_sha256": "e" * 64,
            "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq02.fa",
        }
        aliases = {
            "stable gene ID": {
                **distinct_query,
                "gene_id": "ENSGHOLD.8",
            },
            "query sequence digest": {
                **distinct_query,
                "query_sequence_sha256": "a" * 64,
            },
        }
        for label, alias in aliases.items():
            with self.subTest(cross_query_alias=label):
                path = self.write_tsv(
                    f"aliased-holdout-{label.replace(' ', '-')}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [self.holdout_row(), alias],
                )
                with self.assertRaisesRegex(ValueError, f"{label}.*multiple holdout queries"):
                    self.module.read_holdout_exclusions(path)

    def test_query_representative_prefers_level_basic_length_then_id(self) -> None:
        rows = [
            {
                "transcript_id": "ENST_LEVEL2_BASIC_LONG.1",
                "level": 2,
                "basic": True,
                "sequence_length": 1200,
            },
            {
                "transcript_id": "ENST_LEVEL1_NONBASIC_LONG.1",
                "level": 1,
                "basic": False,
                "sequence_length": 1300,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_SHORT.1",
                "level": 1,
                "basic": True,
                "sequence_length": 800,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_LONG_Z.1",
                "level": 1,
                "basic": True,
                "sequence_length": 1000,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_LONG.1",
                "level": 1,
                "basic": True,
                "sequence_length": 1000,
            },
        ]

        ordered = sorted(rows, key=self.module.query_representative_key)
        representative = self.module.choose_query_representative(rows)

        self.assertEqual(
            [row["transcript_id"] for row in ordered],
            [
                "ENST_LEVEL1_BASIC_LONG.1",
                "ENST_LEVEL1_BASIC_LONG_Z.1",
                "ENST_LEVEL1_BASIC_SHORT.1",
                "ENST_LEVEL1_NONBASIC_LONG.1",
                "ENST_LEVEL2_BASIC_LONG.1",
            ],
        )
        self.assertEqual(
            self.module.query_representative_key(rows[-1]),
            (1, 0, -1000, "ENST_LEVEL1_BASIC_LONG.1"),
        )
        self.assertIs(representative, rows[-1])
        with self.assertRaisesRegex(ValueError, "no query candidates"):
            self.module.choose_query_representative([])

    def test_query_representative_key_requires_real_boolean_basic(self) -> None:
        row = {
            "transcript_id": "ENST_BOOLEAN.1",
            "level": 1,
            "basic": True,
            "sequence_length": 700,
        }
        for invalid in ("False", 0, 1, None):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "basic must be bool"):
                    self.module.query_representative_key({**row, "basic": invalid})

    def test_query_selection_hash_uses_only_seed_and_stable_sequence_identity(self) -> None:
        digest = hashlib.sha256(b"ACGT").hexdigest()
        row = {
            "gene_id": "ENSGIDENTITY.17",
            "transcript_id": "ENSTIDENTITY.3",
            "sequence_sha256": digest,
            "gene_name": "BIOLOGY_NAME",
            "chromosome": "chr21",
            "runtime_seconds": 999,
            "result": "ignored",
        }
        payload = (
            "gasal2-longtarget-phase3-application-v1-20260724"
            f"|ENSGIDENTITY|ENSTIDENTITY|{digest}"
        )
        expected = hashlib.sha256(payload.encode("ascii")).hexdigest()

        self.assertEqual(self.module.query_selection_hash(row), expected)
        self.assertEqual(
            self.module.query_selection_hash(
                {
                    **row,
                    "gene_name": "DIFFERENT_NAME",
                    "chromosome": "chrX",
                    "runtime_seconds": 1,
                    "result": "different",
                }
            ),
            expected,
        )

    def test_query_selection_uses_priority_hash_and_both_exclusion_ledgers(self) -> None:
        records, transcripts = self.basic_query_fixture(55)
        representative_versions = [
            ("ENST_LEVEL2_BASIC_LONG.1", 2, True, 1200, 200),
            ("ENST_LEVEL1_NONBASIC_LONG.1", 1, False, 1300, 201),
            ("ENST_LEVEL1_BASIC_SHORT.1", 1, True, 800, 202),
            ("ENST_LEVEL1_BASIC_LONG_Z.1", 1, True, 1000, 203),
            ("ENST_LEVEL1_BASIC_LONG.1", 1, True, 1000, 204),
        ]
        for transcript_id, level, basic, length, sequence_index in representative_versions:
            self.add_query_record(
                records,
                transcripts,
                transcript_id=transcript_id,
                gene_id="ENSGPRIORITY.9",
                gene_name="PRIORITY",
                sequence=self.unique_query_sequence(sequence_index, length),
                level=level,
                basic=basic,
            )

        excluded_specs = [
            (
                "ENSTDEV.1",
                "ENSGDEV.7",
                "DEVELOPMENT_ID",
                self.unique_query_sequence(300),
            ),
            (
                "ENSTDEVNAME.1",
                "ENSGDEVNAME.1",
                "DEVELOPMENT_NAME",
                self.unique_query_sequence(301),
            ),
            ("ENSTDEVDIGEST.1", "ENSGDEVDIGEST.1", "DEV_DIGEST", "C" * 700),
            (
                "ENSTHOLD.1",
                "ENSGHOLD.3",
                "HOLDOUT_ID",
                self.unique_query_sequence(303),
            ),
            ("ENSTHOLDDIGEST.1", "ENSGHOLDDIGEST.1", "HOLD_DIGEST", "A" * 700),
        ]
        for transcript_id, gene_id, gene_name, sequence in excluded_specs:
            self.add_query_record(
                records,
                transcripts,
                transcript_id=transcript_id,
                gene_id=gene_id,
                gene_name=gene_name,
                sequence=sequence,
            )

        development = {
            "gene_id": {"ENSGDEV"},
            "gene_name": {"DEVELOPMENT_NAME"},
            "sequence_sha256": {self.module.sequence_sha256("C" * 700)},
        }
        selected, counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=development,
            holdout_gene_ids={"ENSGHOLD"},
            holdout_sequence_sha256={self.module.sequence_sha256("A" * 700)},
        )

        expected_records = {
            f"ENSTQ{index:05d}.1": self.unique_query_sequence(index)
            for index in range(1, 56)
        }
        expected_records["ENST_LEVEL1_BASIC_LONG.1"] = self.unique_query_sequence(204, 1000)
        expected_identities: list[tuple[str, str, str, str]] = []
        for transcript_id, sequence in expected_records.items():
            gene_id = (
                "ENSGPRIORITY"
                if transcript_id == "ENST_LEVEL1_BASIC_LONG.1"
                else transcript_id.replace("ENST", "ENSG").split(".", 1)[0]
            )
            stable_transcript_id = transcript_id.split(".", 1)[0]
            digest = hashlib.sha256(sequence.encode("ascii")).hexdigest()
            payload = "|".join(
                (
                    "gasal2-longtarget-phase3-application-v1-20260724",
                    gene_id,
                    stable_transcript_id,
                    digest,
                )
            )
            selection_hash = hashlib.sha256(payload.encode("ascii")).hexdigest()
            expected_identities.append((selection_hash, gene_id, transcript_id, digest))
        expected_identities.sort(key=lambda identity: identity[:3])
        expected_identities = expected_identities[:50]

        self.assertEqual(len(selected), 50)
        self.assertEqual(
            [row["query_id"] for row in selected],
            [f"aq{index:03d}" for index in range(1, 51)],
        )
        self.assertEqual(
            [
                (
                    row["selection_hash"],
                    self.module.stable_id(str(row["gene_id"])),
                    str(row["transcript_id"]),
                    row["sequence_sha256"],
                )
                for row in selected
            ],
            expected_identities,
        )
        selected_genes = {
            self.module.stable_id(str(row["gene_id"])) for row in selected
        }
        self.assertTrue(
            selected_genes.isdisjoint(
                {
                    "ENSGDEV",
                    "ENSGDEVNAME",
                    "ENSGDEVDIGEST",
                    "ENSGHOLD",
                    "ENSGHOLDDIGEST",
                }
            )
        )
        self.assertEqual(counts["input_query_record_count"], 65)
        self.assertEqual(counts["eligible_query_transcript_count"], 60)
        self.assertEqual(counts["representative_query_count"], 56)
        self.assertEqual(counts["selected_query_count"], 50)
        self.assertEqual(counts["excluded_development_gene_id_count"], 1)
        self.assertEqual(counts["excluded_development_gene_name_count"], 1)
        self.assertEqual(counts["excluded_development_sequence_sha256_count"], 1)
        self.assertEqual(counts["excluded_holdout_gene_id_count"], 1)
        self.assertEqual(counts["excluded_holdout_sequence_sha256_count"], 1)

    def test_query_selection_is_identical_under_reversed_fasta_order(self) -> None:
        records, transcripts = self.basic_query_fixture(55)
        forward_rows, forward_counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )
        reverse_rows, reverse_counts = self.module.select_queries(
            fasta_records=reversed(records),
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )

        self.assertEqual(reverse_rows, forward_rows)
        self.assertEqual(reverse_counts, forward_counts)

    def test_query_eligibility_accepts_endpoints_and_counts_biological_exclusions(self) -> None:
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        for index in range(1, 51):
            length = 500 if index == 1 else 2812 if index == 2 else 700
            self.add_query_record(
                records,
                transcripts,
                transcript_id=f"ENSTBOUND{index:03d}.1",
                gene_id=f"ENSGBound{index:03d}.1",
                sequence=self.unique_query_sequence(400 + index, length),
            )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTTOOSHORT.1",
            gene_id="ENSGTOOSHORT.1",
            sequence=self.unique_query_sequence(500, 499),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTTOOLONG.1",
            gene_id="ENSGTOOLONG.1",
            sequence=self.unique_query_sequence(501, 2813),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONCANONICAL.1",
            gene_id="ENSGNONCANONICAL.1",
            sequence="A" * 699 + "N",
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONLNC.1",
            gene_id="ENSGNONLNC.1",
            sequence=self.unique_query_sequence(503),
            gene_type="protein_coding",
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONPRIMARY.1",
            gene_id="ENSGNONPRIMARY.1",
            sequence=self.unique_query_sequence(504),
            chromosome="chrM",
        )

        selected, counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )

        selected_transcripts = {row["transcript_id"] for row in selected}
        self.assertIn("ENSTBOUND001.1", selected_transcripts)
        self.assertIn("ENSTBOUND002.1", selected_transcripts)
        self.assertEqual(counts["input_query_record_count"], 55)
        self.assertEqual(counts["eligible_query_transcript_count"], 50)
        self.assertEqual(counts["representative_query_count"], 50)
        self.assertEqual(counts["selected_query_count"], 50)
        self.assertEqual(counts["excluded_query_length_count"], 2)
        self.assertEqual(counts["excluded_noncanonical_sequence_count"], 1)
        self.assertEqual(counts["excluded_non_lncRNA_count"], 1)
        self.assertEqual(counts["excluded_non_primary_chromosome_count"], 1)

    def test_query_selection_fails_with_fewer_than_fifty_eligible_genes(self) -> None:
        records, transcripts = self.basic_query_fixture(49)
        with self.assertRaisesRegex(ValueError, "only 49 eligible.*50 required"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_duplicate_selected_sequence_digests(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        records[1] = (records[1][0], records[0][1])
        with self.assertRaisesRegex(ValueError, "selected query sequence digests.*unique"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_malformed_gencode_headers(self) -> None:
        sequence = self.unique_query_sequence(600)
        transcript = self.module.Transcript(
            transcript_id="ENSTHEADER.1",
            gene_id="ENSGHEADER.1",
            gene_name="HEADER",
            gene_type="lncRNA",
            chromosome="chr1",
            start=1,
            end=700,
            strand="+",
            level=1,
            tags=frozenset({"basic"}),
        )
        fixtures = {
            "too-few-fields": ("ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER", "header"),
            "blank-transcript": ("|ENSGHEADER.1|-|-|HEADER|HEADER|700|", "transcript ID"),
            "blank-gene": ("ENSTHEADER.1||-|-|HEADER|HEADER|700|", "gene ID"),
            "nonnumeric-length": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER|seven-hundred|",
                "declared length",
            ),
            "mismatched-length": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER|701|",
                "declared length",
            ),
        }
        for name, (header, message) in fixtures.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, message):
                    self.module.select_queries(
                        fasta_records=[(header, sequence)],
                        transcripts={"ENSTHEADER.1": transcript},
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_query_selection_requires_exact_v49_header_and_joined_gene_name(self) -> None:
        malformed_headers = {
            "seven-fields": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700",
                False,
                "GENCODE v49 FASTA header",
            ),
            "nine-fields": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700||",
                False,
                "GENCODE v49 FASTA header",
            ),
            "nonempty-terminal-field": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700|description",
                False,
                "GENCODE v49 FASTA header",
            ),
            "gene-name-drift": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|DRIFT|700|",
                True,
                "FASTA/GTF gene name mismatch",
            ),
        }
        for name, (header, include_metadata, message) in malformed_headers.items():
            with self.subTest(name=name):
                records, transcripts = self.basic_query_fixture(50)
                sequence = self.unique_query_sequence(900)
                if include_metadata:
                    transcripts["ENSTHEADER.1"] = self.module.Transcript(
                        transcript_id="ENSTHEADER.1",
                        gene_id="ENSGHEADER.1",
                        gene_name="HEADER",
                        gene_type="lncRNA",
                        chromosome="chr1",
                        start=1,
                        end=700,
                        strand="+",
                        level=1,
                        tags=frozenset({"basic"}),
                    )
                records.append((header, sequence))
                with self.assertRaisesRegex(ValueError, message):
                    self.module.select_queries(
                        fasta_records=records,
                        transcripts=transcripts,
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_query_selection_rejects_padded_or_blank_v49_identity_before_lookup(self) -> None:
        identity_fields = (
            "transcript ID",
            "gene ID",
            "Havana gene ID",
            "Havana transcript ID",
            "transcript name",
            "gene name",
        )
        mutations = {
            "leading": lambda value: f" {value}",
            "trailing": lambda value: f"{value} ",
            "blank": lambda value: "",
        }
        for index, label in enumerate(identity_fields):
            for mutation_name, mutate in mutations.items():
                with self.subTest(field=label, mutation=mutation_name):
                    records, transcripts = self.basic_query_fixture(50)
                    parts = [
                        "ENSTIDENTITY.1",
                        "ENSGIDENTITY.1",
                        "-",
                        "-",
                        "IDENTITY-201",
                        "IDENTITY",
                        "700",
                        "",
                    ]
                    parts[index] = mutate(parts[index])
                    records.append(("|".join(parts), self.unique_query_sequence(920)))
                    with self.assertRaisesRegex(
                        ValueError,
                        "invalid GENCODE v49 FASTA identity",
                    ):
                        self.module.select_queries(
                            fasta_records=records,
                            transcripts=transcripts,
                            development_exclusions=self.no_development_exclusions(),
                            holdout_gene_ids=set(),
                            holdout_sequence_sha256=set(),
                        )

    def test_query_selection_rejects_duplicate_biological_transcript_ids(self) -> None:
        sequence = self.unique_query_sequence(700)
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTDUPLICATE.1",
            gene_id="ENSGDUPLICATE.1",
            sequence=sequence,
        )
        records.append(
            (
                "ENSTDUPLICATE.1|ENSGDUPLICATE.1|-|-|ALTERNATE-202|"
                "ENSGDUPLICATE|700|",
                sequence,
            )
        )
        with self.assertRaisesRegex(ValueError, "duplicate biological transcript ID"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_duplicate_stable_transcript_ids(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTSTABLEALIAS.1",
            gene_id="ENSGSTABLEALIAS1.1",
            sequence=self.unique_query_sequence(910),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTSTABLEALIAS.2",
            gene_id="ENSGSTABLEALIAS2.1",
            sequence=self.unique_query_sequence(911),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate stable transcript ID 'ENSTSTABLEALIAS'",
        ):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_counts_missing_gtf_transcripts_and_requires_gene_join(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        sequence = self.unique_query_sequence(800)
        missing_header = "ENSTMISSING.1|ENSGMISSING.1|-|-|MISSING-201|MISSING|700|"
        records.append((missing_header, sequence))

        try:
            selected, counts = self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )
        except ValueError as error:
            self.fail(f"valid metadata-missing FASTA record was not excluded: {error}")

        self.assertEqual(len(selected), 50)
        self.assertEqual(counts["input_query_record_count"], 51)
        self.assertEqual(counts["excluded_missing_gtf_metadata_count"], 1)

        metadata = self.module.Transcript(
            transcript_id="ENSTMISSING.1",
            gene_id="ENSGGTF.1",
            gene_name="MISSING",
            gene_type="lncRNA",
            chromosome="chr1",
            start=1,
            end=700,
            strand="+",
            level=1,
            tags=frozenset({"basic"}),
        )
        with self.assertRaisesRegex(ValueError, "FASTA/GTF gene mismatch"):
            self.module.select_queries(
                fasta_records=[
                    ("ENSTMISSING.1|ENSGFASTA.1|-|-|MISSING-201|MISSING|700|", sequence)
                ],
                transcripts={"ENSTMISSING.1": metadata},
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
