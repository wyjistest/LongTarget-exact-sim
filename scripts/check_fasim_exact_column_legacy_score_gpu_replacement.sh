#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_exact_column_legacy_score_gpu_replacement"}"
DNA="${DNA:-"$ROOT/testDNA.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

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
mkdir -p "$WORK/baseline" "$WORK/replacement" "$WORK/transfer_table_off"

run_case() {
  local out_dir="$1"
  shift
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline" \
  FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=0
run_case "$WORK/replacement"
run_case "$WORK/transfer_table_off" \
  FASIM_TRANSFERSTRING_TABLE=0

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
replacement_out="$(find "$WORK/replacement" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
transfer_table_off_out="$(find "$WORK/transfer_table_off" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$replacement_out" || -z "$transfer_table_off_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

cmp -s "$baseline_out" "$replacement_out"
cmp -s "$replacement_out" "$transfer_table_off_out"

grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_enabled=1$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_transfer_string_table_enabled=1$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_transfer_string_table_enabled=0$' "$WORK/transfer_table_off/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_enabled=1$' "$WORK/transfer_table_off/stderr.log"
grep -Eq '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=[1-9][0-9]*$' "$WORK/transfer_table_off/stderr.log"
if grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_enabled=1$' "$WORK/baseline/stderr.log"; then
  echo "baseline unexpectedly enabled legacy score GPU replacement" >&2
  exit 1
fi
grep -q '^benchmark\.fasim_transfer_string_table_enabled=1$' "$WORK/baseline/stderr.log"
awk -F= '/^benchmark\.fasim_top5_gasal2_phase_exact_min_score_seconds=/ { if ($2 + 0 > 0) found=1 } END { exit found ? 0 : 1 }' "$WORK/baseline/stderr.log"
grep -Eq '^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_requests=[1-9][0-9]*$' "$WORK/replacement/stderr.log"
grep -Eq '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=[1-9][0-9]*$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=0$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_mismatches=0$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_min_score_mismatches=0$' "$WORK/replacement/stderr.log"
grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_min_score_seconds=0$' "$WORK/replacement/stderr.log"

baseline_digest="$(sha256sum "$baseline_out" | awk '{print $1}')"
replacement_digest="$(sha256sum "$replacement_out" | awk '{print $1}')"
replacement_used="$(sed -n 's/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=//p' "$WORK/replacement/stderr.log")"
requests="$(sed -n 's/^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_requests=//p' "$WORK/replacement/stderr.log")"
gpu_wall="$(sed -n 's/^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_wall_seconds=//p' "$WORK/replacement/stderr.log")"

printf 'baseline_digest=%s\n' "$baseline_digest"
printf 'replacement_digest=%s\n' "$replacement_digest"
printf 'requests=%s\n' "$requests"
printf 'replacement_used=%s\n' "$replacement_used"
printf 'gpu_legacy_score_wall_seconds=%s\n' "$gpu_wall"
echo "ok"
