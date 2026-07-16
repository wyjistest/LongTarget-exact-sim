#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_fasim_gasal2_paper_phase2.py"


class PaperPhase2SummaryTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(SCRIPT.is_file(), "Phase 2 summary generator is missing")
        spec = importlib.util.spec_from_file_location("paper_phase2_summary", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def pair(pair_id: int, speedup: float, *, workload: str = "w1") -> dict[str, str]:
        return {
            "pair_id_text": f"{workload}__pair{pair_id:02d}__0",
            "workload_id": workload,
            "claim_id": "C1",
            "pair_id": str(pair_id),
            "pair_order": "AB" if pair_id % 2 else "BA",
            "runtime_epoch": "0",
            "runtime_commit": "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f",
            "comparator_version": "3",
            "output_contract": "fast_topk_score_stability_nt",
            "baseline_wall_seconds": str(100.0 * speedup),
            "candidate_wall_seconds": "100.0",
            "paired_speedup": str(speedup),
            "baseline_max_rss_kb": "1000",
            "candidate_max_rss_kb": "900",
            "baseline_gpu_memory_peak_mib": "10",
            "candidate_gpu_memory_peak_mib": "20",
            "top5_score_equal": "1",
            "top5_stability_equal": "1",
            "top5_nt_score_equal": "1",
            "full_output_byte_equal": "NA",
            "missing_rows": "0",
            "extra_rows": "1" if pair_id == 1 else "0",
            "fallbacks": "0",
            "oom": "0",
            "status": "clean",
            "decision": "formal_topk_contract_clean",
            "pair_summary_path": "/abs/artifacts/pair-summary.json",
        }

    def test_summarizes_inclusive_iqr_without_treating_extra_rows_as_topk_failure(self) -> None:
        module = self.load_module()
        rows = [self.pair(index, speedup) for index, speedup in enumerate((1, 2, 3, 4, 5), 1)]

        summary = module.summarize_pairs(rows)[0]

        self.assertEqual(summary["workload_id"], "w1")
        self.assertEqual(summary["valid_pairs"], 5)
        self.assertEqual(summary["median_paired_speedup"], 3.0)
        self.assertEqual(summary["paired_speedup_q1"], 2.0)
        self.assertEqual(summary["paired_speedup_q3"], 4.0)
        self.assertEqual(summary["paired_speedup_min"], 1.0)
        self.assertEqual(summary["paired_speedup_max"], 5.0)
        self.assertEqual(summary["top5_contract_clean"], 1)
        self.assertEqual(summary["diagnostic_extra_rows_total"], 1)

    def test_rejects_nonclean_pair_from_valid_summary(self) -> None:
        module = self.load_module()
        rows = [self.pair(1, 2.0)]
        rows[0]["status"] = "mismatch"

        with self.assertRaisesRegex(ValueError, "non-clean pair"):
            module.summarize_pairs(rows)

    def test_normalizes_artifact_paths_and_renders_from_computed_summary(self) -> None:
        module = self.load_module()
        with tempfile.TemporaryDirectory() as temporary:
            artifact_root = Path(temporary) / "phase2-core"
            artifact_root.mkdir()
            normalized = module.normalize_artifact_path(
                str(artifact_root / "pairs-v3" / "w1" / "pair-summary.json"),
                artifact_root,
            )
            self.assertEqual(normalized, "pairs-v3/w1/pair-summary.json")

        summary = module.summarize_pairs(
            [self.pair(index, speedup) for index, speedup in enumerate((2, 3, 4), 1)]
        )
        report = module.render_report(
            summary,
            failure_count=3,
            artifact_root_label=".paper-artifacts/freeze/phase2-core",
            artifact_manifest_sha256="a" * 64,
            failure_reason_counts={
                "pair_comparator_failure": 1,
                "superseded_derived_pair": 2,
            },
        )
        self.assertIn("3.000000x", report)
        self.assertIn("2.500000-3.500000", report)
        self.assertIn("retained failure/mismatch artifacts: 3", report)
        self.assertIn("pair_comparator_failure=1", report)
        self.assertIn("superseded_derived_pair=2", report)

    def test_selects_required_descriptive_operating_envelope_rows(self) -> None:
        module = self.load_module()
        rows = [
            {
                "workload": workload,
                "contract": "contract",
                "scope": "scope",
                "status": status,
                "row_equal": "true",
                "top5_equal": "NA",
                "speedup": speedup,
                "fallbacks": fallback,
                "scoreinfo_reduced": "false",
                "align_side_reduced": "false",
                "notes": "fixture",
            }
            for workload, status, speedup, fallback in (
                ("h19_short_integrated", "pass", "1.07", "0"),
                ("malat1_first8", "fail", "0.70", "3091"),
                ("chr1_full", "pass", "1.09", "0"),
                ("neat1_first64", "fallback", "1.01", "0"),
                ("chr22_full", "pass", "0.99", "0"),
                ("unrelated", "pass", "9.99", "0"),
            )
        ]

        selected = module.select_operating_envelope(rows, "digest")

        self.assertEqual(
            [row["workload_id"] for row in selected],
            ["chr1_full", "chr22_full", "h19_short_integrated", "malat1_first8", "neat1_first64"],
        )
        self.assertTrue(all(row["n"] == 1 for row in selected))
        self.assertTrue(
            all(row["source_class"] == "committed_historical_artifact" for row in selected)
        )
        self.assertEqual(next(row for row in selected if row["workload_id"] == "malat1_first8")["status"], "fail")

    def test_atomic_copy_preserves_manifest_bytes(self) -> None:
        module = self.load_module()
        self.assertTrue(
            hasattr(module, "atomic_copy"),
            "Phase 2 manifest export must preserve raw bytes",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.tsv"
            destination = root / "nested" / "destination.tsv"
            source.write_bytes(b"a\tb\r\n1\t2\r\n")

            module.atomic_copy(source, destination)

            self.assertEqual(destination.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
