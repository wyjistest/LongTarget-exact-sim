#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_two_slot_overlap_scaffold.md"
BROADER="$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix.sh"
BROADER_CHECK="$ROOT/scripts/check_fasim_gasal2_flush_two_slot_overlap_broader_matrix_result.sh"

grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_SHADOW' "$CPP"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP"' "$CPP"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE' "$CPP"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL' "$CPP"
grep -q 'struct FasimGasal2FlushTwoSlotOverlapStats' "$CPP"
grep -q 'struct FasimGasal2TwoSlotWorkItem' "$CPP"
grep -q 'struct FasimGasal2TwoSlotCompletedItem' "$CPP"
grep -q 'fasim_gasal2_flush_two_slot_overlap_shadow_runtime' "$CPP"
grep -q 'fasim_gasal2_flush_two_slot_overlap_runtime' "$CPP"
grep -q 'fasim_gasal2_flush_two_slot_overlap_validate_runtime' "$CPP"
grep -q 'fasim_gasal2_flush_two_slot_serialized_control_runtime' "$CPP"
grep -q 'fasim_gasal2_two_slot_observe_flush' "$CPP"
grep -q 'fasim_gasal2_two_slot_observe_extend_shape' "$CPP"
grep -q 'fasim_print_gasal2_flush_two_slot_overlap_stats' "$CPP"
grep -q 'two_slot_start_worker' "$CPP"
grep -q 'two_slot_submit_work' "$CPP"
grep -q 'two_slot_drain_pipeline' "$CPP"
grep -q 'FASIM_TWO_SLOT_CPU_FINALIZING' "$CPP"

for metric in \
  benchmark.fasim_gasal2_flush_two_slot_overlap_requested \
  benchmark.fasim_gasal2_flush_two_slot_overlap_active \
  benchmark.fasim_gasal2_flush_two_slot_overlap_validate_requested \
  benchmark.fasim_gasal2_flush_two_slot_overlap_validate_active \
  benchmark.fasim_gasal2_flush_two_slot_serialized_control_requested \
  benchmark.fasim_gasal2_flush_two_slot_serialized_control_active \
  benchmark.fasim_gasal2_flush_two_slot_overlap_disabled_reason \
  benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_observed \
  benchmark.fasim_gasal2_flush_two_slot_overlap_shape_observed_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_eligible_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_ineligible_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_result_object_ready_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_result_object_missing_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_convert_inside_extend_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_direct_convert_active_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_equivalence_first_convert_active_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_archive_first_convert_active_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_non_direct_convert_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_output_side_effect_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_triplex_return_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_gpu_submitted \
  benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_finalized \
  benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_committed \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_submit_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_submit_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_finalize_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_finalize_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_commit_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_commit_count \
  benchmark.fasim_gasal2_flush_two_slot_overlap_unsupported_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_legacy_fallback_flushes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_state_transition_violations \
  benchmark.fasim_gasal2_flush_two_slot_overlap_order_violations \
  benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported \
  benchmark.fasim_gasal2_flush_two_slot_overlap_overlap_fraction \
  benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_finalizer_covered_by_next_flush_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_producer_covered_by_finalizer_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_peak_live_bytes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_peak_live_bytes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_host_peak_bytes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_total_peak_live_bytes \
  benchmark.fasim_gasal2_flush_two_slot_overlap_max_live_slots \
  benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_0_live_slots_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_1_live_slot_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_2_live_slots_seconds \
  benchmark.fasim_gasal2_flush_two_slot_overlap_missing_rows \
  benchmark.fasim_gasal2_flush_two_slot_overlap_extra_rows \
  benchmark.fasim_gasal2_flush_two_slot_overlap_total_tasks \
  benchmark.fasim_gasal2_flush_two_slot_overlap_max_tasks_per_flush \
  benchmark.fasim_gasal2_flush_two_slot_overlap_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'two_slot_active_clean_no_fallback' "$CPP"
grep -q 'two_slot_serialized_control_clean_no_fallback' "$CPP"
grep -q 'validate_mode_synchronous_audit' "$CPP"
grep -q 'FasimGasal2FlushGpuResult' "$DOC"
grep -q 'FlushFinalizedRows' "$DOC"
grep -q 'FREE -> READY -> CPU_FINALIZING -> COMMIT_READY -> COMMITTING -> FREE' "$DOC"
grep -q 'gpu_cpu_overlap_seconds=unavailable' "$DOC"
grep -q 'host_scheduling_overlap_seconds=<measured>' "$DOC"
grep -q 'requires an NVTX/Nsight Systems profile' "$DOC"
grep -q 'check-fasim-gasal2-flush-two-slot-overlap-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-two-slot-overlap-smoke:' "$MAKEFILE"
grep -q 'characterize-fasim-gasal2-flush-two-slot-overlap-chr22:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-two-slot-overlap-chr22-result:' "$MAKEFILE"
grep -q 'characterize-fasim-gasal2-flush-two-slot-overlap-broader-matrix:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-two-slot-overlap-broader-matrix-result:' "$MAKEFILE"
grep -q 'characterize_fasim_gasal2_flush_two_slot_overlap_chr22.sh' "$MAKEFILE"
grep -q 'check_fasim_gasal2_flush_two_slot_overlap_chr22_result.sh' "$MAKEFILE"
grep -q 'characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix.sh' "$MAKEFILE"
grep -q 'check_fasim_gasal2_flush_two_slot_overlap_broader_matrix_result.sh' "$MAKEFILE"
grep -q 'MIN_TWO_SLOT_IMPROVEMENT' "$ROOT/scripts/check_fasim_gasal2_flush_two_slot_overlap_chr22_result.sh"
grep -q 'two_slot_wall_improvement_fraction_vs_extracted' "$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_overlap_chr22.sh"
grep -q 'two_slot_wall_improvement_fraction_vs_serialized' "$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_overlap_chr22.sh"
grep -q 'two_slot_serialized' "$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_overlap_chr22.sh"
grep -q 'schema_version' "$BROADER"
grep -q 'runtime_device_overlap_supported' "$BROADER"
grep -q 'host_scheduling_overlap_available' "$BROADER"
grep -q 'device_overlap_measurement' "$BROADER"
grep -q 'NSIGHT_WORKLOADS' "$BROADER"
grep -q 'WORKLOAD_SPECS' "$BROADER"
grep -q 'benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds unavailable' "$BROADER"
grep -q 'MIN_STRONG_GO_WORKLOADS' "$BROADER_CHECK"
grep -q 'runtime_device_overlap_supported' "$BROADER_CHECK"
grep -q 'cpu_finalizer_gpu_activity_overlap_seconds' "$BROADER_CHECK"

echo "check_fasim_gasal2_flush_two_slot_overlap_scaffold: ok"
