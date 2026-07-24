#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reproduce/bioinformatics/build_holdout_panel.py"


def sequence_digest(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


class HoldoutPanelBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bioinformatics-holdout-builder-")
        self.work = Path(self.temp.name)
        self.lncrna = self.work / "lncrna.fa.gz"
        self.annotation = self.work / "annotation.gtf.gz"
        self.exclusions = self.work / "development_exclusions.tsv"
        self.selection = self.work / "selection.json"
        self.chromosomes = self.work / "chromosomes"
        self.output = self.work / "panel"
        self.manifest = self.work / "holdout_manifest.tsv"
        self.manifest_sha = self.work / "holdout_manifest.sha256"
        self.chromosomes.mkdir()
        self.records = self.write_sources()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_sources(self) -> dict[str, str]:
        records: dict[str, str] = {}
        fasta_lines: list[str] = []
        gtf_lines = [
            "##description: synthetic GENCODE fixture (GRCh38), version 49 (Ensembl 115)",
        ]
        lengths = [410, 520, 630, 740, 900, 1050, 1250, 1450, 1700, 1950, 2250, 2600]
        for index, length in enumerate(lengths, 1):
            gene = f"ENSGH{index:05d}.1"
            transcript = f"ENSTH{index:05d}.1"
            name = f"HOLDOUT{index:02d}"
            sequence = ("ACGT" * ((length + 3) // 4))[:length]
            if index % 2 == 0:
                sequence = ("TGCA" * ((length + 3) // 4))[:length]
            records[transcript] = sequence
            fasta_lines.extend(
                [
                    f">{transcript}|{gene}|-|{name}-201|{name}|{name}|{length}|",
                    sequence,
                ]
            )
            gtf_lines.append(
                f'chr{(index % 8) + 1}\tTEST\ttranscript\t100\t200\t.\t+\t.\t'
                f'gene_id "{gene}"; transcript_id "{transcript}"; gene_type "lncRNA"; '
                f'gene_name "{name}"; transcript_type "lncRNA"; level 1; tag "basic";'
            )

        excluded_sequence = "ACGT" * 100
        records["ENSTEXCLUDED.1"] = excluded_sequence
        fasta_lines.extend(
            [
                ">ENSTEXCLUDED.1|ENSGEXCLUDED.1|-|EXCLUDED-201|EXCLUDED|EXCLUDED|400|",
                excluded_sequence,
            ]
        )
        gtf_lines.append(
            'chr3\tTEST\ttranscript\t100\t200\t.\t+\t.\tgene_id "ENSGEXCLUDED.1"; '
            'transcript_id "ENSTEXCLUDED.1"; gene_type "lncRNA"; gene_name "EXCLUDED"; '
            'transcript_type "lncRNA"; level 1; tag "basic";'
        )

        target_rows = [
            ("chr1", "ENSGTARGET1.1", "TARGET1", 5000, 7000, "+"),
            ("chr2", "ENSGTARGET2.1", "TARGET2", 8000, 10000, "-"),
            ("chr3", "ENSGTARGET3.1", "TARGET3", 12000, 14000, "+"),
            ("chr11", "ENSGDEVCHR.1", "DEVCHR", 15000, 17000, "+"),
        ]
        for chrom, gene, name, start, end, strand in target_rows:
            gtf_lines.append(
                f'{chrom}\tTEST\tgene\t{start}\t{end}\t.\t{strand}\t.\tgene_id "{gene}"; '
                f'gene_type "protein_coding"; gene_name "{name}"; level 1;'
            )

        with gzip.open(self.lncrna, "wt", encoding="utf-8", newline="") as handle:
            handle.write("\n".join(fasta_lines) + "\n")
        with gzip.open(self.annotation, "wt", encoding="utf-8", newline="") as handle:
            handle.write("\n".join(gtf_lines) + "\n")
        self.exclusions.write_text(
            "exclusion_type\tvalue\treason\n"
            "gene_id\tENSGEXCLUDED\tdevelopment_gene\n"
            "gene_name\tH19\tdevelopment_gene\n"
            f"sequence_sha256\t{sequence_digest(excluded_sequence)}\tdevelopment_query\n",
            encoding="utf-8",
        )
        chromosome_sequence = "ACGT" * 6000
        for chrom in ("chr1", "chr2", "chr3"):
            (self.chromosomes / f"{chrom}.fa").write_text(
                f">{chrom}\n{chromosome_sequence}\n", encoding="utf-8"
            )
        return records

    def run_select(self, *, annotation: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "select",
                "--lncrna-fasta",
                str(self.lncrna),
                "--annotation-gtf",
                str(annotation or self.annotation),
                "--development-exclusions",
                str(self.exclusions),
                "--output",
                str(self.selection),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def run_materialize(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "materialize",
                "--selection",
                str(self.selection),
                "--lncrna-fasta",
                str(self.lncrna),
                "--chromosome-dir",
                str(self.chromosomes),
                "--output-root",
                str(self.output),
                "--manifest",
                str(self.manifest),
                "--manifest-sha256",
                str(self.manifest_sha),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def published_snapshot(self) -> tuple[dict[str, bytes], bytes, bytes]:
        files = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        return files, self.manifest.read_bytes(), self.manifest_sha.read_bytes()

    def test_selects_stratified_queries_and_distinct_nondevelopment_targets(self) -> None:
        result = self.run_select()
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(self.selection.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["assembly"], "GRCh38")
        self.assertEqual(payload["annotation_release"], "GENCODE v49")
        self.assertEqual(len(payload["queries"]), 12)
        counts: dict[str, int] = {}
        for row in payload["queries"]:
            counts[row["length_stratum"]] = counts.get(row["length_stratum"], 0) + 1
            self.assertNotEqual(row["gene_id"].split(".", 1)[0], "ENSGEXCLUDED")
            self.assertNotEqual(row["sequence_sha256"], sequence_digest("ACGT" * 100))
        self.assertEqual(counts, {"le_800": 4, "801_1600": 4, "1601_2812": 4})
        self.assertEqual(len(payload["targets"]), 2)
        target_chromosomes = {row["chromosome"] for row in payload["targets"]}
        self.assertEqual(len(target_chromosomes), 2)
        self.assertTrue(target_chromosomes.isdisjoint({"chr11", "chr21", "chr22"}))
        self.assertTrue(all(row["region_length_bp"] == 2501 for row in payload["targets"]))

    def test_materializes_24_frozen_workloads_and_representative_repeats(self) -> None:
        selected = self.run_select()
        self.assertEqual(selected.returncode, 0, selected.stderr)
        result = self.run_materialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.manifest.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({row["gene_id"] for row in rows}), 12)
        self.assertEqual(len({row["target_id"] for row in rows}), 2)
        self.assertEqual(sum(row["repeat_count"] == "3" for row in rows), 6)
        self.assertEqual(sum(row["repeat_count"] == "1" for row in rows), 18)
        self.assertTrue(all(row["query_sequence_sha256"] not in {sequence_digest("ACGT" * 100)} for row in rows))
        for row in rows:
            query = ROOT / row["query_path"] if not Path(row["query_path"]).is_absolute() else Path(row["query_path"])
            target = ROOT / row["target_path"] if not Path(row["target_path"]).is_absolute() else Path(row["target_path"])
            self.assertTrue(query.is_file())
            self.assertTrue(target.is_file())
        digest, relative = self.manifest_sha.read_text(encoding="utf-8").strip().split("  ", 1)
        self.assertEqual(relative, self.manifest.name)
        self.assertEqual(digest, hashlib.sha256(self.manifest.read_bytes()).hexdigest())

        first_bytes = self.manifest.read_bytes()
        rerun = self.run_materialize()
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(self.manifest.read_bytes(), first_bytes)

        selected_filenames = {
            Path(row["query_path"]).name for row in rows
        } | {
            Path(row["target_path"]).name for row in rows
        }
        actual_filenames = {
            path.name for path in self.output.rglob("*") if path.is_file()
        }
        self.assertEqual(actual_filenames, selected_filenames)

    def test_late_target_failure_preserves_preexisting_freeze_byte_for_byte(self) -> None:
        selected = self.run_select()
        self.assertEqual(selected.returncode, 0, selected.stderr)
        payload = json.loads(self.selection.read_text(encoding="utf-8"))
        payload["targets"][-1]["region_end"] = 999999
        self.selection.write_text(json.dumps(payload), encoding="utf-8")

        self.output.mkdir()
        (self.output / "sentinel.freeze").write_bytes(b"preexisting artifact tree\n")
        self.manifest.write_bytes(b"preexisting manifest\n")
        self.manifest_sha.write_bytes(b"preexisting checksum\n")
        before = self.published_snapshot()

        result = self.run_materialize()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside", result.stderr)
        self.assertEqual(self.published_snapshot(), before)
        self.assertEqual(list(self.work.glob(f".{self.output.name}.staging.*")), [])

    def test_rejects_stale_existing_artifact_tree_without_changing_freeze(self) -> None:
        selected = self.run_select()
        self.assertEqual(selected.returncode, 0, selected.stderr)
        materialized = self.run_materialize()
        self.assertEqual(materialized.returncode, 0, materialized.stderr)
        stale = self.output / "queries/stale.fa"
        stale.write_bytes(b">stale\nACGT\n")
        before = self.published_snapshot()

        result = self.run_materialize()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("drift", result.stderr)
        self.assertEqual(self.published_snapshot(), before)
        self.assertEqual(list(self.work.glob(f".{self.output.name}.staging.*")), [])

    def test_fails_closed_when_a_length_stratum_is_too_small(self) -> None:
        insufficient = self.work / "insufficient.gtf.gz"
        with gzip.open(self.annotation, "rt", encoding="utf-8") as source:
            lines = [line for line in source if "ENSTH00012" not in line]
        with gzip.open(insufficient, "wt", encoding="utf-8") as handle:
            handle.writelines(lines)
        result = self.run_select(annotation=insufficient)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("1601_2812", result.stderr)
        self.assertFalse(self.selection.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
