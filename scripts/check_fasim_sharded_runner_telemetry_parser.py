#!/usr/bin/env python3
import tempfile
from pathlib import Path

import fasim_sharded_runner as runner


def main() -> int:
    stderr_text = "\n".join(
        [
            "ordinary stderr line",
            "benchmark.fasim_prealign_cuda_requested=1",
            "benchmark.fasim_prealign_cuda_active=1",
            "benchmark.fasim_prealign_cuda_device=0",
            "benchmark.fasim_prealign_cuda_devices=1",
            "benchmark.fasim_prealign_cuda_tasks=12",
            "benchmark.fasim_prealign_cuda_batches=3",
            "benchmark.fasim_prealign_cuda_topk=64",
            "benchmark.fasim_prealign_cuda_max_tasks=4096",
            "benchmark.fasim_prealign_cuda_peak_suppress_bp=5",
            "benchmark.fasim_prealign_cuda_h2d_seconds=0.010000",
            "benchmark.fasim_prealign_cuda_kernel_seconds=0.120000",
            "benchmark.fasim_prealign_cuda_d2h_seconds=0.020000",
            "benchmark.fasim_prealign_cuda_total_seconds=0.150000",
            "benchmark.fasim_prealign_cuda_dynamic_smem_required=131584",
            "benchmark.fasim_prealign_cuda_dynamic_smem_limit=49152",
            "benchmark.fasim_prealign_cuda_device_shared_mem_limit=49152",
            "benchmark.fasim_prealign_cuda_block_dim=32",
            "benchmark.fasim_prealign_cuda_resource_fit_supported=0",
            "benchmark.fasim_prealign_cuda_fallback_unsupported_rule=0",
            "benchmark.fasim_prealign_cuda_fallback_unsupported_sequence_alphabet=0",
            "benchmark.fasim_prealign_cuda_fallback_too_few_tasks=0",
            "benchmark.fasim_prealign_cuda_fallback_too_many_tasks=0",
            "benchmark.fasim_prealign_cuda_fallback_target_too_short=0",
            "benchmark.fasim_prealign_cuda_fallback_query_too_long_or_unsupported=2",
            "benchmark.fasim_prealign_cuda_fallback_cuda_allocation_or_launch=1",
            "benchmark.fasim_prealign_cuda_fallback_empty_candidate_set=0",
            "benchmark.fasim_prealign_cuda_fallback_unknown=0",
            "benchmark.fasim_extend_threads=2",
            "benchmark.fasim_extend_seconds=0.500000",
            "benchmark.fasim_extend_candidates=4",
            "benchmark.fasim_extend_cutlength_attempts=7",
            "benchmark.fasim_extend_align_calls=7",
            "benchmark.fasim_extend_align_cells=7000",
            "benchmark.fasim_extend_align_seconds=0.300000",
            "benchmark.fasim_extend_convert_calls=3",
            "benchmark.fasim_extend_convert_seconds=0.040000",
            "benchmark.fasim_extend_sort_unique_seconds=0.010000",
            "benchmark.fasim_extend_records_before_filter=5",
            "benchmark.fasim_extend_records_emitted=2",
            "benchmark.fasim_extend_empty_scoreinfo=1",
            "benchmark.fasim_align_query_translate_seconds=0.010000",
            "benchmark.fasim_align_ref_translate_seconds=0.020000",
            "benchmark.fasim_align_profile_seconds=0.030000",
            "benchmark.fasim_align_ssw_total_seconds=0.200000",
            "benchmark.fasim_align_forward_score_end_seconds=0.110000",
            "benchmark.fasim_align_reverse_start_seconds=0.040000",
            "benchmark.fasim_align_traceback_seconds=0.050000",
            "benchmark.fasim_align_forward_score_gpu_shadow_enabled=1",
            "benchmark.fasim_align_forward_score_gpu_requests=7",
            "benchmark.fasim_align_forward_score_gpu_cells=7000",
            "benchmark.fasim_align_forward_score_gpu_cpu_seconds=0.110000",
            "benchmark.fasim_align_forward_score_gpu_pack_seconds=0.001000",
            "benchmark.fasim_align_forward_score_gpu_h2d_seconds=0.020000",
            "benchmark.fasim_align_forward_score_gpu_kernel_seconds=0.030000",
            "benchmark.fasim_align_forward_score_gpu_d2h_seconds=0.040000",
            "benchmark.fasim_align_forward_score_gpu_unpack_seconds=0.002000",
            "benchmark.fasim_align_forward_score_gpu_total_seconds=0.095000",
            "benchmark.fasim_align_forward_score_gpu_score_mismatches=0",
            "benchmark.fasim_align_forward_score_gpu_endpoint_mismatches=1",
            "benchmark.fasim_align_forward_score_gpu_unsupported_requests=2",
            "benchmark.fasim_forward_score_batch_shadow_enabled=1",
            "benchmark.fasim_forward_score_batch_requests=7",
            "benchmark.fasim_forward_score_batch_cells=7000",
            "benchmark.fasim_forward_score_batch_pack_seconds=0.003000",
            "benchmark.fasim_forward_score_batch_h2d_seconds=0.021000",
            "benchmark.fasim_forward_score_batch_kernel_seconds=0.031000",
            "benchmark.fasim_forward_score_batch_d2h_seconds=0.041000",
            "benchmark.fasim_forward_score_batch_unpack_seconds=0.004000",
            "benchmark.fasim_forward_score_batch_total_seconds=0.096000",
            "benchmark.fasim_forward_score_batch_cpu_reference_seconds=0.110000",
            "benchmark.fasim_forward_score_batch_score_mismatches=0",
            "benchmark.fasim_forward_score_batch_endpoint_mismatches=1",
            "benchmark.fasim_forward_score_batch_unsupported_requests=2",
            "benchmark.fasim_score_bridge_shadow_enabled=1",
            "benchmark.fasim_score_bridge_requests=7",
            "benchmark.fasim_score_bridge_cells=7000",
            "benchmark.fasim_score_bridge_groups=1",
            "benchmark.fasim_score_bridge_descriptor_count=7",
            "benchmark.fasim_score_bridge_descriptor_bytes=336",
            "benchmark.fasim_score_bridge_query_buffer_bytes=42",
            "benchmark.fasim_score_bridge_target_buffer_bytes=700",
            "benchmark.fasim_score_bridge_pack_seconds=0.005000",
            "benchmark.fasim_score_bridge_h2d_seconds=0.022000",
            "benchmark.fasim_score_bridge_kernel_seconds=0.032000",
            "benchmark.fasim_score_bridge_d2h_seconds=0.042000",
            "benchmark.fasim_score_bridge_unpack_seconds=0.006000",
            "benchmark.fasim_score_bridge_total_seconds=0.107000",
            "benchmark.fasim_score_bridge_cpu_reference_seconds=0.110000",
            "benchmark.fasim_score_bridge_score_mismatches=0",
            "benchmark.fasim_score_bridge_endpoint_mismatches=1",
            "benchmark.fasim_score_bridge_unsupported_requests=2",
            "benchmark.fasim_align_convert_seconds=0.060000",
            "benchmark.fasim_align_cleanup_seconds=0.005000",
            "benchmark.fasim_align_calls=7",
            "benchmark.fasim_align_byte_forward_calls=5",
            "benchmark.fasim_align_word_forward_calls=2",
            "benchmark.fasim_align_reverse_calls=7",
            "benchmark.fasim_align_traceback_calls=7",
            "benchmark.fasim_align_null_results=0",
            "benchmark.fasim_align_profile_reuse_shadow_enabled=1",
            "benchmark.fasim_align_profile_build_calls=7",
            "benchmark.fasim_align_profile_unique_keys=1",
            "benchmark.fasim_align_profile_reusable_calls=6",
            "benchmark.fasim_align_profile_build_seconds=0.030000",
            "benchmark.fasim_align_profile_est_saved_seconds=0.025000",
            "benchmark.fasim_align_query_unique_keys=1",
            "benchmark.fasim_align_query_reusable_calls=6",
            "benchmark.fasim_align_profile_cache_requested=1",
            "benchmark.fasim_align_profile_cache_active=1",
            "benchmark.fasim_align_profile_cache_validate=1",
            "benchmark.fasim_align_profile_cache_calls=7",
            "benchmark.fasim_align_profile_cache_hits=6",
            "benchmark.fasim_align_profile_cache_misses=1",
            "benchmark.fasim_align_profile_cache_unique_keys=1",
            "benchmark.fasim_align_profile_cache_build_seconds=0.030000",
            "benchmark.fasim_align_profile_cache_saved_seconds=0.025000",
            "benchmark.fasim_align_profile_cache_validate_seconds=0.070000",
            "benchmark.fasim_align_profile_cache_score_mismatches=0",
            "benchmark.fasim_align_profile_cache_endpoint_mismatches=0",
            "benchmark.fasim_align_profile_cache_cigar_mismatches=0",
            "benchmark.fasim_align_profile_cache_digest_mismatches=0",
            "benchmark.fasim_align_profile_cache_fallbacks=0",
            "benchmark.fasim_output_seconds=0.020000",
            "benchmark.fasim_prealign_cuda_fallbacks=0",
            "",
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        stderr_path = Path(tmp) / "worker.stderr.log"
        stderr_path.write_text(stderr_text, encoding="utf-8")

        telemetry = runner._parse_fasim_telemetry_file(stderr_path)
        assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry
        assert telemetry["fasim_prealign_cuda_active"] == 1, telemetry
        assert telemetry["fasim_prealign_cuda_tasks"] == 12, telemetry
        assert telemetry["fasim_prealign_cuda_batches"] == 3, telemetry
        assert telemetry["fasim_prealign_cuda_kernel_seconds"] == 0.12, telemetry
        assert telemetry["fasim_prealign_cuda_dynamic_smem_required"] == 131584, telemetry
        assert telemetry["fasim_prealign_cuda_dynamic_smem_limit"] == 49152, telemetry
        assert telemetry["fasim_prealign_cuda_device_shared_mem_limit"] == 49152, telemetry
        assert telemetry["fasim_prealign_cuda_block_dim"] == 32, telemetry
        assert telemetry["fasim_prealign_cuda_resource_fit_supported"] == 0, telemetry
        assert telemetry["fasim_prealign_cuda_fallback_query_too_long_or_unsupported"] == 2, telemetry
        assert telemetry["fasim_prealign_cuda_fallback_cuda_allocation_or_launch"] == 1, telemetry
        assert telemetry["fasim_extend_seconds"] == 0.5, telemetry
        assert telemetry["fasim_extend_candidates"] == 4, telemetry
        assert telemetry["fasim_extend_align_calls"] == 7, telemetry
        assert telemetry["fasim_extend_align_cells"] == 7000, telemetry
        assert telemetry["fasim_extend_align_seconds"] == 0.3, telemetry
        assert telemetry["fasim_extend_convert_seconds"] == 0.04, telemetry
        assert telemetry["fasim_extend_records_emitted"] == 2, telemetry
        assert telemetry["fasim_align_forward_score_end_seconds"] == 0.11, telemetry
        assert telemetry["fasim_align_reverse_start_seconds"] == 0.04, telemetry
        assert telemetry["fasim_align_traceback_seconds"] == 0.05, telemetry
        assert telemetry["fasim_align_forward_score_gpu_shadow_enabled"] == 1, telemetry
        assert telemetry["fasim_align_forward_score_gpu_requests"] == 7, telemetry
        assert telemetry["fasim_align_forward_score_gpu_cells"] == 7000, telemetry
        assert telemetry["fasim_align_forward_score_gpu_cpu_seconds"] == 0.11, telemetry
        assert telemetry["fasim_align_forward_score_gpu_total_seconds"] == 0.095, telemetry
        assert telemetry["fasim_align_forward_score_gpu_score_mismatches"] == 0, telemetry
        assert telemetry["fasim_align_forward_score_gpu_endpoint_mismatches"] == 1, telemetry
        assert telemetry["fasim_align_forward_score_gpu_unsupported_requests"] == 2, telemetry
        assert telemetry["fasim_forward_score_batch_shadow_enabled"] == 1, telemetry
        assert telemetry["fasim_forward_score_batch_requests"] == 7, telemetry
        assert telemetry["fasim_forward_score_batch_cells"] == 7000, telemetry
        assert telemetry["fasim_forward_score_batch_pack_seconds"] == 0.003, telemetry
        assert telemetry["fasim_forward_score_batch_total_seconds"] == 0.096, telemetry
        assert telemetry["fasim_forward_score_batch_cpu_reference_seconds"] == 0.11, telemetry
        assert telemetry["fasim_forward_score_batch_score_mismatches"] == 0, telemetry
        assert telemetry["fasim_forward_score_batch_endpoint_mismatches"] == 1, telemetry
        assert telemetry["fasim_forward_score_batch_unsupported_requests"] == 2, telemetry
        assert telemetry["fasim_score_bridge_shadow_enabled"] == 1, telemetry
        assert telemetry["fasim_score_bridge_requests"] == 7, telemetry
        assert telemetry["fasim_score_bridge_cells"] == 7000, telemetry
        assert telemetry["fasim_score_bridge_groups"] == 1, telemetry
        assert telemetry["fasim_score_bridge_descriptor_count"] == 7, telemetry
        assert telemetry["fasim_score_bridge_descriptor_bytes"] == 336, telemetry
        assert telemetry["fasim_score_bridge_query_buffer_bytes"] == 42, telemetry
        assert telemetry["fasim_score_bridge_target_buffer_bytes"] == 700, telemetry
        assert telemetry["fasim_score_bridge_pack_seconds"] == 0.005, telemetry
        assert telemetry["fasim_score_bridge_total_seconds"] == 0.107, telemetry
        assert telemetry["fasim_score_bridge_cpu_reference_seconds"] == 0.11, telemetry
        assert telemetry["fasim_score_bridge_score_mismatches"] == 0, telemetry
        assert telemetry["fasim_score_bridge_endpoint_mismatches"] == 1, telemetry
        assert telemetry["fasim_score_bridge_unsupported_requests"] == 2, telemetry
        assert telemetry["fasim_align_calls"] == 7, telemetry
        assert telemetry["fasim_align_byte_forward_calls"] == 5, telemetry
        assert telemetry["fasim_align_word_forward_calls"] == 2, telemetry
        assert telemetry["fasim_align_profile_reuse_shadow_enabled"] == 1, telemetry
        assert telemetry["fasim_align_profile_build_calls"] == 7, telemetry
        assert telemetry["fasim_align_profile_unique_keys"] == 1, telemetry
        assert telemetry["fasim_align_profile_reusable_calls"] == 6, telemetry
        assert telemetry["fasim_align_profile_build_seconds"] == 0.03, telemetry
        assert telemetry["fasim_align_profile_est_saved_seconds"] == 0.025, telemetry
        assert telemetry["fasim_align_query_unique_keys"] == 1, telemetry
        assert telemetry["fasim_align_query_reusable_calls"] == 6, telemetry
        assert telemetry["fasim_align_profile_cache_requested"] == 1, telemetry
        assert telemetry["fasim_align_profile_cache_active"] == 1, telemetry
        assert telemetry["fasim_align_profile_cache_validate"] == 1, telemetry
        assert telemetry["fasim_align_profile_cache_calls"] == 7, telemetry
        assert telemetry["fasim_align_profile_cache_hits"] == 6, telemetry
        assert telemetry["fasim_align_profile_cache_misses"] == 1, telemetry
        assert telemetry["fasim_align_profile_cache_unique_keys"] == 1, telemetry
        assert telemetry["fasim_align_profile_cache_build_seconds"] == 0.03, telemetry
        assert telemetry["fasim_align_profile_cache_saved_seconds"] == 0.025, telemetry
        assert telemetry["fasim_align_profile_cache_validate_seconds"] == 0.07, telemetry
        assert telemetry["fasim_align_profile_cache_score_mismatches"] == 0, telemetry
        assert telemetry["fasim_align_profile_cache_endpoint_mismatches"] == 0, telemetry
        assert telemetry["fasim_align_profile_cache_cigar_mismatches"] == 0, telemetry
        assert telemetry["fasim_align_profile_cache_digest_mismatches"] == 0, telemetry
        assert telemetry["fasim_align_profile_cache_fallbacks"] == 0, telemetry

        second_telemetry = {
            **telemetry,
            "fasim_prealign_cuda_dynamic_smem_required": 262144,
            "fasim_prealign_cuda_dynamic_smem_limit": 65536,
            "fasim_prealign_cuda_device_shared_mem_limit": 65536,
            "fasim_prealign_cuda_block_dim": 64,
            "fasim_prealign_cuda_resource_fit_supported": 1,
        }
        summed = runner._sum_fasim_telemetry([telemetry, second_telemetry])
        assert summed["fasim_prealign_cuda_requested"] == 1, summed
        assert summed["fasim_prealign_cuda_active"] == 1, summed
        assert summed["fasim_prealign_cuda_tasks"] == 24, summed
        assert summed["fasim_prealign_cuda_batches"] == 6, summed
        assert summed["fasim_prealign_cuda_kernel_seconds"] == 0.24, summed
        assert summed["fasim_prealign_cuda_dynamic_smem_required"] == 262144, summed
        assert summed["fasim_prealign_cuda_dynamic_smem_limit"] == 65536, summed
        assert summed["fasim_prealign_cuda_device_shared_mem_limit"] == 65536, summed
        assert summed["fasim_prealign_cuda_block_dim"] == 64, summed
        assert summed["fasim_prealign_cuda_resource_fit_supported"] == 0, summed
        assert summed["fasim_prealign_cuda_fallback_query_too_long_or_unsupported"] == 4, summed
        assert summed["fasim_prealign_cuda_fallback_cuda_allocation_or_launch"] == 2, summed
        assert summed["fasim_extend_seconds"] == 1.0, summed
        assert summed["fasim_extend_candidates"] == 8, summed
        assert summed["fasim_extend_cutlength_attempts"] == 14, summed
        assert summed["fasim_extend_align_calls"] == 14, summed
        assert summed["fasim_extend_align_cells"] == 14000, summed
        assert summed["fasim_extend_align_seconds"] == 0.6, summed
        assert summed["fasim_extend_convert_calls"] == 6, summed
        assert summed["fasim_extend_convert_seconds"] == 0.08, summed
        assert summed["fasim_extend_sort_unique_seconds"] == 0.02, summed
        assert summed["fasim_extend_records_before_filter"] == 10, summed
        assert summed["fasim_extend_records_emitted"] == 4, summed
        assert summed["fasim_extend_empty_scoreinfo"] == 2, summed
        assert summed["fasim_align_forward_score_end_seconds"] == 0.22, summed
        assert summed["fasim_align_reverse_start_seconds"] == 0.08, summed
        assert summed["fasim_align_traceback_seconds"] == 0.1, summed
        assert summed["fasim_align_forward_score_gpu_shadow_enabled"] == 1, summed
        assert summed["fasim_align_forward_score_gpu_requests"] == 14, summed
        assert summed["fasim_align_forward_score_gpu_cells"] == 14000, summed
        assert summed["fasim_align_forward_score_gpu_cpu_seconds"] == 0.22, summed
        assert summed["fasim_align_forward_score_gpu_pack_seconds"] == 0.002, summed
        assert summed["fasim_align_forward_score_gpu_h2d_seconds"] == 0.04, summed
        assert summed["fasim_align_forward_score_gpu_kernel_seconds"] == 0.06, summed
        assert summed["fasim_align_forward_score_gpu_d2h_seconds"] == 0.08, summed
        assert summed["fasim_align_forward_score_gpu_unpack_seconds"] == 0.004, summed
        assert summed["fasim_align_forward_score_gpu_total_seconds"] == 0.19, summed
        assert summed["fasim_align_forward_score_gpu_score_mismatches"] == 0, summed
        assert summed["fasim_align_forward_score_gpu_endpoint_mismatches"] == 2, summed
        assert summed["fasim_align_forward_score_gpu_unsupported_requests"] == 4, summed
        assert summed["fasim_forward_score_batch_shadow_enabled"] == 1, summed
        assert summed["fasim_forward_score_batch_requests"] == 14, summed
        assert summed["fasim_forward_score_batch_cells"] == 14000, summed
        assert summed["fasim_forward_score_batch_pack_seconds"] == 0.006, summed
        assert summed["fasim_forward_score_batch_h2d_seconds"] == 0.042, summed
        assert summed["fasim_forward_score_batch_kernel_seconds"] == 0.062, summed
        assert summed["fasim_forward_score_batch_d2h_seconds"] == 0.082, summed
        assert summed["fasim_forward_score_batch_unpack_seconds"] == 0.008, summed
        assert summed["fasim_forward_score_batch_total_seconds"] == 0.192, summed
        assert summed["fasim_forward_score_batch_cpu_reference_seconds"] == 0.22, summed
        assert summed["fasim_forward_score_batch_score_mismatches"] == 0, summed
        assert summed["fasim_forward_score_batch_endpoint_mismatches"] == 2, summed
        assert summed["fasim_forward_score_batch_unsupported_requests"] == 4, summed
        assert summed["fasim_score_bridge_shadow_enabled"] == 1, summed
        assert summed["fasim_score_bridge_requests"] == 14, summed
        assert summed["fasim_score_bridge_cells"] == 14000, summed
        assert summed["fasim_score_bridge_groups"] == 2, summed
        assert summed["fasim_score_bridge_descriptor_count"] == 14, summed
        assert summed["fasim_score_bridge_descriptor_bytes"] == 672, summed
        assert summed["fasim_score_bridge_query_buffer_bytes"] == 84, summed
        assert summed["fasim_score_bridge_target_buffer_bytes"] == 1400, summed
        assert summed["fasim_score_bridge_pack_seconds"] == 0.01, summed
        assert summed["fasim_score_bridge_h2d_seconds"] == 0.044, summed
        assert summed["fasim_score_bridge_kernel_seconds"] == 0.064, summed
        assert summed["fasim_score_bridge_d2h_seconds"] == 0.084, summed
        assert summed["fasim_score_bridge_unpack_seconds"] == 0.012, summed
        assert summed["fasim_score_bridge_total_seconds"] == 0.214, summed
        assert summed["fasim_score_bridge_cpu_reference_seconds"] == 0.22, summed
        assert summed["fasim_score_bridge_score_mismatches"] == 0, summed
        assert summed["fasim_score_bridge_endpoint_mismatches"] == 2, summed
        assert summed["fasim_score_bridge_unsupported_requests"] == 4, summed
        assert summed["fasim_align_calls"] == 14, summed
        assert summed["fasim_align_byte_forward_calls"] == 10, summed
        assert summed["fasim_align_word_forward_calls"] == 4, summed
        assert summed["fasim_align_reverse_calls"] == 14, summed
        assert summed["fasim_align_traceback_calls"] == 14, summed
        assert summed["fasim_align_profile_reuse_shadow_enabled"] == 1, summed
        assert summed["fasim_align_profile_build_calls"] == 14, summed
        assert summed["fasim_align_profile_unique_keys"] == 2, summed
        assert summed["fasim_align_profile_reusable_calls"] == 12, summed
        assert summed["fasim_align_profile_build_seconds"] == 0.06, summed
        assert summed["fasim_align_profile_est_saved_seconds"] == 0.05, summed
        assert summed["fasim_align_query_unique_keys"] == 2, summed
        assert summed["fasim_align_query_reusable_calls"] == 12, summed
        assert summed["fasim_align_profile_cache_requested"] == 1, summed
        assert summed["fasim_align_profile_cache_active"] == 1, summed
        assert summed["fasim_align_profile_cache_validate"] == 1, summed
        assert summed["fasim_align_profile_cache_calls"] == 14, summed
        assert summed["fasim_align_profile_cache_hits"] == 12, summed
        assert summed["fasim_align_profile_cache_misses"] == 2, summed
        assert summed["fasim_align_profile_cache_unique_keys"] == 2, summed
        assert summed["fasim_align_profile_cache_build_seconds"] == 0.06, summed
        assert summed["fasim_align_profile_cache_saved_seconds"] == 0.05, summed
        assert summed["fasim_align_profile_cache_validate_seconds"] == 0.14, summed
        assert summed["fasim_align_profile_cache_score_mismatches"] == 0, summed
        assert summed["fasim_align_profile_cache_endpoint_mismatches"] == 0, summed
        assert summed["fasim_align_profile_cache_cigar_mismatches"] == 0, summed
        assert summed["fasim_align_profile_cache_digest_mismatches"] == 0, summed
        assert summed["fasim_align_profile_cache_fallbacks"] == 0, summed
        assert summed["fasim_prealign_cuda_topk"] == 64, summed

        run = runner.RunResult(
            label="synthetic",
            cmd=["fake"],
            env_overrides={"FASIM_ENABLE_PREALIGN_CUDA": "1"},
            wall_seconds=1.25,
            stdout_path=Path(tmp) / "worker.stdout.log",
            stderr_path=stderr_path,
            output_dir=Path(tmp),
            output_path=Path(tmp) / "out.lite",
            exit_code=0,
            telemetry=telemetry,
        )
        run_json = runner._run_to_json(run)
        assert run_json["telemetry"]["fasim_prealign_cuda_tasks"] == 12, run_json
        assert run_json["telemetry"]["fasim_align_forward_score_gpu_requests"] == 7, run_json
        assert run_json["telemetry"]["fasim_forward_score_batch_requests"] == 7, run_json
        assert run_json["telemetry"]["fasim_score_bridge_requests"] == 7, run_json
        assert run_json["telemetry"]["fasim_align_profile_reusable_calls"] == 6, run_json
        assert run_json["telemetry"]["fasim_align_profile_cache_hits"] == 6, run_json

        worker = runner._worker_telemetry_from_shards(
            [
                {"run": run_json},
                {"run": {**run_json, "telemetry": {
                    "fasim_prealign_cuda_tasks": 4,
                    "fasim_prealign_cuda_fallback_query_too_long_or_unsupported": 1,
                    "fasim_prealign_cuda_fallback_cuda_allocation_or_launch": 1,
                    "fasim_extend_align_calls": 2,
                    "fasim_align_forward_score_gpu_requests": 3,
                    "fasim_align_forward_score_gpu_cells": 3000,
                    "fasim_align_forward_score_gpu_score_mismatches": 0,
                    "fasim_align_forward_score_gpu_endpoint_mismatches": 1,
                    "fasim_align_forward_score_gpu_unsupported_requests": 1,
                    "fasim_forward_score_batch_requests": 3,
                    "fasim_forward_score_batch_cells": 3000,
                    "fasim_forward_score_batch_score_mismatches": 0,
                    "fasim_forward_score_batch_endpoint_mismatches": 1,
                    "fasim_forward_score_batch_unsupported_requests": 1,
                    "fasim_score_bridge_requests": 3,
                    "fasim_score_bridge_cells": 3000,
                    "fasim_score_bridge_groups": 1,
                    "fasim_score_bridge_descriptor_count": 3,
                    "fasim_score_bridge_descriptor_bytes": 144,
                    "fasim_score_bridge_query_buffer_bytes": 42,
                    "fasim_score_bridge_target_buffer_bytes": 300,
                    "fasim_score_bridge_score_mismatches": 0,
                    "fasim_score_bridge_endpoint_mismatches": 1,
                    "fasim_score_bridge_unsupported_requests": 1,
                    "fasim_align_profile_build_calls": 2,
                    "fasim_align_profile_unique_keys": 1,
                    "fasim_align_profile_reusable_calls": 1,
                    "fasim_align_query_unique_keys": 1,
                    "fasim_align_query_reusable_calls": 1,
                    "fasim_align_profile_cache_calls": 2,
                    "fasim_align_profile_cache_hits": 1,
                    "fasim_align_profile_cache_misses": 1,
                    "fasim_align_profile_cache_unique_keys": 1,
                }}},
                {"status": "skipped_by_resume", "run": {"telemetry": {}}},
            ]
        )
        assert worker["fasim_prealign_cuda_tasks"] == 16, worker
        assert worker["fasim_prealign_cuda_fallback_query_too_long_or_unsupported"] == 3, worker
        assert worker["fasim_prealign_cuda_fallback_cuda_allocation_or_launch"] == 2, worker
        assert worker["fasim_extend_align_calls"] == 9, worker
        assert worker["fasim_align_calls"] == 7, worker
        assert worker["fasim_align_forward_score_gpu_shadow_enabled"] == 1, worker
        assert worker["fasim_align_forward_score_gpu_requests"] == 10, worker
        assert worker["fasim_align_forward_score_gpu_cells"] == 10000, worker
        assert worker["fasim_align_forward_score_gpu_score_mismatches"] == 0, worker
        assert worker["fasim_align_forward_score_gpu_endpoint_mismatches"] == 2, worker
        assert worker["fasim_align_forward_score_gpu_unsupported_requests"] == 3, worker
        assert worker["fasim_forward_score_batch_shadow_enabled"] == 1, worker
        assert worker["fasim_forward_score_batch_requests"] == 10, worker
        assert worker["fasim_forward_score_batch_cells"] == 10000, worker
        assert worker["fasim_forward_score_batch_score_mismatches"] == 0, worker
        assert worker["fasim_forward_score_batch_endpoint_mismatches"] == 2, worker
        assert worker["fasim_forward_score_batch_unsupported_requests"] == 3, worker
        assert worker["fasim_score_bridge_shadow_enabled"] == 1, worker
        assert worker["fasim_score_bridge_requests"] == 10, worker
        assert worker["fasim_score_bridge_cells"] == 10000, worker
        assert worker["fasim_score_bridge_groups"] == 2, worker
        assert worker["fasim_score_bridge_descriptor_count"] == 10, worker
        assert worker["fasim_score_bridge_descriptor_bytes"] == 480, worker
        assert worker["fasim_score_bridge_query_buffer_bytes"] == 84, worker
        assert worker["fasim_score_bridge_target_buffer_bytes"] == 1000, worker
        assert worker["fasim_score_bridge_score_mismatches"] == 0, worker
        assert worker["fasim_score_bridge_endpoint_mismatches"] == 2, worker
        assert worker["fasim_score_bridge_unsupported_requests"] == 3, worker
        assert worker["fasim_align_profile_build_calls"] == 9, worker
        assert worker["fasim_align_profile_unique_keys"] == 2, worker
        assert worker["fasim_align_profile_reusable_calls"] == 7, worker
        assert worker["fasim_align_query_unique_keys"] == 2, worker
        assert worker["fasim_align_query_reusable_calls"] == 7, worker
        assert worker["fasim_align_profile_cache_calls"] == 9, worker
        assert worker["fasim_align_profile_cache_hits"] == 7, worker
        assert worker["fasim_align_profile_cache_misses"] == 2, worker
        assert worker["fasim_align_profile_cache_unique_keys"] == 2, worker
        assert worker["fasim_prealign_cuda_requested"] == 1, worker

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
