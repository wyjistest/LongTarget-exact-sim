#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fasim_segment_ownership import (  # noqa: E402
    SegmentInterval,
    choose_owner,
    derive_descriptors,
    segment_starts,
    write_descriptor_manifest,
)
from fasim_tfo_archive import TFOSORTED_COLUMNS  # noqa: E402


SHADOW = SCRIPTS / "fasim_segment_ownership.py"
OFFSET_COLUMNS = ("QueryStart", "QueryEnd", "MidPoint", "Center")


def base_row(query_start: int, query_end: int, index: int, **overrides: str) -> dict[str, str]:
    midpoint = (query_start + query_end) // 2
    row = {
        "QueryStart": str(query_start),
        "QueryEnd": str(query_end),
        "StartInSeq": str(index * 10 + 1),
        "EndInSeq": str(index * 10 + 60),
        "Direction": "R",
        "Chr": "chrSynthetic",
        "StartInGenome": str(index * 10 + 1001),
        "EndInGenome": str(index * 10 + 1060),
        "MeanStability": "2.0",
        "MeanIdentity(%)": "75",
        "Strand": "ParaPlus",
        "Rule": "0",
        "Score": "100",
        "Nt(bp)": "60",
        "Class": "0",
        "MidPoint": str(midpoint),
        "Center": str(midpoint),
        "TFO sequence": f"TFO{index:03d}",
        "TTS sequence": f"TTS{index:03d}",
    }
    row.update(overrides)
    return row


def write_tfosorted(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(TFOSORTED_COLUMNS),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_metrics(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


class SegmentDescriptorTest(unittest.TestCase):
    def test_descriptor_geometry_for_shifted_2048_512_grid(self) -> None:
        intervals = [
            SegmentInterval("0", 0, 2048),
            SegmentInterval("1", 256, 2304),
            SegmentInterval("2", 764, 2812),
        ]
        descriptors = derive_descriptors(intervals, grid_shift=256, query_length=2812)
        self.assertEqual(
            [
                (
                    descriptor.segment_id,
                    descriptor.core_start,
                    descriptor.core_end,
                    descriptor.left_halo,
                    descriptor.right_halo,
                    descriptor.is_first_segment,
                    descriptor.is_last_segment,
                )
                for descriptor in descriptors
            ],
            [
                ("0", 0, 1152, 0, 896, True, False),
                ("1", 1152, 1534, 896, 770, False, False),
                ("2", 1534, 2812, 770, 0, False, True),
            ],
        )

    def test_owner_is_unique_order_independent_and_covers_edges(self) -> None:
        starts = segment_starts(2812, 1024, 256, 64)
        intervals = [
            SegmentInterval(str(index), start, min(start + 1024, 2812))
            for index, start in enumerate(starts)
        ]
        descriptors = derive_descriptors(intervals, grid_shift=64, query_length=2812)
        probes = [
            (1, 80),
            (descriptors[0].core_end, descriptors[0].core_end + 1),
            (descriptors[1].core_start, descriptors[1].core_end),
            (2730, 2812),
        ]
        for query_start, query_end in probes:
            with self.subTest(query_start=query_start, query_end=query_end):
                forward = choose_owner(query_start, query_end, descriptors)
                reverse = choose_owner(query_start, query_end, list(reversed(descriptors)))
                self.assertIsNotNone(forward.owner)
                self.assertEqual(forward.owner, reverse.owner)
                self.assertGreaterEqual(forward.eligible_count, 1)
        self.assertTrue(choose_owner(1, 80, descriptors).owner.is_first_segment)
        self.assertTrue(choose_owner(2730, 2812, descriptors).owner.is_last_segment)

    def test_span_larger_than_every_segment_has_no_owner(self) -> None:
        descriptors = derive_descriptors(
            [SegmentInterval("0", 0, 1024), SegmentInterval("1", 768, 1792)],
            grid_shift=0,
            query_length=2000,
        )
        decision = choose_owner(200, 1500, descriptors)
        self.assertIsNone(decision.owner)
        self.assertEqual(decision.eligible_count, 0)


class OwnershipShadowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase2-ownership-")
        self.work = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_exhaustive_fixture_has_one_owner_and_exact_authority_output(self) -> None:
        query_length = 2812
        starts = segment_starts(query_length, 1024, 256, 0)
        intervals = [
            SegmentInterval(str(index), start, min(start + 1024, query_length))
            for index, start in enumerate(starts)
        ]
        descriptors = derive_descriptors(intervals, grid_shift=0, query_length=query_length)
        descriptor_path = self.work / "descriptors.tsv"
        write_descriptor_manifest(descriptor_path, descriptors)

        boundary = descriptors[0].core_end
        rows = [
            base_row(1, 80, 1),
            base_row(100, 180, 2, Strand="ParaMinus"),
            base_row(boundary - 20, boundary + 20, 3, Strand="AntiPlus"),
            base_row(boundary, boundary + 60, 4, Strand="AntiMinus"),
            base_row(1, 900, 5, **{"Nt(bp)": "900"}),
            base_row(2730, 2812, 6),
            base_row(1600, 1660, 7, Score="200", **{"MeanStability": "3.0"}),
            base_row(1700, 1760, 8, Score="200", **{"MeanStability": "3.0"}),
            base_row(1800, 1860, 9, Score="200", **{"MeanStability": "3.0"}),
        ]
        authority = self.work / "authority.tsv"
        write_tfosorted(authority, rows)

        manifest = self.work / "segments.tsv"
        manifest_rows: list[dict[str, str]] = []
        for descriptor in descriptors:
            local_rows: list[dict[str, str]] = []
            for row in rows:
                query_start = int(row["QueryStart"])
                query_end = int(row["QueryEnd"])
                if descriptor.segment_start <= query_start - 1 and query_end <= descriptor.segment_end:
                    local = dict(row)
                    for column in OFFSET_COLUMNS:
                        local[column] = str(int(local[column]) - descriptor.segment_start)
                    local_rows.append(local)
            output = self.work / f"segment-{descriptor.segment_id}.tsv"
            write_tfosorted(output, local_rows)
            manifest_rows.append(
                {
                    "segment_id": descriptor.segment_id,
                    "global_start": str(descriptor.segment_start),
                    "global_end": str(descriptor.segment_end),
                    "tfosorted": str(output),
                }
            )
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["segment_id", "global_start", "global_end", "tfosorted"],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(manifest_rows)

        summary = self.work / "summary.txt"
        ownership_output = self.work / "ownership.tsv"
        subprocess.run(
            [
                sys.executable,
                str(SHADOW),
                "shadow",
                "--segments",
                str(manifest),
                "--descriptors",
                str(descriptor_path),
                "--authority",
                str(authority),
                "--output",
                str(ownership_output),
                "--db",
                str(self.work / "shadow.sqlite"),
                "--summary",
                str(summary),
            ],
            cwd=ROOT,
            check=True,
        )
        values = parse_metrics(summary)
        self.assertEqual(values["rows_no_owner"], "0")
        self.assertEqual(values["rows_owner_mismatch_vs_authority"], "0")
        self.assertEqual(values["authority_missing_rows"], "0")
        self.assertEqual(values["authority_extra_rows"], "0")
        self.assertEqual(values["owner_is_unique"], "1")
        self.assertGreater(int(values["rows_multi_owner_before_tiebreak"]), 0)
        self.assertGreater(int(values["rows_non_owner_duplicate"]), 0)
        self.assertEqual(values["potential_exact_tasks_removed"], "unavailable")
        self.assertEqual(values["potential_tracebacks_removed"], "unavailable")
        self.assertEqual(values["runtime_work_dropped"], "0")
        self.assertEqual(authority.read_bytes(), ownership_output.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
