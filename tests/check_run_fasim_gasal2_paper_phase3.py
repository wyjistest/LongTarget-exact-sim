#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "run_fasim_gasal2_paper_phase3.py"


class PaperPhase3DriverTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(DRIVER.is_file(), "Phase 3 driver is missing")
        spec = importlib.util.spec_from_file_location("paper_phase3_driver", DRIVER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def row(midpoint: int, index: int, score: int, stability: float, nt: int) -> dict[str, str]:
        from sys import path as sys_path

        if str(ROOT / "scripts") not in sys_path:
            sys_path.insert(0, str(ROOT / "scripts"))
        from fasim_tfo_archive import TFOSORTED_COLUMNS

        query_start = midpoint - 30
        query_end = midpoint + 30
        payload = {
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
        return {column: payload[column] for column in TFOSORTED_COLUMNS}

    def make_run(self, name: str, rows: list[dict[str, str]], fallback: int = 0) -> Path:
        from sys import path as sys_path

        if str(ROOT / "scripts") not in sys_path:
            sys_path.insert(0, str(ROOT / "scripts"))
        from fasim_tfo_archive import TFOSORTED_COLUMNS

        run = self.work / name
        output = run / "output"
        output.mkdir(parents=True)
        with (output / f"{name}-TFOsorted").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(TFOSORTED_COLUMNS),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        metrics = {
            "fasim_top5_gasal2_gpu_scoreinfo_requested": 1,
            "fasim_top5_gasal2_gpu_scoreinfo_active": 1,
            "fasim_gasal2_fallbacks": fallback,
            "fasim_gasal2_length_guard_fallbacks": 0,
            "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches": 0,
            "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches": 0,
            "fasim_gasal2_requests": 100,
            "fasim_gasal2_traceback_requests": 50,
        }
        (run / "stderr.log").write_text(
            "".join(f"benchmark.{key}={value}\n" for key, value in metrics.items()),
            encoding="utf-8",
        )
        return run

    def base_rows(self) -> list[dict[str, str]]:
        return [
            self.row(100, 1, 300, 1.0, 70),
            self.row(400, 2, 290, 2.0, 80),
            self.row(700, 3, 280, 3.0, 90),
            self.row(1000, 4, 270, 4.0, 100),
            self.row(1300, 5, 260, 5.0, 110),
            self.row(1600, 6, 250, 6.0, 120),
        ]

    def test_frozen_plan_has_thirteen_supported_rows_and_three_guards(self) -> None:
        module = self.load_module()
        rows = module.load_phase3_rows(ROOT / "paper/workload_manifest.tsv")
        plan = module.build_phase3_plan(
            rows,
            ROOT / "paper/workload_manifest.tsv",
            ROOT / ".tmp/fasim_longtarget_gasal2_direct",
            20260715,
        )

        self.assertEqual(plan["supported_workload_count"], 13)
        self.assertEqual(plan["guard_workload_count"], 3)
        self.assertEqual(plan["pair_count"], 31)
        self.assertEqual(plan["timed_run_count"], 62)
        self.assertEqual(plan["warmup_count"], 26)
        self.assertEqual(plan["preflight_count"], 3)

    def test_full_row_drift_is_diagnostic_when_clustered_contract_is_clean(self) -> None:
        module = self.load_module()
        baseline_rows = self.base_rows()
        candidate_rows = [*baseline_rows, self.row(2000, 99, 1, 0.1, 40)]
        baseline = self.make_run("baseline", baseline_rows)
        candidate = self.make_run("candidate", candidate_rows)
        compare = self.work / "compare"
        compare.mkdir()

        result = module.compare_supported_pair(baseline, candidate, compare)

        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["clustered_score_top5_equal"], 1)
        self.assertEqual(result["clustered_stability_top5_equal"], 1)
        self.assertEqual(result["clustered_nt_top5_equal"], 1)
        self.assertEqual(result["full_extra_rows"], 1)
        self.assertTrue((compare / "top5-details.tsv").is_file())

    def test_clustered_drift_is_mismatch_and_details_are_retained(self) -> None:
        module = self.load_module()
        baseline_rows = self.base_rows()
        candidate_rows = baseline_rows[1:]
        baseline = self.make_run("baseline", baseline_rows)
        candidate = self.make_run("candidate", candidate_rows)
        compare = self.work / "compare"
        compare.mkdir()

        result = module.compare_supported_pair(baseline, candidate, compare)

        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["all_three_top5_equal"], 0)
        with (compare / "top5-details.tsv").open(newline="", encoding="utf-8") as handle:
            details = list(csv.DictReader(handle, delimiter="\t"))
        self.assertTrue(details)
        self.assertEqual({row["side"] for row in details}, {"baseline", "candidate"})

    def test_fallback_is_not_relabelled_as_scientific_mismatch(self) -> None:
        module = self.load_module()
        rows = self.base_rows()
        baseline = self.make_run("baseline", rows)
        candidate = self.make_run("candidate", rows, fallback=1)
        compare = self.work / "compare"
        compare.mkdir()

        result = module.compare_supported_pair(baseline, candidate, compare)

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["fallbacks"], 1)
        self.assertEqual(result["all_three_top5_equal"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
