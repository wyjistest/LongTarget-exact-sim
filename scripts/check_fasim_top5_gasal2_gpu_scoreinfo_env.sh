#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="$ROOT/.tmp/check_fasim_top5_gasal2_gpu_scoreinfo_env"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK"
strings "$BIN" >"$WORK/strings.txt"

grep -q 'FASIM_TOP5_GASAL2_GPU_SCOREINFO' "$WORK/strings.txt"
grep -q 'FASIM_TOP5_GASAL2_PHASE_TIMING' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_gpu_scoreinfo_requested' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_gpu_scoreinfo_active' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_phase_exact_scoreinfo_build_seconds' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_phase_transfer_string_seconds' "$WORK/strings.txt"
grep -q 'fasim_transfer_string_table_enabled' "$WORK/strings.txt"
grep -q 'FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU' "$WORK/strings.txt"
grep -q 'fasim_exact_column_legacy_score_gpu_replacement_enabled' "$WORK/strings.txt"
grep -q 'fasim_exact_column_legacy_score_gpu_replacement_used' "$WORK/strings.txt"
grep -q 'fasim_exact_column_legacy_score_gpu_replacement_fallbacks' "$WORK/strings.txt"
grep -q 'FASIM_ALIGN_GASAL2_SCORE_PREPASS' "$WORK/strings.txt"
grep -q 'fasim_gasal2_score_prepass_enabled' "$WORK/strings.txt"
grep -q 'FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS' "$WORK/strings.txt"
grep -q 'fasim_gasal2_staged_score_prepass_enabled' "$WORK/strings.txt"
grep -q 'FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE' "$WORK/strings.txt"
grep -q 'fasim_gasal2_staged_score_prepass_pruned_best_fallback_groups' "$WORK/strings.txt"
grep -q 'fasim_gasal2_staged_score_prepass_pruned_remaining_requests' "$WORK/strings.txt"
grep -q 'FASIM_ALIGN_GASAL2_MAX_QUERY_LEN' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_phase_gasal2_query_preflight_supported' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_phase_gasal2_query_preflight_query_len' "$WORK/strings.txt"
grep -q 'fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len' "$WORK/strings.txt"
grep -q 'fasim_gasal2_length_guard_fallbacks' "$WORK/strings.txt"
grep -q 'fasim_gasal2_length_guard_last_query_len' "$WORK/strings.txt"
grep -q 'fasim_gasal2_length_guard_max_query_len' "$WORK/strings.txt"
grep -q 'fasim_gasal2_score_query_bytes' "$WORK/strings.txt"
grep -q 'fasim_gasal2_traceback_query_bytes' "$WORK/strings.txt"
grep -q 'fasim_gasal2_traceback_query_reuse_potential_saved_bytes' "$WORK/strings.txt"
grep -q 'FASIM_GPU_DP_COLUMN_AUTO' "$WORK/strings.txt"
grep -q 'FASIM_EXACT_COLUMN_EXTEND_BATCH' "$WORK/strings.txt"
grep -q 'FASIM_TRANSFERSTRING_TABLE' "$WORK/strings.txt"
grep -q 'FASIM_ALIGN_GASAL2' "$WORK/strings.txt"

echo "ok"
