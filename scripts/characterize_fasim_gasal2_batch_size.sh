#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_batch_size"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
BATCH_SIZES="${BATCH_SIZES:-1000 2500 5000 10000 20000}"

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

summary="$WORK/summary.csv"
echo "batch_size,effective_batch_size,score_prepass_enabled,wall_seconds,digest,lines,gasal2_batches,score_batches,traceback_batches,score_requests,traceback_requests,gasal2_wait_seconds,score_wait_seconds,traceback_wait_seconds,gasal2_fill_seconds,gasal2_total_seconds,gasal2_extend_wall_seconds,transfer_string_seconds,replacement_used,replacement_fallbacks" >"$summary"

for batch_size in $BATCH_SIZES; do
  out_dir="$WORK/batch_${batch_size}"
  mkdir -p "$out_dir"
  start_seconds="$(date +%s)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_ALIGN_GASAL2_BATCH="$batch_size" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end_seconds="$(date +%s)"

  out_path="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_path" ]]; then
    echo "missing output for batch size $batch_size" >&2
    exit 1
  fi

  wall_seconds="$((end_seconds - start_seconds))"
  digest="$(sha256sum "$out_path" | awk '{print $1}')"
  lines="$(wc -l < "$out_path")"
  effective_batch_size="$(awk -F= '/^benchmark\.fasim_gasal2_effective_batch_size=/{print $2}' "$out_dir/stderr.log")"
  score_prepass_enabled="$(awk -F= '/^benchmark\.fasim_gasal2_score_prepass_enabled=/{print $2}' "$out_dir/stderr.log")"
  gasal2_batches="$(awk -F= '/^benchmark\.fasim_gasal2_batches=/{print $2}' "$out_dir/stderr.log")"
  score_batches="$(awk -F= '/^benchmark\.fasim_gasal2_score_batches=/{print $2}' "$out_dir/stderr.log")"
  traceback_batches="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_batches=/{print $2}' "$out_dir/stderr.log")"
  score_requests="$(awk -F= '/^benchmark\.fasim_gasal2_score_requests=/{print $2}' "$out_dir/stderr.log")"
  traceback_requests="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_requests=/{print $2}' "$out_dir/stderr.log")"
  gasal2_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  score_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_score_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  traceback_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  gasal2_fill_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_fill_seconds=/{print $2}' "$out_dir/stderr.log")"
  gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$out_dir/stderr.log")"
  gasal2_extend_wall_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds=/{print $2}' "$out_dir/stderr.log")"
  transfer_string_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_transfer_string_seconds=/{print $2}' "$out_dir/stderr.log")"
  replacement_used="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=/{print $2}' "$out_dir/stderr.log")"
  replacement_fallbacks="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=/{print $2}' "$out_dir/stderr.log")"

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$batch_size" \
    "$effective_batch_size" \
    "$score_prepass_enabled" \
    "$wall_seconds" \
    "$digest" \
    "$lines" \
    "$gasal2_batches" \
    "$score_batches" \
    "$traceback_batches" \
    "$score_requests" \
    "$traceback_requests" \
    "$gasal2_wait_seconds" \
    "$score_wait_seconds" \
    "$traceback_wait_seconds" \
    "$gasal2_fill_seconds" \
    "$gasal2_total_seconds" \
    "$gasal2_extend_wall_seconds" \
    "$transfer_string_seconds" \
    "$replacement_used" \
    "$replacement_fallbacks" >>"$summary"
done

cat "$summary"
