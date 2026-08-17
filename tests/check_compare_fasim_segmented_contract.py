#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARE = ROOT / "scripts" / "compare_fasim_segmented_contract.py"
sys.path.insert(0, str(ROOT / "scripts"))
from fasim_tfo_archive import TFOSORTED_COLUMNS  # noqa: E402


def row(midpoint: int, index: int, score: int, stability: float, nt: int) -> dict[str, str]:
    query_start = midpoint - 30
    query_end = midpoint + 30
    return {
        "QueryStart": str(query_start),
        "QueryEnd": str(query_end),
        "StartInSeq": str(index * 100 + 1),
        "EndInSeq": str(index * 100 + nt),
        "Direction": "R",
        "Chr": "chrSynthetic",
        "StartInGenome": str(index * 1000 + 1),
        "EndInGenome": str(index * 1000 + nt),
        "MeanStability": str(stability),
        "MeanIdentity(%)": "75",
        "Strand": ["ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus"][index % 4],
        "Rule": "0",
        "Score": str(score),
        "Nt(bp)": str(nt),
        "Class": "0",
        "MidPoint": str(midpoint),
        "Center": str(midpoint),
        "TFO sequence": f"TFO{index:03d}",
        "TTS sequence": f"TTS{index:03d}",
    }


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(TFOSORTED_COLUMNS),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class SegmentedContractComparatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase2-contract-")
        self.work = Path(self.tempdir.name)
        self.rows = [
            row(100, 1, 300, 1.0, 70),
            row(105, 2, 200, 4.0, 80),
            row(110, 3, 100, 2.0, 120),
            row(400, 4, 250, 3.0, 90),
            row(700, 5, 240, 2.5, 85),
            row(1000, 6, 230, 2.4, 84),
            row(1300, 7, 220, 2.3, 83),
            row(1600, 8, 210, 2.2, 82),
            row(1900, 9, 210, 2.2, 82),
        ]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def compare(
        self, baseline: Path, candidate: Path, details: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [
                sys.executable,
                str(COMPARE),
                "--baseline",
                str(baseline),
                "--candidate",
                str(candidate),
                "--k",
                "5",
            ]
        if details is not None:
            command.extend(["--details", str(details)])
        return subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_same_row_set_is_order_independent_for_all_clustered_rankings(self) -> None:
        baseline = self.work / "baseline.tsv"
        candidate = self.work / "candidate.tsv"
        write_rows(baseline, self.rows)
        write_rows(candidate, list(reversed(self.rows)))
        result = self.compare(baseline, candidate)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = parse(result.stdout)
        self.assertEqual(values["full_missing_rows"], "0")
        self.assertEqual(values["full_extra_rows"], "0")
        self.assertEqual(values["clustered_score_top5_equal"], "1")
        self.assertEqual(values["clustered_stability_top5_equal"], "1")
        self.assertEqual(values["clustered_nt_top5_equal"], "1")
        self.assertEqual(values["all_three_top5_equal"], "1")
        self.assertEqual(values["boundary_ties_equal"], "1")
        self.assertGreater(int(values["representative_conflict_clusters"]), 0)

    def test_details_capture_raw_and_clustered_representatives_for_each_side(self) -> None:
        baseline = self.work / "baseline.tsv"
        candidate = self.work / "candidate.tsv"
        details = self.work / "details.tsv"
        write_rows(baseline, self.rows)
        write_rows(candidate, list(reversed(self.rows)))

        result = self.compare(baseline, candidate, details)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        with details.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows = list(reader)
        self.assertEqual(
            reader.fieldnames,
            ["side", "kind", "mode", "rank", "cluster_id", *TFOSORTED_COLUMNS],
        )
        self.assertEqual({row["side"] for row in rows}, {"baseline", "candidate"})
        self.assertEqual({row["kind"] for row in rows}, {"raw", "clustered"})
        self.assertEqual({row["mode"] for row in rows}, {"score", "stability", "nt"})
        self.assertTrue(all(row["cluster_id"] == "NA" for row in rows if row["kind"] == "raw"))
        self.assertTrue(all(row["cluster_id"] != "NA" for row in rows if row["kind"] == "clustered"))

    def test_missing_boundary_tie_is_reported(self) -> None:
        baseline = self.work / "baseline.tsv"
        candidate = self.work / "candidate.tsv"
        write_rows(baseline, self.rows)
        write_rows(candidate, self.rows[:-1])
        result = self.compare(baseline, candidate)
        self.assertNotEqual(result.returncode, 0)
        values = parse(result.stdout)
        self.assertEqual(values["full_missing_rows"], "1")
        self.assertEqual(values["boundary_ties_equal"], "0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
