#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_chr22_slices"}"
RUN_20MB="${RUN_20MB:-0}"

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

run_gpu_score_direct() {
  local label="$1"
  local dna="$2"
  local out_dir="$WORK/$label"
  mkdir -p "$out_dir"
  local start_seconds
  local end_seconds
  start_seconds="$(date +%s)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    "$BIN" -f1 "$dna" -f2 "$ROOT/H19.fa" -r 0 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end_seconds="$(date +%s)"
  printf '%s\n' "$((end_seconds - start_seconds))" >"$out_dir/wall_seconds.txt"
}

run_gpu_score_direct "chr22_10m_20m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_20m.fa"
run_gpu_score_direct "chr22_20m_30m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_20m_30m.fa"
if [[ "$RUN_20MB" != "0" ]]; then
  run_gpu_score_direct "chr22_10m_30m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_30m.fa"
fi

{
  echo "label,wall_seconds,digest,lines,scoreinfos,traceback_requests,traceback_batches,gasal2_total_seconds,legacy_score_replacement_used,legacy_score_replacement_fallbacks"
  for label in chr22_10m_20m chr22_20m_30m chr22_10m_30m; do
    out_dir="$WORK/$label"
    if [[ ! -d "$out_dir" ]]; then
      continue
    fi
    out_path="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
    if [[ -z "$out_path" ]]; then
      echo "missing output for $label" >&2
      exit 1
    fi
    wall_seconds="$(cat "$out_dir/wall_seconds.txt")"
    digest="$(sha256sum "$out_path" | awk '{print $1}')"
    lines="$(wc -l < "$out_path")"
    scoreinfos="$(awk -F= '/^benchmark\.fasim_gasal2_longtarget_task_batch_scoreinfos=/{print $2}' "$out_dir/stderr.log")"
    traceback_requests="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_requests=/{print $2}' "$out_dir/stderr.log")"
    traceback_batches="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_batches=/{print $2}' "$out_dir/stderr.log")"
    gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$out_dir/stderr.log")"
    legacy_score_replacement_used="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=/{print $2}' "$out_dir/stderr.log")"
    legacy_score_replacement_fallbacks="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=/{print $2}' "$out_dir/stderr.log")"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$label" \
      "$wall_seconds" \
      "$digest" \
      "$lines" \
      "$scoreinfos" \
      "$traceback_requests" \
      "$traceback_batches" \
      "$gasal2_total_seconds" \
      "$legacy_score_replacement_used" \
      "$legacy_score_replacement_fallbacks"
  done
} >"$WORK/summary.csv"

cat "$WORK/summary.csv"
