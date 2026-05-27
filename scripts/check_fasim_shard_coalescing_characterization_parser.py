#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_shard_coalescing_characterization as bench


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target.fa"
        target.write_text(
            ">hg19|chr11_a|10-13\n"
            "ACGT\n"
            ">hg19|chr11_b|20-25\n"
            "AACCGG\n"
            ">hg19|chr11_c|30-34\n"
            "TTTAA\n",
            encoding="utf-8",
        )

        records = bench.read_fasta(target)
        assert [record.header for record in records] == [
            ">hg19|chr11_a|10-13",
            ">hg19|chr11_b|20-25",
            ">hg19|chr11_c|30-34",
        ], records

        grouped_target, group_plan = bench.write_grouped_fasta(
            records=records,
            group_size=2,
            output_dir=root / "grouped",
            workload_name="fixture",
        )
        assert grouped_target.exists(), grouped_target
        assert group_plan["group_size"] == 2, group_plan
        assert group_plan["target_record_count"] == 3, group_plan
        assert group_plan["grouped_shard_count"] == 2, group_plan
        assert group_plan["groups"][0]["record_headers"] == [
            ">hg19|chr11_a|10-13",
            ">hg19|chr11_b|20-25",
        ], group_plan
        assert group_plan["groups"][1]["record_headers"] == [
            ">hg19|chr11_c|30-34",
        ], group_plan

        grouped_text = grouped_target.read_text(encoding="utf-8")
        assert ">group" not in grouped_text, grouped_text
        assert ">hg19|chr11_a|10-13" in grouped_text, grouped_text
        assert ">hg19|chr11_b|20-25" in grouped_text, grouped_text
        assert ">hg19|chr11_c|30-34" in grouped_text, grouped_text

        report_path = root / "workers_4" / "report.json"
        report_path.parent.mkdir(parents=True)
        report = {
            "summary": {"all_digest_match": True},
            "baseline": {
                "single_seconds": 11.0,
                "merged_digest": "abc123",
            },
            "runs": [
                {
                    "worker_count": 4,
                    "wall_seconds": 7.5,
                    "runner_total_seconds": 8.0,
                    "shard_count": 2,
                    "merged_records": 12,
                    "merged_digest": "abc123",
                    "single_digest": "abc123",
                    "single_vs_sharded_digest_match": True,
                    "duplicate_records_removed": 3,
                    "fallbacks": 0,
                    "per_worker_seconds": [7.5, 4.0, 0.0, 0.0],
                    "per_worker_records": [8, 4, 0, 0],
                    "per_shard_seconds": [7.0, 0.5],
                    "per_shard_records": [8, 4],
                    "report_path": str(report_path),
                    "per_worker": [
                        {
                            "telemetry": {
                                "fasim_prealign_cuda_tasks": 5,
                                "fasim_prealign_cuda_batches": 2,
                                "fasim_align_profile_cache_active": 1,
                                "fasim_align_profile_cache_calls": 20,
                                "fasim_align_profile_cache_hits": 18,
                                "fasim_align_profile_cache_misses": 2,
                                "fasim_extend_seconds": 1.5,
                                "fasim_output_seconds": 0.25,
                            }
                        }
                    ],
                }
            ],
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")

        row = bench.row_from_scaling_report(
            report_path=report_path,
            workload_name="fixture",
            target_record_count=3,
            group_size=2,
            grouped_shard_count=2,
            worker_count=4,
            baseline_by_worker={4: {"wall_seconds": 10.0, "fallbacks": 0}},
        )

        assert row["workload"] == "fixture", row
        assert row["target_record_count"] == 3, row
        assert row["group_size"] == 2, row
        assert row["grouped_shard_count"] == 2, row
        assert row["worker_count"] == 4, row
        assert row["wall_seconds"] == 7.5, row
        assert row["speedup_vs_group_size_1"] == 10.0 / 7.5, row
        assert row["digest_match"] == 1, row
        assert row["merged_records"] == 12, row
        assert row["duplicate_removed"] == 3, row
        assert row["prealign_cuda_fallbacks"] == 0, row
        assert row["prealign_cuda_fallback_delta_vs_group_size_1"] == 0, row
        assert row["prealign_cuda_tasks"] == 5, row
        assert row["prealign_cuda_batches"] == 2, row
        assert row["profile_cache_active"] == 1, row
        assert row["profile_cache_hit_rate"] == 18 / 20, row
        assert row["extend_seconds"] == 1.5, row
        assert row["output_seconds"] == 0.25, row
        assert row["imbalance_ratio"] == 7.5 / ((7.5 + 4.0) / 2), row
        assert row["per_worker_seconds"] == [7.5, 4.0, 0.0, 0.0], row
        assert row["per_shard_records"] == [8, 4], row

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
