#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_dual_finalizer_scaffold.md"

grep -q 'FASIM_GASAL2_FLUSH_DUAL_FINALIZER_SHADOW' "$CPP"
grep -q 'struct FasimGasal2DualFinalizerStats' "$CPP"
grep -q 'fasim_gasal2_flush_dual_finalizer_shadow_runtime' "$CPP"
grep -q 'fasim_print_gasal2_dual_finalizer_stats' "$CPP"
grep -q 'fasim_gasal2_dual_finalizer_observe_ready' "$CPP"
grep -q 'fasim_gasal2_dual_finalizer_observe_legacy' "$CPP"
grep -q 'fasim_gasal2_dual_finalizer_compare' "$CPP"
grep -q 'FasimGasal2FlushFinalizedRows' "$CPP"
grep -q 'fasim_gasal2_make_triplex_finalized_rows' "$CPP"
grep -q 'unsupported_finalizer_shape' "$CPP"
grep -q 'go_extract_finalize_flush_next' "$CPP"
grep -q 'extracted_finalizer_missing' "$CPP"

for metric in \
  benchmark.fasim_gasal2_dual_finalizer_requested \
  benchmark.fasim_gasal2_dual_finalizer_active \
  benchmark.fasim_gasal2_dual_finalizer_disabled_reason \
  benchmark.fasim_gasal2_dual_finalizer_result_boundary_ready_flushes \
  benchmark.fasim_gasal2_dual_finalizer_flushes_observed \
  benchmark.fasim_gasal2_dual_finalizer_flushes_compared \
  benchmark.fasim_gasal2_dual_finalizer_unsupported_flushes \
  benchmark.fasim_gasal2_dual_finalizer_legacy_rows \
  benchmark.fasim_gasal2_dual_finalizer_extracted_rows \
  benchmark.fasim_gasal2_dual_finalizer_missing_rows \
  benchmark.fasim_gasal2_dual_finalizer_extra_rows \
  benchmark.fasim_gasal2_dual_finalizer_order_mismatches \
  benchmark.fasim_gasal2_dual_finalizer_cigar_mismatches \
  benchmark.fasim_gasal2_dual_finalizer_coordinate_mismatches \
  benchmark.fasim_gasal2_dual_finalizer_counter_mismatches \
  benchmark.fasim_gasal2_dual_finalizer_archive_descriptor_mismatches \
  benchmark.fasim_gasal2_dual_finalizer_legacy_seconds \
  benchmark.fasim_gasal2_dual_finalizer_extracted_seconds \
  benchmark.fasim_gasal2_dual_finalizer_compare_seconds \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_flush_id \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_task_id \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_row_index \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_field \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_legacy_row \
  benchmark.fasim_gasal2_dual_finalizer_first_mismatch_extracted_row \
  benchmark.fasim_gasal2_dual_finalizer_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'same FlushGpuResult' "$DOC"
grep -q 'FasimGasal2FlushFinalizedRows' "$DOC"
grep -q 'decision=go_real_ordered_commit_opt_in_next' "$DOC"
grep -q 'unsupported_finalizer_shape' "$DOC"
grep -q 'check-fasim-gasal2-flush-dual-finalizer-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-dual-finalizer-smoke:' "$MAKEFILE"

echo "check_fasim_gasal2_flush_dual_finalizer_scaffold: ok"
