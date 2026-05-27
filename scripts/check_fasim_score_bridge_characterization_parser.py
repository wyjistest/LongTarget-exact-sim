#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_score_bridge_characterization as bench


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.json"
        report = {
            "single_vs_sharded_digest_match": True,
            "merged_records": 926,
            "single_run": {"wall_seconds": 3.5},
            "per_worker": [
                {"wall_seconds": 1.25},
                {"wall_seconds": 1.50},
            ],
            "sharded_telemetry": {
                "fasim_prealign_cuda_fallbacks": 0,
                "fasim_prealign_cuda_total_seconds": 0.20,
                "fasim_extend_seconds": 6.0,
                "fasim_extend_align_seconds": 5.5,
                "fasim_align_forward_score_end_seconds": 2.0,
                "fasim_score_bridge_shadow_enabled": 1,
                "fasim_score_bridge_requests": 1000,
                "fasim_score_bridge_cells": 123456789,
                "fasim_score_bridge_groups": 4,
                "fasim_score_bridge_descriptor_count": 1000,
                "fasim_score_bridge_descriptor_bytes": 32000,
                "fasim_score_bridge_query_buffer_bytes": 8000,
                "fasim_score_bridge_target_buffer_bytes": 64000,
                "fasim_score_bridge_cpu_reference_seconds": 2.0,
                "fasim_score_bridge_pack_seconds": 0.10,
                "fasim_score_bridge_h2d_seconds": 0.20,
                "fasim_score_bridge_kernel_seconds": 0.30,
                "fasim_score_bridge_d2h_seconds": 0.40,
                "fasim_score_bridge_unpack_seconds": 0.05,
                "fasim_score_bridge_total_seconds": 1.05,
                "fasim_score_bridge_score_mismatches": 0,
                "fasim_score_bridge_endpoint_mismatches": 1,
                "fasim_score_bridge_unsupported_requests": 2,
            },
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")

        row = bench.row_from_report(
            report_path=report_path,
            workload="synthetic",
            workers=4,
            max_requests=1000,
            runner_total_seconds=1.75,
        )

        assert row["workload"] == "synthetic", row
        assert row["workers"] == 4, row
        assert row["max_requests"] == 1000, row
        assert row["wall_seconds"] == 1.5, row
        assert row["digest_match"] == 1, row
        assert row["records"] == 926, row
        assert row["bridge_shadow_enabled"] == 1, row
        assert row["bridge_requests"] == 1000, row
        assert row["bridge_cells"] == 123456789, row
        assert row["bridge_groups"] == 4, row
        assert row["bridge_descriptor_count"] == 1000, row
        assert row["bridge_descriptor_bytes"] == 32000, row
        assert row["bridge_query_buffer_bytes"] == 8000, row
        assert row["bridge_target_buffer_bytes"] == 64000, row
        assert row["bridge_descriptor_bytes_per_request"] == 32.0, row
        assert row["bridge_target_bytes_per_request"] == 64000 / 998, row
        assert row["bridge_query_bytes_per_group"] == 2000.0, row
        assert row["bridge_cpu_reference_seconds"] == 2.0, row
        assert row["bridge_total_seconds"] == 1.05, row
        assert row["bridge_processed_requests"] == 998, row
        assert row["bridge_processed_fraction"] == 0.998, row
        assert row["bridge_total_vs_observed_cpu_reference"] == 0.525, row
        assert row["bridge_processed_cpu_reference_est_seconds"] == 1.996, row
        assert row["bridge_total_vs_processed_cpu_reference_est"] == 1.05 / 1.996, row
        assert row["bridge_score_mismatches"] == 0, row
        assert row["bridge_endpoint_mismatches"] == 1, row
        assert row["bridge_unsupported_requests"] == 2, row

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
