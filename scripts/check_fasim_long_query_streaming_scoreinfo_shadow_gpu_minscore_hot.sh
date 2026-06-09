#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore_hot"}"
BUILD_BIN="${BUILD_BIN:-1}"

WORK="$WORK" \
BIN="$BIN" \
BUILD_BIN="$BUILD_BIN" \
EXTRA_SHADOW_ENV="${EXTRA_SHADOW_ENV:-FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1}" \
EXPECTED_SCOREINFO_MISMATCHES=0 \
EXPECTED_DECISION=streaming_scoreinfo_shadow_active \
EXPECTED_LEGACY_BYTE_SHARED="${EXPECTED_LEGACY_BYTE_SHARED:-1}" \
EXPECTED_GPU_MINSCORE_REQUESTED="${EXPECTED_GPU_MINSCORE_REQUESTED:-1}" \
EXPECTED_GPU_MINSCORE_ACTIVE="${EXPECTED_GPU_MINSCORE_ACTIVE:-1}" \
EXPECTED_GPU_MINSCORE_HOT="${EXPECTED_GPU_MINSCORE_HOT:-1}" \
  bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh"

stderr="$WORK/candidate/stderr.log"
tasks="$(sed -n 's/^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks=//p' "$stderr" | tail -n 1)"
used="$(sed -n 's/^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used=//p' "$stderr" | tail -n 1)"
minscore_seconds="$(sed -n 's/^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds=//p' "$stderr" | tail -n 1)"
validation_minscore_seconds="$(sed -n 's/^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds=//p' "$stderr" | tail -n 1)"
if [[ -z "$tasks" || -z "$used" || "$used" != "$tasks" ]]; then
  echo "expected hot GPU minScore to be used for all tasks, got used=$used tasks=$tasks" >&2
  exit 1
fi
awk -v value="$minscore_seconds" 'BEGIN {
  if ((value + 0.0) > 0.05) {
    printf("expected hot-path minscore_seconds <= 0.05, got %s\n", value) > "/dev/stderr";
    exit 1;
  }
}'
awk -v value="$validation_minscore_seconds" 'BEGIN {
  if ((value + 0.0) <= 0.0) {
    printf("expected positive validation_minscore_seconds, got %s\n", value) > "/dev/stderr";
    exit 1;
  }
}'
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0$' "$stderr"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches=0$' "$stderr"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches=0$' "$stderr"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_error=none$' "$stderr"
