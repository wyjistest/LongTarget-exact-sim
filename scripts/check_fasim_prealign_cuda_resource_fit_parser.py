#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_prealign_cuda_resource_fit as bench


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "report.json"
        report = {
            "target_record_count": 4,
            "group_target_records": 2,
            "grouped_shard_count": 2,
            "merged_records": 20,
            "duplicate_records_removed": 1,
            "merged_digest": "baseline-digest",
            "single_digest": "single-digest",
            "single_vs_sharded_digest_match": True,
            "per_worker": [
                {"wall_seconds": 5.0, "shard_ids": ["shard_0000"]},
                {"wall_seconds": 3.0, "shard_ids": ["shard_0001"]},
            ],
            "sharded_telemetry": {
                "fasim_prealign_cuda_requested": 1,
                "fasim_prealign_cuda_active": 0,
                "fasim_prealign_cuda_tasks": 0,
                "fasim_prealign_cuda_batches": 0,
                "fasim_prealign_cuda_fallbacks": 2,
                "fasim_prealign_cuda_fallback_query_too_long_or_unsupported": 0,
                "fasim_prealign_cuda_fallback_cuda_allocation_or_launch": 2,
                "fasim_prealign_cuda_topk": 32,
                "fasim_prealign_cuda_max_tasks": 1024,
                "fasim_prealign_cuda_peak_suppress_bp": 5,
                "fasim_prealign_cuda_dynamic_smem_required": 131584,
                "fasim_prealign_cuda_dynamic_smem_limit": 49152,
                "fasim_prealign_cuda_shared_mem_default_limit": 49152,
                "fasim_prealign_cuda_shared_mem_optin_limit": 98304,
                "fasim_prealign_cuda_device_shared_mem_limit": 49152,
                "fasim_prealign_cuda_block_dim": 32,
                "fasim_prealign_cuda_resource_fit_supported": 0,
                "fasim_prealign_cuda_smem_optin_possible": 1,
                "fasim_prealign_cuda_smem_optin_requested": 1,
                "fasim_prealign_cuda_smem_optin_active": 0,
                "fasim_prealign_cuda_smem_optin_fallback_reason": "attribute_set_failed",
                "fasim_prealign_cuda_total_seconds": 0.0,
                "fasim_prealign_cuda_kernel_seconds": 0.0,
                "fasim_align_profile_cache_calls": 100,
                "fasim_align_profile_cache_hits": 99,
            },
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")

        row = bench.row_from_runner_report(
            report_path=report_path,
            workload_name="fixture",
            target_bases=1234,
            group_target_records=2,
            worker_count=2,
            topk_candidate=32,
            max_tasks_candidate=1024,
            runner_total_seconds=5.25,
            baseline_digest="baseline-digest",
        )

        assert row["workload"] == "fixture", row
        assert row["target_record_count"] == 4, row
        assert row["group_target_records"] == 2, row
        assert row["grouped_shard_count"] == 2, row
        assert row["worker_count"] == 2, row
        assert row["topk_candidate"] == 32, row
        assert row["max_tasks_candidate"] == 1024, row
        assert row["wall_seconds"] == 5.0, row
        assert row["digest_match"] == 1, row
        assert row["digest_match_vs_baseline"] == 1, row
        assert row["merged_digest"] == "baseline-digest", row
        assert row["baseline_digest"] == "baseline-digest", row
        assert row["prealign_cuda_requested"] == 1, row
        assert row["prealign_cuda_active"] == 0, row
        assert row["prealign_cuda_fallbacks"] == 2, row
        assert row["fallback_reason_top"] == "cuda_allocation_or_launch", row
        assert row["fallback_reason_top_count"] == 2, row
        assert row["fallback_cuda_allocation_or_launch"] == 2, row
        assert row["effective_topk"] == 32, row
        assert row["effective_max_tasks"] == 1024, row
        assert row["dynamic_smem_required"] == 131584, row
        assert row["dynamic_smem_limit"] == 49152, row
        assert row["shared_mem_default_limit"] == 49152, row
        assert row["shared_mem_optin_limit"] == 98304, row
        assert row["device_shared_mem_limit"] == 49152, row
        assert row["block_dim"] == 32, row
        assert row["resource_fit_supported"] == 0, row
        assert row["smem_optin_possible"] == 1, row
        assert row["smem_optin_requested"] == 1, row
        assert row["smem_optin_active"] == 0, row
        assert row["smem_optin_fallback_reason"] == "attribute_set_failed", row
        assert row["prealign_cuda_total_seconds"] == 0.0, row
        assert row["profile_cache_hit_rate"] == 0.99, row

        assert bench.parse_group_values("none,16") == [None, 16]
        assert bench.parse_group_values("32") == [32]
        assert bench.parse_ordered_csv_ints("64,32,16", flag="--topk-values") == [
            64,
            32,
            16,
        ]
        assert bench.parse_ordered_csv_ints("4096,1024,4096", flag="--max-tasks-values") == [
            4096,
            1024,
        ]

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
