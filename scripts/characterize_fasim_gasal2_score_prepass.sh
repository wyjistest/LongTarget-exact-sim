#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_score_prepass"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
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
mkdir -p "$WORK/base" "$WORK/prepass"

run_case() {
  local label="$1"
  shift
  local out_dir="$WORK/$label"
  local start_seconds
  local end_seconds
  start_seconds="$(date +%s)"
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end_seconds="$(date +%s)"
  printf '%s\n' "$((end_seconds - start_seconds))" >"$out_dir/wall_seconds.txt"
}

run_case base FASIM_ALIGN_GASAL2_SCORE_PREPASS=0
run_case prepass FASIM_ALIGN_GASAL2_SCORE_PREPASS=1

base_out="$(find "$WORK/base" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
prepass_out="$(find "$WORK/prepass" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$base_out" || -z "$prepass_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$base_out" \
  --candidate "$prepass_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

summary="$WORK/summary.csv"
echo "label,wall_seconds,digest,lines,score_prepass_enabled,gasal2_requests,gasal2_batches,score_requests,score_batches,traceback_requests,traceback_batches,gasal2_wait_seconds,score_wait_seconds,traceback_wait_seconds,gasal2_total_seconds,gasal2_extend_wall_seconds" >"$summary"

for label in base prepass; do
  out_dir="$WORK/$label"
  out_path="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  wall_seconds="$(cat "$out_dir/wall_seconds.txt")"
  digest="$(sha256sum "$out_path" | awk '{print $1}')"
  lines="$(wc -l < "$out_path")"
  score_prepass_enabled="$(awk -F= '/^benchmark\.fasim_gasal2_score_prepass_enabled=/{print $2}' "$out_dir/stderr.log")"
  gasal2_requests="$(awk -F= '/^benchmark\.fasim_gasal2_requests=/{print $2}' "$out_dir/stderr.log")"
  gasal2_batches="$(awk -F= '/^benchmark\.fasim_gasal2_batches=/{print $2}' "$out_dir/stderr.log")"
  score_requests="$(awk -F= '/^benchmark\.fasim_gasal2_score_requests=/{print $2}' "$out_dir/stderr.log")"
  score_batches="$(awk -F= '/^benchmark\.fasim_gasal2_score_batches=/{print $2}' "$out_dir/stderr.log")"
  traceback_requests="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_requests=/{print $2}' "$out_dir/stderr.log")"
  traceback_batches="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_batches=/{print $2}' "$out_dir/stderr.log")"
  gasal2_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  score_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_score_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  traceback_wait_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_wait_seconds=/{print $2}' "$out_dir/stderr.log")"
  gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$out_dir/stderr.log")"
  gasal2_extend_wall_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds=/{print $2}' "$out_dir/stderr.log")"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$label" \
    "$wall_seconds" \
    "$digest" \
    "$lines" \
    "$score_prepass_enabled" \
    "$gasal2_requests" \
    "$gasal2_batches" \
    "$score_requests" \
    "$score_batches" \
    "$traceback_requests" \
    "$traceback_batches" \
    "$gasal2_wait_seconds" \
    "$score_wait_seconds" \
    "$traceback_wait_seconds" \
    "$gasal2_total_seconds" \
    "$gasal2_extend_wall_seconds" >>"$summary"
done

cat "$summary"
cat "$WORK/top5_compare.txt"
