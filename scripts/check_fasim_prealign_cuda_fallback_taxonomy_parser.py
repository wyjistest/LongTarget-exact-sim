#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_prealign_cuda_fallback_taxonomy as bench


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
                "fasim_prealign_cuda_fallback_query_too_long_or_unsupported": 2,
                "fasim_prealign_cuda_fallback_cuda_allocation_or_launch": 0,
                "fasim_prealign_cuda_topk": 64,
                "fasim_prealign_cuda_max_tasks": 4096,
                "fasim_prealign_cuda_peak_suppress_bp": 5,
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
            runner_total_seconds=5.25,
        )

        assert row["workload"] == "fixture", row
        assert row["target_record_count"] == 4, row
        assert row["group_target_records"] == 2, row
        assert row["grouped_shard_count"] == 2, row
        assert row["worker_count"] == 2, row
        assert row["wall_seconds"] == 5.0, row
        assert row["digest_match"] == 1, row
        assert row["prealign_cuda_requested"] == 1, row
        assert row["prealign_cuda_active"] == 0, row
        assert row["prealign_cuda_fallbacks"] == 2, row
        assert row["fallback_reason_total"] == 2, row
        assert row["fallback_reason_top"] == "query_too_long_or_unsupported", row
        assert row["fallback_reason_top_count"] == 2, row
        assert row["fallback_query_too_long_or_unsupported"] == 2, row
        assert row["topk"] == 64, row
        assert row["max_tasks"] == 4096, row
        assert row["suppress_bp"] == 5, row
        assert row["profile_cache_hit_rate"] == 0.99, row

        assert bench.parse_group_values("none,8,16") == [None, 8, 16]
        assert bench.parse_group_values("8,none,8") == [None, 8]
        assert bench.group_label(None) == "default"
        assert bench.group_label(16) == "16"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
