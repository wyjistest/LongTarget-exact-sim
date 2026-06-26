#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_extracted_finalizer_real_opt_in.md"

grep -q 'FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER' "$CPP"
grep -q 'FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE' "$CPP"
grep -q 'struct FasimGasal2ExtractedFinalizerStats' "$CPP"
grep -q 'fasim_gasal2_flush_extracted_finalizer_runtime' "$CPP"
grep -q 'fasim_gasal2_flush_extracted_finalizer_validate_runtime' "$CPP"
grep -q 'fasim_print_gasal2_extracted_finalizer_stats' "$CPP"
grep -q 'fasim_gasal2_extracted_finalizer_observe_ready' "$CPP"
grep -q 'fasim_gasal2_extracted_finalizer_observe_unsupported' "$CPP"
grep -q 'fasim_gasal2_extracted_finalizer_observe_commit' "$CPP"
grep -q 'fasim_gasal2_extracted_finalizer_compare' "$CPP"
grep -q 'buildExtractedTriplexesByTask' "$CPP"
grep -q 'direct_archive_finalizer_unsupported' "$CPP"
grep -q 'result_bytes_includes_traceback=1' "$CPP"
grep -q 'real_extracted_active_clean_no_fallback' "$CPP"
grep -q 'real_extracted_active_with_legacy_fallback' "$CPP"
grep -q 'validate_mismatch_fallback' "$CPP"
grep -q 'unsupported_shape_legacy_fallback' "$CPP"

for metric in \
  benchmark.fasim_gasal2_extracted_finalizer_requested \
  benchmark.fasim_gasal2_extracted_finalizer_active \
  benchmark.fasim_gasal2_extracted_finalizer_validate_requested \
  benchmark.fasim_gasal2_extracted_finalizer_validate_active \
  benchmark.fasim_gasal2_extracted_finalizer_disabled_reason \
  benchmark.fasim_gasal2_extracted_finalizer_result_boundary_ready_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_flushes_observed \
  benchmark.fasim_gasal2_extracted_finalizer_eligible_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_committed_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_legacy_fallback_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_legacy_finalizer_executed \
  benchmark.fasim_gasal2_extracted_finalizer_extracted_finalizer_executed \
  benchmark.fasim_gasal2_extracted_finalizer_comparison_performed \
  benchmark.fasim_gasal2_extracted_finalizer_extracted_active_flushes \
  benchmark.fasim_gasal2_extracted_finalizer_legacy_rows \
  benchmark.fasim_gasal2_extracted_finalizer_extracted_rows \
  benchmark.fasim_gasal2_extracted_finalizer_committed_rows \
  benchmark.fasim_gasal2_extracted_finalizer_missing_rows \
  benchmark.fasim_gasal2_extracted_finalizer_extra_rows \
  benchmark.fasim_gasal2_extracted_finalizer_order_mismatches \
  benchmark.fasim_gasal2_extracted_finalizer_cigar_mismatches \
  benchmark.fasim_gasal2_extracted_finalizer_coordinate_mismatches \
  benchmark.fasim_gasal2_extracted_finalizer_counter_mismatches \
  benchmark.fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches \
  benchmark.fasim_gasal2_extracted_finalizer_legacy_seconds \
  benchmark.fasim_gasal2_extracted_finalizer_extracted_seconds \
  benchmark.fasim_gasal2_extracted_finalizer_compare_seconds \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_flush_id \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_task_id \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_row_index \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_field \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_legacy_row \
  benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_extracted_row \
  benchmark.fasim_gasal2_extracted_finalizer_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'same `FlushGpuResult`' "$DOC"
grep -q 'validate_active=0' "$DOC"
grep -q 'unsupported_finalizer_shape' "$DOC"
grep -q 'check-fasim-gasal2-flush-extracted-finalizer-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-extracted-finalizer-smoke:' "$MAKEFILE"
grep -q 'characterize-fasim-gasal2-flush-extracted-finalizer-chr22:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-extracted-finalizer-chr22-result:' "$MAKEFILE"
grep -q 'characterize_fasim_gasal2_flush_extracted_finalizer_chr22.sh' "$MAKEFILE"
grep -q 'check_fasim_gasal2_flush_extracted_finalizer_chr22_result.sh' "$MAKEFILE"
grep -q 'MAX_EXTRACTED_OVERHEAD' "$ROOT/scripts/check_fasim_gasal2_flush_extracted_finalizer_chr22_result.sh"
grep -q 'runs.tsv' "$ROOT/scripts/characterize_fasim_gasal2_flush_extracted_finalizer_chr22.sh"
grep -q 'topk_compare.tsv' "$ROOT/scripts/characterize_fasim_gasal2_flush_extracted_finalizer_chr22.sh"
grep -q 'chr22 Characterization' "$DOC"

echo "check_fasim_gasal2_flush_extracted_finalizer_scaffold: ok"
