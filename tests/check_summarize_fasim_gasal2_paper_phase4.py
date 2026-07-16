#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/summarize_fasim_gasal2_paper_phase4.py"


def load_module():
    if not SCRIPT.is_file():
        raise AssertionError("Phase 4 summarizer is missing")
    spec = importlib.util.spec_from_file_location("paper_phase4_summary", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load Phase 4 summarizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pair(workload: str, pair_id: int, **values: object) -> dict[str, str]:
    row = {
        "pair_id_text": f"{workload}__pair{pair_id:02d}__0",
        "workload_id": workload,
        "claim_id": "C6" if workload.startswith("c6") else "C5",
        "pair_id": str(pair_id),
        "runtime_epoch": "0",
        "runtime_commit": "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f",
        "output_contract": "full_tfosorted_rowset",
        "baseline_wall_seconds": "10",
        "candidate_wall_seconds": "8",
        "paired_speedup": "1.25",
        "baseline_max_rss_kb": "1000",
        "candidate_max_rss_kb": "900",
        "baseline_gpu_memory_peak_mib": "10",
        "candidate_gpu_memory_peak_mib": "20",
        "status": "clean",
        "fallbacks": "0",
        "overflow_batches": "0",
    }
    row.update({key: str(value) for key, value in values.items()})
    return row


class PaperPhase4SummaryTests(unittest.TestCase):
    def test_exact_summary_keeps_stage_and_end_to_end_effects_separate(self) -> None:
        module = load_module()
        rows = [
            pair(
                "c6_exact_kcnq_segment_chr22",
                index,
                baseline_wall_seconds=baseline,
                candidate_wall_seconds=candidate,
                paired_speedup=baseline / candidate,
                baseline_exact_stage_seconds=8,
                candidate_exact_stage_seconds=4,
                exact_stage_speedup=2,
                exact_tasks=100,
                exact_cells=1000,
                exact_work_equal=1,
                request_counts_equal=1,
                full_output_byte_equal=1,
                all_three_top5_equal=1,
                boundary_ties_equal=1,
            )
            for index, (baseline, candidate) in enumerate(((10, 8), (11, 9), (12, 10)), 1)
        ]

        summary = module.summarize_pairs(rows)[0]

        self.assertEqual(summary["valid_pairs"], 3)
        self.assertEqual(summary["median_paired_speedup"], 11 / 9)
        self.assertEqual(summary["median_exact_stage_speedup"], 2.0)
        self.assertEqual(summary["all_pairs_clean"], 1)
        self.assertEqual(summary["exact_work_equal_all"], 1)

    def test_sqlite_merge_summary_retains_wall_cost_and_rss_benefit(self) -> None:
        module = load_module()
        rows = [
            pair(
                "c5_archive_large_synthetic",
                index,
                output_contract="archive_restore_only",
                baseline_wall_seconds=1.7,
                candidate_wall_seconds=2.2,
                paired_speedup=1.7 / 2.2,
                memory_merge_wall_seconds=1.2,
                sqlite_merge_wall_seconds=1.65,
                memory_peak_rss_kb=44000,
                sqlite_peak_rss_kb=29000,
                peak_rss_reduction_fraction=0.34,
                full_output_byte_equal=1,
            )
            for index in range(1, 4)
        ]

        summary = module.summarize_pairs(rows)[0]

        self.assertLess(summary["median_paired_speedup"], 1)
        self.assertEqual(summary["median_peak_rss_reduction_fraction"], 0.34)
        self.assertEqual(summary["full_output_clean_all"], 1)

    def test_linked_ablation_does_not_invent_a_same_workload_triad(self) -> None:
        module = load_module()
        phase2 = [
            {
                "workload_id": "c1_h19_chr21_chr22_fast_topk",
                "claim_id": "C1",
                "output_contract": "fast_topk_score_stability_nt",
                "valid_pairs": "5",
                "median_paired_speedup": "38.32",
            },
            {
                "workload_id": "c4_h19_chr21_two_slot",
                "claim_id": "C4",
                "output_contract": "fast_topk_score_stability_nt",
                "valid_pairs": "5",
                "median_paired_speedup": "1.14",
            },
            {
                "workload_id": "c4_h19_chr22_two_slot",
                "claim_id": "C4",
                "output_contract": "fast_topk_score_stability_nt",
                "valid_pairs": "5",
                "median_paired_speedup": "1.15",
            },
        ]

        rows = module.linked_ablation_rows(phase2)

        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["same_workload_abc_triad"] == 0 for row in rows))
        self.assertEqual(
            {row["contrast"] for row in rows},
            {"authority_vs_checked_gasal2", "sync_vs_two_slot"},
        )

    def test_historical_resource_rows_count_active_not_available_gpus(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            summary = root / "multiworker.json"
            summary.write_text(
                json.dumps(
                    {
                        "workers_1_two_slot_peak_gpu_compute_used_mb_median": 19746,
                        "workers_1_two_slot_peak_rss_tree_kb_median": 1000,
                        "workers_2_two_slot_peak_gpu_compute_used_mb_median": 39492,
                        "workers_2_two_slot_peak_rss_tree_kb_median": 2000,
                    }
                ),
                encoding="utf-8",
            )

            rows = module.resource_rows([], root, summary)

        by_workers = {row["worker_count"]: row for row in rows}
        self.assertEqual(by_workers[1]["gpu_count"], 1)
        self.assertEqual(by_workers[2]["gpu_count"], 2)
        self.assertEqual(by_workers[4]["gpu_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
