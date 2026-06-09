#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_realpath_prototype"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

WORK="$WORK" \
BIN="$BIN" \
BUILD_BIN=0 \
EXTRA_SHADOW_ENV="FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1" \
EXPECTED_SCOREINFO_MISMATCHES=0 \
EXPECTED_DECISION=streaming_scoreinfo_shadow_active \
EXPECTED_LEGACY_BYTE_SHARED=1 \
EXPECTED_GPU_MINSCORE_REQUESTED=1 \
EXPECTED_GPU_MINSCORE_ACTIVE=1 \
EXPECTED_GPU_MINSCORE_HOT=1 \
  bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh"

stderr="$WORK/candidate/stderr.log"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested=1$' "$stderr"
grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used=[1-9][0-9]*$' "$stderr"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0$' "$stderr"
grep -q '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority=cpu_validated$' "$stderr"
