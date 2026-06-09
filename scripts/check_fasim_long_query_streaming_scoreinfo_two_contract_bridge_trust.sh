#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust"}"
BUILD_BIN="${BUILD_BIN:-1}"

WORK="$WORK" \
BIN="$BIN" \
BUILD_BIN="$BUILD_BIN" \
EXTRA_SHADOW_ENV="FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1" \
EXPECTED_SCOREINFO_MISMATCHES=0 \
EXPECTED_DECISION=two_contract_bridge_trust_active \
EXPECTED_LEGACY_BYTE_SHARED=1 \
EXPECTED_GPU_MINSCORE_REQUESTED=1 \
EXPECTED_GPU_MINSCORE_ACTIVE=1 \
EXPECTED_GPU_MINSCORE_HOT=1 \
EXPECTED_CPU_SCOREINFO_GROUPS=0 \
EXPECTED_CPU_PREALIGN_SECONDS=0 \
EXPECTED_COMPARE_SECONDS=0 \
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
two_error="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_error)"
realpath_requested="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested)"
realpath_trust="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust)"
realpath_used="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used)"
realpath_fallbacks="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks)"
realpath_digest_authority="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority)"
cpu_scoreinfo_groups="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups)"
cpu_prealign_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds)"
compare_seconds="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds)"
decision="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"

for value_name in \
  tasks two_requested two_active two_used two_fallbacks \
  two_score_mismatches two_min_score_mismatches two_scoreinfo_mismatches two_error \
  realpath_requested realpath_trust realpath_used realpath_fallbacks \
  realpath_digest_authority cpu_scoreinfo_groups cpu_prealign_seconds \
  compare_seconds decision; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing two-contract bridge trust metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$two_requested" != "1" || "$two_active" != "1" || "$two_used" != "$tasks" ]]; then
  echo "expected active two-contract trust bridge, got requested=$two_requested active=$two_active used=$two_used tasks=$tasks" >&2
  exit 1
fi
if [[ "$two_fallbacks" != "0" ||
      "$two_score_mismatches" != "0" ||
      "$two_min_score_mismatches" != "0" ||
      "$two_scoreinfo_mismatches" != "0" ||
      "$two_error" != "none" ]]; then
  echo "expected clean two-contract trust bridge, got fallbacks=$two_fallbacks score=$two_score_mismatches min_score=$two_min_score_mismatches scoreinfo=$two_scoreinfo_mismatches error=$two_error" >&2
  exit 1
fi
if [[ "$realpath_requested" != "1" ||
      "$realpath_trust" != "1" ||
      "$realpath_used" != "$tasks" ||
      "$realpath_fallbacks" != "0" ||
      "$realpath_digest_authority" != "external_digest_gate" ]]; then
  echo "expected two-contract trust to feed realpath, got requested=$realpath_requested trust=$realpath_trust used=$realpath_used tasks=$tasks fallbacks=$realpath_fallbacks authority=$realpath_digest_authority" >&2
  exit 1
fi
if [[ "$cpu_scoreinfo_groups" != "0" ||
      "$cpu_prealign_seconds" != "0" ||
      "$compare_seconds" != "0" ]]; then
  echo "expected trust mode to skip CPU scoreInfo validation, got cpu_groups=$cpu_scoreinfo_groups cpu_prealign=$cpu_prealign_seconds compare=$compare_seconds" >&2
  exit 1
fi
if [[ "$decision" != "two_contract_bridge_trust_active" ]]; then
  echo "expected two_contract_bridge_trust_active decision, got $decision" >&2
  exit 1
fi

printf 'two_contract_trust requested=%s active=%s used=%s fallbacks=%s\n' \
  "$two_requested" "$two_active" "$two_used" "$two_fallbacks"
printf 'two_contract_trust realpath_requested=%s realpath_trust=%s realpath_used=%s authority=%s\n' \
  "$realpath_requested" "$realpath_trust" "$realpath_used" "$realpath_digest_authority"
printf 'two_contract_trust cpu_scoreinfo_groups=%s cpu_prealign_seconds=%s compare_seconds=%s\n' \
  "$cpu_scoreinfo_groups" "$cpu_prealign_seconds" "$compare_seconds"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
