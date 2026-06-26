#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_result_boundary_scaffold.md"

grep -q 'FASIM_GASAL2_FLUSH_RESULT_BOUNDARY_SHADOW' "$CPP"
grep -q 'struct FasimGasal2FlushGpuResult' "$CPP"
grep -q 'struct FasimGasal2FlushResultBoundaryStats' "$CPP"
grep -q 'fasim_gasal2_flush_result_boundary_shadow_runtime' "$CPP"
grep -q 'fasim_print_gasal2_flush_result_boundary_stats' "$CPP"
grep -q 'go_pure_finalizer_extraction_next' "$CPP"
grep -q 'finalizerSelectedByTask' "$CPP"
grep -q 'flushGpuResult.selected_by_task' "$CPP"

for metric in \
  benchmark.fasim_gasal2_flush_result_boundary_requested \
  benchmark.fasim_gasal2_flush_result_boundary_active \
  benchmark.fasim_gasal2_flush_result_boundary_disabled_reason \
  benchmark.fasim_gasal2_flush_result_boundary_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_materialized_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_finalizer_consumed_result_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_task_backing_owned_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_score_group_mapping_owned_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_selected_by_task_owned_flushes \
  benchmark.fasim_gasal2_flush_result_boundary_task_count \
  benchmark.fasim_gasal2_flush_result_boundary_score_groups \
  benchmark.fasim_gasal2_flush_result_boundary_selected_alignments \
  benchmark.fasim_gasal2_flush_result_boundary_result_bytes \
  benchmark.fasim_gasal2_flush_result_boundary_traceback_bytes \
  benchmark.fasim_gasal2_flush_result_boundary_result_bytes_includes_traceback \
  benchmark.fasim_gasal2_flush_result_boundary_materialize_seconds \
  benchmark.fasim_gasal2_flush_result_boundary_cigar_seconds \
  benchmark.fasim_gasal2_flush_result_boundary_finalize_seconds \
  benchmark.fasim_gasal2_flush_result_boundary_commit_seconds \
  benchmark.fasim_gasal2_flush_result_boundary_rows_compared \
  benchmark.fasim_gasal2_flush_result_boundary_missing_rows \
  benchmark.fasim_gasal2_flush_result_boundary_extra_rows \
  benchmark.fasim_gasal2_flush_result_boundary_cigar_mismatches \
  benchmark.fasim_gasal2_flush_result_boundary_digest_mismatches \
  benchmark.fasim_gasal2_flush_result_boundary_result_digest \
  benchmark.fasim_gasal2_flush_result_boundary_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'finalize_flush(result) -> FlushFinalizedRows' "$DOC"
grep -q 'commit_flush(flush_id, rows)' "$DOC"
grep -q 'FREE -> GPU_SUBMITTED -> GPU_READY -> CPU_FINALIZING -> COMMIT_READY -> COMMITTED -> FREE' "$DOC"
grep -q 'check-fasim-gasal2-flush-result-boundary-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-result-boundary-smoke:' "$MAKEFILE"

echo "check_fasim_gasal2_flush_result_boundary_scaffold: ok"
