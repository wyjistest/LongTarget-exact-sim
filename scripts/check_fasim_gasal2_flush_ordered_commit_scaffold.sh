#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
DOC="$ROOT/docs/fasim_gasal2_flush_ordered_commit_scaffold.md"

grep -q 'FASIM_GASAL2_FLUSH_ORDERED_COMMIT_SHADOW' "$CPP"
grep -q 'struct FasimGasal2OrderedCommitStats' "$CPP"
grep -q 'fasim_gasal2_flush_ordered_commit_shadow_runtime' "$CPP"
grep -q 'fasim_print_gasal2_ordered_commit_stats' "$CPP"
grep -q 'fasim_gasal2_ordered_commit_observe_ready' "$CPP"
grep -q 'fasim_gasal2_ordered_commit_observe_commit' "$CPP"
grep -q 'go_same_result_dual_finalizer_shadow_next' "$CPP"

for metric in \
  benchmark.fasim_gasal2_ordered_commit_requested \
  benchmark.fasim_gasal2_ordered_commit_active \
  benchmark.fasim_gasal2_ordered_commit_disabled_reason \
  benchmark.fasim_gasal2_ordered_commit_flushes_ready \
  benchmark.fasim_gasal2_ordered_commit_flushes_committed \
  benchmark.fasim_gasal2_ordered_commit_direct_flushes_committed \
  benchmark.fasim_gasal2_ordered_commit_triplex_flushes_committed \
  benchmark.fasim_gasal2_ordered_commit_order_violations \
  benchmark.fasim_gasal2_ordered_commit_precommit_rows \
  benchmark.fasim_gasal2_ordered_commit_appended_rows \
  benchmark.fasim_gasal2_ordered_commit_archive_records \
  benchmark.fasim_gasal2_ordered_commit_result_bytes_p50 \
  benchmark.fasim_gasal2_ordered_commit_result_bytes_p90 \
  benchmark.fasim_gasal2_ordered_commit_result_bytes_max \
  benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p50 \
  benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p90 \
  benchmark.fasim_gasal2_ordered_commit_traceback_bytes_max \
  benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback \
  benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p50 \
  benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p90 \
  benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_max \
  benchmark.fasim_gasal2_ordered_commit_projected_two_slot_peak_bytes \
  benchmark.fasim_gasal2_ordered_commit_finalize_seconds \
  benchmark.fasim_gasal2_ordered_commit_write_task_seconds \
  benchmark.fasim_gasal2_ordered_commit_archive_seconds \
  benchmark.fasim_gasal2_ordered_commit_counter_seconds \
  benchmark.fasim_gasal2_ordered_commit_total_seconds \
  benchmark.fasim_gasal2_ordered_commit_missing_rows \
  benchmark.fasim_gasal2_ordered_commit_extra_rows \
  benchmark.fasim_gasal2_ordered_commit_cigar_mismatches \
  benchmark.fasim_gasal2_ordered_commit_counter_mismatches \
  benchmark.fasim_gasal2_ordered_commit_digest_mismatches \
  benchmark.fasim_gasal2_ordered_commit_decision
do
  grep -q "$metric" "$CPP"
  grep -q "$metric" "$DOC"
done

grep -q 'FlushGpuResult' "$DOC"
grep -q 'precommit rows' "$DOC"
grep -q 'projected_two_slot_peak_bytes' "$DOC"
grep -q 'check-fasim-gasal2-flush-ordered-commit-scaffold:' "$MAKEFILE"
grep -q 'check-fasim-gasal2-flush-ordered-commit-smoke:' "$MAKEFILE"

echo "check_fasim_gasal2_flush_ordered_commit_scaffold: ok"
