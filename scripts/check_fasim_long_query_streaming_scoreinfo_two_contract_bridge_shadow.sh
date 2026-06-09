#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_shadow"}"
BUILD_BIN="${BUILD_BIN:-1}"

WORK="$WORK" \
BIN="$BIN" \
BUILD_BIN="$BUILD_BIN" \
EXTRA_SHADOW_ENV="FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1" \
EXPECTED_SCOREINFO_MISMATCHES=0 \
EXPECTED_DECISION=two_contract_bridge_shadow_active \
EXPECTED_LEGACY_BYTE_SHARED=1 \
EXPECTED_GPU_MINSCORE_REQUESTED=1 \
EXPECTED_GPU_MINSCORE_ACTIVE=1 \
  bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh"

stderr="$WORK/candidate/stderr.log"
metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1
}

tasks="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
two_requested="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested)"
two_active="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active)"
two_used="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used)"
two_fallbacks="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks)"
two_score_mismatches="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches)"
two_min_score_mismatches="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches)"
two_scoreinfo_mismatches="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches)"
two_total_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds)"
two_h2d_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds)"
two_kernel_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds)"
two_d2h_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds)"
two_error="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_error)"
fused_requested="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested)"
decision="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"

for value_name in \
  tasks two_requested two_active two_used two_fallbacks \
  two_score_mismatches two_min_score_mismatches two_scoreinfo_mismatches \
  two_total_seconds two_h2d_seconds two_kernel_seconds two_d2h_seconds \
  two_error fused_requested decision; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing two-contract bridge shadow metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$two_requested" != "1" || "$two_active" != "1" ]]; then
  echo "expected two-contract requested=1 active=1, got requested=$two_requested active=$two_active" >&2
  exit 1
fi
if [[ "$two_used" != "$tasks" ]]; then
  echo "expected two-contract used to equal tasks, got used=$two_used tasks=$tasks" >&2
  exit 1
fi
if [[ "$two_fallbacks" != "0" ||
      "$two_score_mismatches" != "0" ||
      "$two_min_score_mismatches" != "0" ||
      "$two_scoreinfo_mismatches" != "0" ]]; then
  echo "expected clean two-contract shadow, got fallbacks=$two_fallbacks score=$two_score_mismatches min_score=$two_min_score_mismatches scoreinfo=$two_scoreinfo_mismatches" >&2
  exit 1
fi
if [[ "$two_error" != "none" || "$decision" != "two_contract_bridge_shadow_active" ]]; then
  echo "expected clean two-contract decision/error, got decision=$decision error=$two_error" >&2
  exit 1
fi
if [[ "$fused_requested" != "0" ]]; then
  echo "two-contract bridge shadow must not use fused minScore, got fused_requested=$fused_requested" >&2
  exit 1
fi

for timing_name in two_total_seconds two_kernel_seconds; do
  timing_value="${!timing_name}"
  awk -v name="$timing_name" -v value="$timing_value" 'BEGIN {
    if ((value + 0.0) <= 0.0) {
      printf("expected positive %s, got %s\n", name, value) > "/dev/stderr";
      exit 1;
    }
  }'
done
for timing_name in two_h2d_seconds two_d2h_seconds; do
  timing_value="${!timing_name}"
  awk -v name="$timing_name" -v value="$timing_value" 'BEGIN {
    if ((value + 0.0) < 0.0) {
      printf("expected nonnegative %s, got %s\n", name, value) > "/dev/stderr";
      exit 1;
    }
  }'
done

printf 'two_contract requested=%s active=%s used=%s fallbacks=%s\n' \
  "$two_requested" "$two_active" "$two_used" "$two_fallbacks"
printf 'two_contract score_mismatches=%s min_score_mismatches=%s scoreinfo_mismatches=%s\n' \
  "$two_score_mismatches" "$two_min_score_mismatches" "$two_scoreinfo_mismatches"
printf 'two_contract total_seconds=%s h2d_seconds=%s kernel_seconds=%s d2h_seconds=%s error=%s\n' \
  "$two_total_seconds" "$two_h2d_seconds" "$two_kernel_seconds" "$two_d2h_seconds" "$two_error"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
