#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts" / "merge_fasim_segmented_tfosorted.py"
RESTORE = ROOT / "scripts" / "restore_fasim_tfosorted_column_archive_probe.py"

TFOSORTED_COLUMNS = [
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint requires a non-negative value")
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def zigzag(value: int) -> int:
    return (value << 1) if value >= 0 else ((-value << 1) - 1)


def encode_delta(values: list[int]) -> bytes:
    previous = 0
    payload = bytearray()
    for value in values:
        payload.extend(put_varint(zigzag(value - previous)))
        previous = value
    return bytes(payload)


def encode_varints(values: list[int]) -> bytes:
    return b"".join(put_varint(value) for value in values)


def encode_bytes(values: list[bytes]) -> bytes:
    return b"".join(put_varint(len(value)) + value for value in values)


def encode_dictionary(values: list[bytes]) -> bytes:
    dictionary: list[bytes] = []
    indices: list[int] = []
    for value in values:
        if value not in dictionary:
            dictionary.append(value)
        indices.append(dictionary.index(value))
    return (
        put_varint(len(dictionary))
        + encode_bytes(dictionary)
        + encode_varints(indices)
    )


def write_archive(path: Path, rows: list[dict[str, int | bytes]], version: int = 2) -> None:
    payloads = [
        encode_delta([int(row["q_start"]) for row in rows]),
        encode_delta([int(row["seq_start"]) for row in rows]),
        encode_delta([int(row["score"]) for row in rows]),
        encode_delta([int(row["align_len"]) for row in rows]),
        encode_varints([int(row["q_len"]) for row in rows]),
        encode_varints([int(row["target_len"]) for row in rows]),
        encode_varints([int(row["rule"]) for row in rows]),
        encode_varints([int(row["nt"]) for row in rows]),
        bytes(int(row["flags"]) for row in rows),
        encode_dictionary([bytes(row["stability"]) for row in rows]),
        encode_dictionary([bytes(row["identity"]) for row in rows]),
        encode_bytes([bytes(row["tfo_mask"]) for row in rows]),
        encode_bytes([bytes(row["tts_mask"]) for row in rows]),
    ]
    block = struct.pack("<II", len(rows), len(payloads))
    block += b"".join(struct.pack("<I", len(payload)) for payload in payloads)
    block += b"".join(payloads)
    with path.open("wb") as handle:
        handle.write(b"FATFOC1\0")
        handle.write(struct.pack("<II", version, 65536))
        if rows:
            handle.write(struct.pack("<I", len(block)))
            handle.write(block)
        handle.write(struct.pack("<I", 0))


def write_tfosorted(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TFOSORTED_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def base_row(**overrides: str) -> dict[str, str]:
    row = {
        "QueryStart": "1",
        "QueryEnd": "4",
        "StartInSeq": "3",
        "EndInSeq": "6",
        "Direction": "R",
        "Chr": "chr11",
        "StartInGenome": "1002",
        "EndInGenome": "1005",
        "MeanStability": "1.25",
        "MeanIdentity(%)": "75",
        "Strand": "ParaPlus",
        "Rule": "0",
        "Score": "42",
        "Nt(bp)": "4",
        "Class": "0",
        "MidPoint": "2",
        "Center": "2",
        "TFO sequence": "ACGT",
        "TTS sequence": "GTAC",
    }
    row.update(overrides)
    return row


def parse_metrics(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class SegmentedMergeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase1-")
        self.work = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_merge(
        self,
        manifest: Path,
        output: Path,
        *extra: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(MERGE),
                "--segments",
                str(manifest),
                "--output",
                str(output),
                *extra,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_typed_text_manifest_matches_legacy_manifest_byte_for_byte(self) -> None:
        rows = [base_row(), base_row(QueryStart="5", QueryEnd="8", MidPoint="6", Center="6")]
        source = self.work / "segment-TFOsorted"
        write_tfosorted(source, rows)

        legacy = self.work / "legacy.tsv"
        write_manifest(
            legacy,
            ["segment_id", "global_start", "global_end", "tfosorted"],
            [{"segment_id": "0", "global_start": "10", "global_end": "30", "tfosorted": str(source)}],
        )
        typed = self.work / "typed.tsv"
        write_manifest(
            typed,
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"],
            [{
                "segment_id": "0",
                "global_start": "10",
                "global_end": "30",
                "artifact_kind": "tfosorted",
                "artifact_path": str(source),
            }],
        )

        legacy_out = self.work / "legacy-out.tsv"
        typed_out = self.work / "typed-out.tsv"
        self.run_merge(legacy, legacy_out)
        result = self.run_merge(typed, typed_out)
        self.assertEqual(legacy_out.read_bytes(), typed_out.read_bytes())
        self.assertEqual(parse_metrics(result.stdout)["artifact_kind_counts"], "tfosorted:1")

    def test_sqlite_dedup_preserves_first_seen_order_and_filter_boundaries(self) -> None:
        first = self.work / "first.tsv"
        second = self.work / "second.tsv"
        duplicate_global = base_row(
            QueryStart="11", QueryEnd="14", MidPoint="12", Center="12", Score="100"
        )
        lower_filtered = base_row(
            QueryStart="10", QueryEnd="13", MidPoint="11", Center="11", Score="90"
        )
        upper_filtered = base_row(
            QueryStart="12", QueryEnd="15", MidPoint="13", Center="13", Score="80"
        )
        write_tfosorted(first, [duplicate_global, lower_filtered, upper_filtered])
        write_tfosorted(
            second,
            [base_row(QueryStart="1", QueryEnd="4", MidPoint="2", Center="2", Score="100")],
        )
        manifest = self.work / "segments.tsv"
        write_manifest(
            manifest,
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"],
            [
                {
                    "segment_id": "first",
                    "global_start": "0",
                    "global_end": "100",
                    "artifact_kind": "tfosorted",
                    "artifact_path": str(first),
                },
                {
                    "segment_id": "second",
                    "global_start": "10",
                    "global_end": "110",
                    "artifact_kind": "tfosorted",
                    "artifact_path": str(second),
                },
            ],
        )
        output = self.work / "merged.tsv"
        db = self.work / "seen.sqlite"
        result = self.run_merge(
            manifest,
            output,
            "--query-min",
            "11",
            "--query-max",
            "14",
            "--dedup-backend",
            "sqlite",
            "--dedup-db",
            str(db),
            "--keep-dedup-db",
        )
        metrics = parse_metrics(result.stdout)
        self.assertEqual(metrics["input_rows"], "4")
        self.assertEqual(metrics["output_rows"], "1")
        self.assertEqual(metrics["duplicate_rows"], "1")
        self.assertEqual(metrics["filtered_rows"], "2")
        self.assertEqual(metrics["dedup_backend"], "sqlite")
        self.assertGreater(int(metrics["dedup_db_bytes"]), 0)
        self.assertTrue(db.is_file())
        with output.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(rows, [duplicate_global])

    def test_sqlite_db_is_removed_after_success_unless_kept(self) -> None:
        source = self.work / "segment.tsv"
        write_tfosorted(source, [base_row()])
        manifest = self.work / "segments.tsv"
        write_manifest(
            manifest,
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"],
            [{
                "segment_id": "0",
                "global_start": "0",
                "global_end": "10",
                "artifact_kind": "tfosorted",
                "artifact_path": str(source),
            }],
        )
        db = self.work / "transient.sqlite"
        result = self.run_merge(
            manifest,
            self.work / "out.tsv",
            "--dedup-backend",
            "sqlite",
            "--dedup-db",
            str(db),
        )
        self.assertFalse(db.exists())
        self.assertEqual(parse_metrics(result.stdout)["dedup_db_retained"], "0")

    def make_archive_fixture(self) -> tuple[Path, Path, Path, Path]:
        query = self.work / "query.fa"
        target = self.work / "target.fa"
        query.write_text(">segment\nAACCGGTTAACCGGTTAACCGGTTAACCGGTT\n", encoding="utf-8")
        target.write_text(">hg19|chr11|1000-1063\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n", encoding="utf-8")
        archive = self.work / "segment.archive-first.tfoa"
        write_archive(
            archive,
            [{
                "q_start": 2,
                "seq_start": 3,
                "score": 42,
                "align_len": 4,
                "q_len": 4,
                "target_len": 4,
                "rule": 0,
                "nt": 4,
                "flags": 0,
                "stability": b"1.25",
                "identity": b"75",
                "tfo_mask": b"\0",
                "tts_mask": b"\0",
            }],
        )
        expected = self.work / "expected.tsv"
        expected_row = base_row(
            QueryStart="12",
            QueryEnd="15",
            MidPoint="13",
            Center="13",
        )
        expected_row["TFO sequence"] = "ACCG"
        expected_row["TTS sequence"] = "GTAC"
        write_tfosorted(expected, [expected_row])
        return query, target, archive, expected

    def archive_manifest(
        self,
        path: Path,
        query: Path,
        target: Path,
        archive: Path,
        query_digest: str | None = None,
    ) -> None:
        columns = [
            "segment_id",
            "global_start",
            "global_end",
            "artifact_kind",
            "artifact_path",
            "query_fasta",
            "query_fasta_sha256",
            "target_fasta",
            "target_fasta_sha256",
        ]
        write_manifest(
            path,
            columns,
            [{
                "segment_id": "0",
                "global_start": "10",
                "global_end": "42",
                "artifact_kind": "archive_first_tfoa",
                "artifact_path": str(archive),
                "query_fasta": str(query),
                "query_fasta_sha256": query_digest or sha256(query),
                "target_fasta": str(target),
                "target_fasta_sha256": sha256(target),
            }],
        )

    def test_archive_merge_matches_text_and_restores_compound_target_metadata(self) -> None:
        query, target, archive, expected = self.make_archive_fixture()
        manifest = self.work / "archive-manifest.tsv"
        self.archive_manifest(manifest, query, target, archive)
        output = self.work / "archive-merged.tsv"
        result = self.run_merge(
            manifest,
            output,
            "--dedup-backend",
            "sqlite",
            "--dedup-db",
            str(self.work / "archive.sqlite"),
        )
        self.assertEqual(output.read_bytes(), expected.read_bytes())
        metrics = parse_metrics(result.stdout)
        self.assertEqual(metrics["artifact_kind_counts"], "archive_first_tfoa:1")
        self.assertEqual(metrics["archive_input_bytes"], str(archive.stat().st_size))
        self.assertEqual(metrics["text_input_bytes"], "0")

        restored = self.work / "restored.tsv"
        subprocess.run(
            [
                sys.executable,
                str(RESTORE),
                "--archive",
                str(archive),
                "--output",
                str(restored),
                "--query-fasta",
                str(query),
                "--target-fasta",
                str(target),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        local_expected_rows = []
        with expected.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                row["QueryStart"] = "2"
                row["QueryEnd"] = "5"
                row["MidPoint"] = "3"
                row["Center"] = "3"
                local_expected_rows.append(row)
        local_expected = self.work / "local-expected.tsv"
        write_tfosorted(local_expected, local_expected_rows)
        self.assertEqual(restored.read_bytes(), local_expected.read_bytes())

    def test_archive_version_and_reference_digest_fail_closed(self) -> None:
        query, target, archive, _expected = self.make_archive_fixture()
        bad_version = self.work / "bad-version.tfoa"
        write_archive(bad_version, [], version=99)
        bad_manifest = self.work / "bad-version.tsv"
        self.archive_manifest(bad_manifest, query, target, bad_version)
        result = self.run_merge(bad_manifest, self.work / "bad.tsv", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", result.stderr.lower())

        bad_columns = self.work / "bad-columns.tfoa"
        bad_columns.write_bytes(archive.read_bytes())
        payload = bytearray(bad_columns.read_bytes())
        struct.pack_into("<I", payload, 24, 12)
        bad_columns.write_bytes(payload)
        columns_manifest = self.work / "bad-columns.tsv"
        self.archive_manifest(columns_manifest, query, target, bad_columns)
        result = self.run_merge(
            columns_manifest,
            self.work / "bad-columns-out.tsv",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("column payload count", result.stderr.lower())

        oversized_block = self.work / "oversized-block.tfoa"
        oversized_block.write_bytes(
            b"FATFOC1\0"
            + struct.pack("<II", 2, 65536)
            + struct.pack("<I", 512 * 1024 * 1024)
        )
        oversized_manifest = self.work / "oversized-block.tsv"
        self.archive_manifest(oversized_manifest, query, target, oversized_block)
        result = self.run_merge(
            oversized_manifest,
            self.work / "oversized-block-out.tsv",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("block size", result.stderr.lower())

        oversized_rows = self.work / "oversized-rows.tfoa"
        oversized_rows.write_bytes(
            b"FATFOC1\0" + struct.pack("<II", 2, 2_000_000) + struct.pack("<I", 0)
        )
        oversized_rows_manifest = self.work / "oversized-rows.tsv"
        self.archive_manifest(oversized_rows_manifest, query, target, oversized_rows)
        result = self.run_merge(
            oversized_rows_manifest,
            self.work / "oversized-rows-out.tsv",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("block rows", result.stderr.lower())

        digest_manifest = self.work / "bad-digest.tsv"
        self.archive_manifest(digest_manifest, query, target, archive, query_digest="0" * 64)
        result = self.run_merge(digest_manifest, self.work / "bad-digest-out.tsv", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("digest", result.stderr.lower())

    def test_missing_non_integer_and_out_of_range_coordinates_fail_closed(self) -> None:
        for label, row, expected_error in [
            ("missing", base_row(Center=""), "Center"),
            ("non-integer", base_row(QueryStart="one"), "QueryStart"),
            ("out-of-range", base_row(QueryEnd="11"), "range"),
        ]:
            with self.subTest(label=label):
                source = self.work / f"{label}.tsv"
                write_tfosorted(source, [row])
                manifest = self.work / f"{label}-manifest.tsv"
                write_manifest(
                    manifest,
                    ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"],
                    [{
                        "segment_id": "0",
                        "global_start": "0",
                        "global_end": "10",
                        "artifact_kind": "tfosorted",
                        "artifact_path": str(source),
                    }],
                )
                result = self.run_merge(manifest, self.work / f"{label}-out.tsv", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error.lower(), result.stderr.lower())

    def test_failure_preserves_partial_output_and_sqlite_diagnostic_state(self) -> None:
        source = self.work / "partial-source.tsv"
        write_tfosorted(source, [base_row(), base_row(Center="")])
        manifest = self.work / "partial-manifest.tsv"
        write_manifest(
            manifest,
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"],
            [{
                "segment_id": "0",
                "global_start": "0",
                "global_end": "10",
                "artifact_kind": "tfosorted",
                "artifact_path": str(source),
            }],
        )
        output = self.work / "failed-output.tsv"
        database = self.work / "failed-dedup.sqlite"
        result = self.run_merge(
            manifest,
            output,
            "--dedup-backend",
            "sqlite",
            "--dedup-db",
            str(database),
            "--sqlite-commit-rows",
            "1",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertTrue(output.with_name(f"{output.name}.partial").is_file())
        self.assertTrue(database.is_file())
        self.assertGreater(database.stat().st_size, 0)

    def test_source_does_not_accumulate_complete_output_list(self) -> None:
        source = MERGE.read_text(encoding="utf-8")
        self.assertNotIn("output_rows: list[", source)
        self.assertNotIn("output_rows.append(", source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
