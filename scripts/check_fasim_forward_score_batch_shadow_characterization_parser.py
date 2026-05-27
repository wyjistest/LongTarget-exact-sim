#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import benchmark_fasim_forward_score_batch_shadow_characterization as bench


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
                "fasim_forward_score_batch_shadow_enabled": 1,
                "fasim_forward_score_batch_requests": 1000,
                "fasim_forward_score_batch_cells": 123456789,
                "fasim_forward_score_batch_cpu_reference_seconds": 2.0,
                "fasim_forward_score_batch_pack_seconds": 0.10,
                "fasim_forward_score_batch_h2d_seconds": 0.20,
                "fasim_forward_score_batch_kernel_seconds": 0.30,
                "fasim_forward_score_batch_d2h_seconds": 0.40,
                "fasim_forward_score_batch_unpack_seconds": 0.05,
                "fasim_forward_score_batch_total_seconds": 1.05,
                "fasim_forward_score_batch_score_mismatches": 0,
                "fasim_forward_score_batch_endpoint_mismatches": 1,
                "fasim_forward_score_batch_unsupported_requests": 2,
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
        assert row["batch_shadow_enabled"] == 1, row
        assert row["batch_requests"] == 1000, row
        assert row["batch_cells"] == 123456789, row
        assert row["batch_cpu_reference_seconds"] == 2.0, row
        assert row["batch_total_seconds"] == 1.05, row
        assert row["batch_processed_requests"] == 998, row
        assert row["batch_processed_fraction"] == 0.998, row
        assert row["batch_total_vs_observed_cpu_reference"] == 0.525, row
        assert row["batch_processed_cpu_reference_est_seconds"] == 1.996, row
        assert row["batch_total_vs_processed_cpu_reference_est"] == 1.05 / 1.996, row
        assert row["batch_score_mismatches"] == 0, row
        assert row["batch_endpoint_mismatches"] == 1, row
        assert row["batch_unsupported_requests"] == 2, row

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
