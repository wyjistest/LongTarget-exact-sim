#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_pure_finalizer_scaffold.md"

grep -q 'FASIM_GASAL2_FLUSH_PURE_FINALIZER_SHADOW' "$CPP"
grep -q 'struct FasimGasal2FlushPureFinalizerStats' "$CPP"
grep -q 'fasim_gasal2_flush_pure_finalizer_shadow_runtime' "$CPP"
grep -q 'fasim_print_gasal2_flush_pure_finalizer_stats' "$CPP"
grep -q 'go_ordered_commit_extraction_next' "$CPP"
grep -q 'ordered_commit_not_extracted' "$CPP"
grep -q 'directRowsByTask' "$CPP"
grep -q 'triplexesByTask' "$CPP"

for metric in \
  benchmark.fasim_gasal2_flush_pure_finalizer_requested \
  benchmark.fasim_gasal2_flush_pure_finalizer_active \
  benchmark.fasim_gasal2_flush_pure_finalizer_disabled_reason \
  benchmark.fasim_gasal2_flush_pure_finalizer_flushes_observed \
  benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_ready_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_missing_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_eligible_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_ineligible_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_local_rows_ready_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_direct_rows_local_ready_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_triplex_rows_local_ready_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_output_side_effect_blocker_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_archive_writer_blocker_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_global_task_triplex_commit_blocker_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_telemetry_global_counter_blocker_flushes \
  benchmark.fasim_gasal2_flush_pure_finalizer_precommit_rows \
  benchmark.fasim_gasal2_flush_pure_finalizer_rows_compared \
  benchmark.fasim_gasal2_flush_pure_finalizer_missing_rows \
  benchmark.fasim_gasal2_flush_pure_finalizer_extra_rows \
  benchmark.fasim_gasal2_flush_pure_finalizer_cigar_mismatches \
  benchmark.fasim_gasal2_flush_pure_finalizer_digest_mismatches \
  benchmark.fasim_gasal2_flush_pure_finalizer_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'finalize_flush(result) -> FlushFinalizedRows' "$DOC"
grep -q 'commit_flush(flush_id, rows)' "$DOC"
grep -q 'decision=go_ordered_commit_extraction_next' "$DOC"
grep -q 'check-fasim-gasal2-flush-pure-finalizer-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-pure-finalizer-smoke:' "$MAKEFILE"

echo "check_fasim_gasal2_flush_pure_finalizer_scaffold: ok"
