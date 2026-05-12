#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-}"
STDERR_LOG="${STDERR_LOG:-}"

if [ -z "$STDERR_LOG" ]; then
  if [ -z "$OUTPUT_SUBDIR" ]; then
    echo "set STDERR_LOG or OUTPUT_SUBDIR" >&2
    exit 1
  fi
  STDERR_LOG="$ROOT_DIR/.tmp/$OUTPUT_SUBDIR/stderr.log"
fi

if [ ! -f "$STDERR_LOG" ]; then
  echo "missing stderr log: $STDERR_LOG" >&2
  exit 1
fi

EXPECTED_ACTIVE="${EXPECTED_ACTIVE:-1}"
EXPECTED_DISABLED_REASON="${EXPECTED_DISABLED_REASON:-none}"
EXPECTED_SELECTION_MODE="${EXPECTED_SELECTION_MODE:-}"
EXPECTED_REQUEST_INDEX="${EXPECTED_REQUEST_INDEX:-}"
EXPECTED_MAX_REQUESTS="${EXPECTED_MAX_REQUESTS:-}"
EXPECTED_REQUESTS_SELECTED="${EXPECTED_REQUESTS_SELECTED:-}"
EXPECTED_REQUESTS_SKIPPED="${EXPECTED_REQUESTS_SKIPPED:-}"
EXPECTED_REQUESTS_COMPARED="${EXPECTED_REQUESTS_COMPARED:?set EXPECTED_REQUESTS_COMPARED}"
EXPECTED_SELECTION_INVALID="${EXPECTED_SELECTION_INVALID:-0}"
EXPECTED_SELECTION_DISABLED_REASON="${EXPECTED_SELECTION_DISABLED_REASON:-none}"
EXPECTED_RESIDENT_SOURCE_REQUESTED="${EXPECTED_RESIDENT_SOURCE_REQUESTED:-}"
EXPECTED_RESIDENT_SOURCE_ACTIVE="${EXPECTED_RESIDENT_SOURCE_ACTIVE:-}"
EXPECTED_RESIDENT_SOURCE_SUPPORTED="${EXPECTED_RESIDENT_SOURCE_SUPPORTED:-}"
EXPECTED_RESIDENT_SOURCE_DISABLED_REASON="${EXPECTED_RESIDENT_SOURCE_DISABLED_REASON:-}"
EXPECTED_SUMMARY_H2D_ELIDED="${EXPECTED_SUMMARY_H2D_ELIDED:-}"
EXPECTED_INPUT_SOURCE="${EXPECTED_INPUT_SOURCE:-}"
EXPECTED_RESIDENT_SOURCE_FALLBACKS="${EXPECTED_RESIDENT_SOURCE_FALLBACKS:-}"

require_metric_gt_zero() {
  metric="$1"
  value="$(sed -n "s/^benchmark\\.$metric=//p" "$STDERR_LOG" | tail -n 1)"
  if [ -z "$value" ] || ! awk "BEGIN { exit !($value > 0) }"; then
    echo "expected benchmark.$metric > 0, got '${value:-missing}'" >&2
    exit 1
  fi
}

grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_requested=1$' "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_active=$EXPECTED_ACTIVE$" "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_authority=cpu$' "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_disabled_reason=$EXPECTED_DISABLED_REASON$" "$STDERR_LOG"

if [ -n "$EXPECTED_SELECTION_MODE" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_selection_mode=$EXPECTED_SELECTION_MODE$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_REQUEST_INDEX" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_requested_request_index=$EXPECTED_REQUEST_INDEX$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_MAX_REQUESTS" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_requested_max_requests=$EXPECTED_MAX_REQUESTS$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_REQUESTS_SELECTED" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_requests_selected=$EXPECTED_REQUESTS_SELECTED$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_REQUESTS_SKIPPED" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_requests_skipped=$EXPECTED_REQUESTS_SKIPPED$" "$STDERR_LOG"
fi

grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_selection_invalid=$EXPECTED_SELECTION_INVALID$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_selection_disabled_reason=$EXPECTED_SELECTION_DISABLED_REASON$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_requests_compared=$EXPECTED_REQUESTS_COMPARED$" "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_requests_mismatched=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_candidate_digest_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_candidate_value_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_min_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_first_max_tie_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_safe_store_digest_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_total_mismatches=0$' "$STDERR_LOG"

if [ -n "$EXPECTED_RESIDENT_SOURCE_REQUESTED" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_resident_source_requested=$EXPECTED_RESIDENT_SOURCE_REQUESTED$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_RESIDENT_SOURCE_ACTIVE" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_resident_source_active=$EXPECTED_RESIDENT_SOURCE_ACTIVE$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_RESIDENT_SOURCE_SUPPORTED" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_resident_source_supported=$EXPECTED_RESIDENT_SOURCE_SUPPORTED$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_RESIDENT_SOURCE_DISABLED_REASON" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_resident_source_disabled_reason=$EXPECTED_RESIDENT_SOURCE_DISABLED_REASON$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_SUMMARY_H2D_ELIDED" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_summary_h2d_elided=$EXPECTED_SUMMARY_H2D_ELIDED$" "$STDERR_LOG"
fi
if [ "$EXPECTED_SUMMARY_H2D_ELIDED" = "1" ]; then
  require_metric_gt_zero sim_initial_exact_frontier_per_request_shadow_summary_h2d_bytes_saved
fi
if [ -n "$EXPECTED_INPUT_SOURCE" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_input_source=$EXPECTED_INPUT_SOURCE$" "$STDERR_LOG"
fi
if [ -n "$EXPECTED_RESIDENT_SOURCE_FALLBACKS" ]; then
  grep -Eq "^benchmark\\.sim_initial_exact_frontier_per_request_shadow_fallbacks=$EXPECTED_RESIDENT_SOURCE_FALLBACKS$" "$STDERR_LOG"
fi
if [ "$EXPECTED_ACTIVE" = "1" ]; then
  require_metric_gt_zero sim_initial_exact_frontier_per_request_shadow_kernel_seconds
  require_metric_gt_zero sim_initial_exact_frontier_per_request_shadow_compare_seconds
fi

grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_contract_level=candidate_safe_store$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_contract_candidate_supported=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_contract_safe_store_supported=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_contract_epoch_supported=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_full_contract_supported=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_exact_frontier_per_request_shadow_full_contract_disabled_reason=missing_epoch_contract$' "$STDERR_LOG"
