#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "compare_promoter_pair",
    SCRIPTS / "compare_exact_long_query_hybrid_promoter_pair_v1.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ComparePromoterPairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="compare-promoter-pair-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_files_byte_equal_streams_content(self) -> None:
        left = self.root / "left"
        right = self.root / "right"
        left.write_bytes(b"a" * (9 * 1024 * 1024))
        right.write_bytes(left.read_bytes())
        self.assertTrue(MODULE.files_byte_equal(left, right))
        with right.open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b"b")
        self.assertFalse(MODULE.files_byte_equal(left, right))

    def test_candidate_site_builder_accepts_reference_n_outside_retained_hit(self) -> None:
        query = self.root / "query.fa"
        target = self.root / "target.fa"
        tfosorted = self.root / "retained-TFOsorted"
        destination = self.root / "candidate_sites.tsv"
        query.write_text(">ENSGTEST\n" + "A" * 60 + "\n", encoding="ascii")
        target.write_text(">logical_full_concat\n" + "A" * 60 + "N\n", encoding="ascii")
        row = {
            "QueryStart": "1",
            "QueryEnd": "51",
            "StartInSeq": "1",
            "EndInSeq": "51",
            "Direction": "R",
            "Chr": "",
            "StartInGenome": "1",
            "EndInGenome": "51",
            "MeanStability": "2.0",
            "MeanIdentity(%)": "100",
            "Strand": "ParaPlus",
            "Rule": "2",
            "Score": "100",
            "Nt(bp)": "51",
            "Class": "0",
            "MidPoint": "26",
            "Center": "26",
            "TFO sequence": "A" * 51,
            "TTS sequence": "A" * 51,
        }
        with tfosorted.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=MODULE.candidate_sites.canonicalize_rows.TFOSORTED_COLUMNS,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(row)
        summary = MODULE.write_candidate_sites_allow_reference_n(
            query,
            target,
            tfosorted,
            destination,
            "synthetic_workload",
            "ENSGTEST",
        )
        self.assertEqual(summary["row_count"], 3)
        self.assertEqual(
            summary["reference_n_policy"],
            "input_N_allowed_only_after_decoder_rejected_every_overlapping_hit",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
