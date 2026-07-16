#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/summarize_fasim_gasal2_paper_phase3.py"


class PaperPhase3SummaryTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(SCRIPT.is_file(), "Phase 3 summarizer is missing")
        spec = importlib.util.spec_from_file_location("paper_phase3_summary", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def pair(
        workload: str,
        pair_id: int,
        status: str,
        *,
        query_id: str = "MALAT1",
        target_id: str = "chr11_center_2mb",
        role: str = "generalization_core",
        speedup: float = 10.0,
    ) -> dict[str, str]:
        equal = "1" if status == "clean" else "0"
        return {
            "pair_id_text": f"{workload}__pair{pair_id:02d}__0",
            "workload_id": workload,
            "claim_id": "C2",
            "role": role,
            "query_id": query_id,
            "query_length_nt": "1024",
            "fragment_position": "5p",
            "target_id": target_id,
            "target_region": "slice:1-100",
            "preset_id": "gasal2_short_topk_v1",
            "pair_id": str(pair_id),
            "pair_order": "AB",
            "runtime_epoch": "0",
            "runtime_commit": "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f",
            "comparator_version": "1",
            "output_contract": "fast_topk_score_stability_nt",
            "baseline_wall_seconds": str(speedup * 2),
            "candidate_wall_seconds": "2",
            "paired_speedup": str(speedup),
            "baseline_max_rss_kb": "1000",
            "candidate_max_rss_kb": "900",
            "baseline_gpu_memory_peak_mib": "10",
            "candidate_gpu_memory_peak_mib": "20",
            "raw_score_top5_equal": "1",
            "raw_stability_top5_equal": equal,
            "raw_nt_top5_equal": "1",
            "clustered_score_top5_equal": "1",
            "clustered_stability_top5_equal": equal,
            "clustered_nt_top5_equal": "1",
            "all_three_top5_equal": equal,
            "boundary_ties_equal": "1",
            "baseline_boundary_tie_groups": "0",
            "candidate_boundary_tie_groups": "0",
            "baseline_representative_conflict_clusters": "0",
            "candidate_representative_conflict_clusters": "0",
            "full_missing_rows": "1",
            "full_extra_rows": "2",
            "candidate_active_path": "1",
            "gasal2_requests": "100",
            "traceback_requests": "50",
            "fallbacks": "0",
            "length_guard_fallbacks": "0",
            "runtime_batch_fallbacks": "0",
            "overflow_fallbacks": "0",
            "oom": "0",
            "status": status,
            "decision": f"generalization_clustered_contract_{status}",
            "details_path": "pairs-v1/details.tsv",
            "pair_summary_path": "pairs-v1/summary.json",
        }

    def test_workload_summary_keeps_repeat_consistent_mismatch(self) -> None:
        module = self.load_module()
        rows = [self.pair("g01", index, "mismatch", speedup=value) for index, value in enumerate((9, 10, 11), 1)]

        summary = module.summarize_workloads(rows)[0]

        self.assertEqual(summary["status"], "mismatch")
        self.assertEqual(summary["valid_pairs"], 3)
        self.assertEqual(summary["median_paired_speedup"], 10.0)
        self.assertEqual(summary["clustered_stability_all_equal"], 0)
        self.assertEqual(summary["fallbacks_total"], 0)

    def test_preregistered_ten_of_thirteen_clean_is_supported(self) -> None:
        module = self.load_module()
        identities = ["MALAT1", "NEAT1", "KCNQ1OT1", "H19", "MEG3"]
        targets = ["chr11_center_2mb", "chr21_center_2mb", "chr22_center_2mb"]
        rows = []
        for index in range(13):
            clean = index < 10
            rows.append(
                self.pair(
                    f"g{index + 1:02d}",
                    1,
                    "clean" if clean else "mismatch",
                    query_id=identities[index % len(identities)],
                    target_id=targets[index % len(targets)],
                    role="breadth",
                )
            )
        summaries = module.summarize_workloads(rows)

        decision = module.generalization_decision(summaries)

        self.assertEqual(decision["decision"], "generalization_supported")
        self.assertEqual(decision["clean_workloads"], 10)
        self.assertAlmostEqual(decision["clean_fraction"], 10 / 13)

    def test_mismatch_details_are_aggregated_with_pair_identity(self) -> None:
        module = self.load_module()
        with tempfile.TemporaryDirectory() as temporary:
            artifact_root = Path(temporary)
            details = artifact_root / "pairs-v1" / "g01" / "top5-details.tsv"
            details.parent.mkdir(parents=True)
            details.write_text(
                "side\tkind\tmode\trank\tcluster_id\tTFO sequence\n"
                "baseline\tclustered\tstability\t1\t2\tAAAA\n",
                encoding="utf-8",
            )
            row = self.pair("g01", 1, "mismatch")
            row["details_path"] = str(details)

            fields, aggregated = module.aggregate_mismatch_details([row], artifact_root)

            self.assertEqual(fields[:3], ["pair_id_text", "workload_id", "pair_status"])
            self.assertEqual(aggregated[0]["pair_id_text"], row["pair_id_text"])
            self.assertEqual(aggregated[0]["TFO sequence"], "AAAA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
