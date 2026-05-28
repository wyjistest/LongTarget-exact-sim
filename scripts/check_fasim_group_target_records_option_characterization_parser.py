#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_group_target_records_option as bench


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "report.json"
        report = {
            "run_status": "completed",
            "target_record_count": 3,
            "group_target_records": 2,
            "grouped_shard_count": 2,
            "shard_count": 2,
            "worker_count": 2,
            "merged_records": 12,
            "duplicate_records_removed": 1,
            "single_vs_sharded_digest_match": True,
            "resumed_shards": [],
            "failed_shards": [],
            "manifest": str(root / "run_manifest.json"),
            "per_worker": [
                {"wall_seconds": 5.0, "shard_ids": ["shard_0000"]},
                {"wall_seconds": 3.0, "shard_ids": ["shard_0001"]},
            ],
            "per_shard": [
                {"records": 8, "run": {"wall_seconds": 4.5}},
                {"records": 4, "run": {"wall_seconds": 2.5}},
            ],
            "sharded_telemetry": {
                "fasim_prealign_cuda_fallbacks": 0,
                "fasim_prealign_cuda_tasks": 30,
                "fasim_prealign_cuda_batches": 2,
                "fasim_align_profile_cache_active": 1,
                "fasim_align_profile_cache_calls": 100,
                "fasim_align_profile_cache_hits": 97,
                "fasim_align_profile_cache_misses": 3,
                "fasim_extend_seconds": 2.25,
                "fasim_output_seconds": 0.125,
            },
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")

        row = bench.row_from_runner_report(
            report_path=report_path,
            workload_name="fixture",
            target_bases=12345,
            group_target_records=2,
            worker_count=2,
            baseline_by_worker={2: {"wall_seconds": 10.0, "fallbacks": 0}},
            runner_total_seconds=5.25,
            resume_status="fresh_manifest",
        )

        assert row["workload"] == "fixture", row
        assert row["target_record_count"] == 3, row
        assert row["target_bases"] == 12345, row
        assert row["group_target_records"] == 2, row
        assert row["group_label"] == "2", row
        assert row["grouped_shard_count"] == 2, row
        assert row["worker_count"] == 2, row
        assert row["wall_seconds"] == 5.0, row
        assert row["runner_total_seconds"] == 5.25, row
        assert row["speedup_vs_default_grouping"] == 2.0, row
        assert row["digest_match"] == 1, row
        assert row["merged_records"] == 12, row
        assert row["duplicate_removed"] == 1, row
        assert row["prealign_cuda_fallbacks"] == 0, row
        assert row["prealign_cuda_fallback_delta_vs_default"] == 0, row
        assert row["prealign_cuda_tasks"] == 30, row
        assert row["prealign_cuda_batches"] == 2, row
        assert row["profile_cache_active"] == 1, row
        assert row["profile_cache_hit_rate"] == 0.97, row
        assert row["extend_seconds"] == 2.25, row
        assert row["output_seconds"] == 0.125, row
        assert row["imbalance_ratio"] == 5.0 / 4.0, row
        assert row["per_worker_seconds"] == [5.0, 3.0], row
        assert row["per_worker_shards"] == [1, 1], row
        assert row["per_shard_records"] == [8, 4], row
        assert row["per_shard_seconds"] == [4.5, 2.5], row
        assert row["manifest_resume_status"] == "fresh_manifest", row

        assert bench.parse_group_values("none,8,16,32") == [None, 8, 16, 32]
        assert bench.parse_group_values("8,none,16") == [None, 8, 16]
        assert bench.group_label(None) == "default"
        assert bench.group_label(16) == "16"

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
