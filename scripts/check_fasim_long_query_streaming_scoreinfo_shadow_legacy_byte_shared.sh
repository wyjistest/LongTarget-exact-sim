#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_shadow_legacy_byte_shared"}"
BUILD_BIN="${BUILD_BIN:-1}"

WORK="$WORK" \
BIN="$BIN" \
BUILD_BIN="$BUILD_BIN" \
EXTRA_SHADOW_ENV="FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1" \
EXPECTED_SCOREINFO_MISMATCHES=0 \
EXPECTED_DECISION=streaming_scoreinfo_shadow_active \
EXPECTED_LEGACY_BYTE_SHARED=1 \
  bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh"
