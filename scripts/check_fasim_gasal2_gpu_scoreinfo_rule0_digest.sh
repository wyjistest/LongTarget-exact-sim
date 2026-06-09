#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

WORK="$ROOT/.tmp/check_fasim_gasal2_gpu_scoreinfo_rule0_digest"
rm -rf "$WORK"
mkdir -p "$WORK/direct_cpu_score" "$WORK/direct_gpu_score"

run_case() {
  local out_dir="$1"
  shift
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
    FASIM_ALIGN_GASAL2_ALL_TRACEBACK=1 \
    FASIM_ALIGN_GASAL2_BATCH=5000 \
    FASIM_ALIGN_GASAL2_TASK_BATCH=4096 \
    "$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 0 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/direct_cpu_score"
run_case "$WORK/direct_gpu_score" \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1

CPU_SCORE_OUT="$WORK/direct_cpu_score/hg19-H19-testDNA-TFOsorted.lite"
GPU_SCORE_OUT="$WORK/direct_gpu_score/hg19-H19-testDNA-TFOsorted.lite"

for path in "$CPU_SCORE_OUT" "$GPU_SCORE_OUT"; do
  if [[ ! -s "$path" ]]; then
    echo "expected output missing: $path" >&2
    exit 1
  fi
done

cmp -s "$CPU_SCORE_OUT" "$GPU_SCORE_OUT"
grep -Eq '^benchmark\.fasim_gasal2_traceback_requests=[1-9][0-9]*$' "$WORK/direct_gpu_score/stderr.log"
grep -q '^benchmark\.fasim_gasal2_cpu_traceback_align_calls=0$' "$WORK/direct_gpu_score/stderr.log"

echo "ok"
