#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
CPU_BIN="${CPU_BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi
if [[ ! -x "$CPU_BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_gpu_dp_column_auto_digest"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/cpu" "$WORK/manual_cuda" "$WORK/auto_high" "$WORK/auto_low" "$WORK/auto_low_exact"

cp "$ROOT/testDNA.fa" "$WORK/inputs/testDNA.fa"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

strings "$BIN" >"$WORK/strings.txt"
grep -q 'FASIM_GPU_DP_COLUMN_AUTO' "$WORK/strings.txt"
grep -q 'FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS' "$WORK/strings.txt"
grep -q 'FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS' "$WORK/strings.txt"

run_case() {
  local bin="$1"
  local out_dir="$2"
  shift 2
  (
    cd "$WORK/inputs"
    env "$@" \
      FASIM_VERBOSE=0 \
      FASIM_OUTPUT_MODE=lite \
      "$bin" -f1 testDNA.fa -f2 H19.fa -r 1 -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  )
}

run_case "$CPU_BIN" "$WORK/cpu"
run_case "$BIN" "$WORK/manual_cuda" FASIM_ENABLE_PREALIGN_CUDA=1 FASIM_PREALIGN_CUDA_TOPK=64
run_case "$BIN" "$WORK/auto_high" FASIM_GPU_DP_COLUMN_AUTO=1
run_case "$BIN" "$WORK/auto_low" FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_PREALIGN_CUDA_TOPK=64
run_case "$BIN" "$WORK/auto_low_exact" FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_PREALIGN_CUDA_TOPK=64 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1

CPU_OUT="$WORK/cpu/hg19-H19-testDNA-TFOsorted.lite"
MANUAL_OUT="$WORK/manual_cuda/hg19-H19-testDNA-TFOsorted.lite"
AUTO_HIGH_OUT="$WORK/auto_high/hg19-H19-testDNA-TFOsorted.lite"
AUTO_LOW_OUT="$WORK/auto_low/hg19-H19-testDNA-TFOsorted.lite"
AUTO_LOW_EXACT_OUT="$WORK/auto_low_exact/hg19-H19-testDNA-TFOsorted.lite"

for path in "$CPU_OUT" "$MANUAL_OUT" "$AUTO_HIGH_OUT" "$AUTO_LOW_OUT" "$AUTO_LOW_EXACT_OUT"; do
  if [[ ! -s "$path" ]]; then
    echo "expected output missing: $path" >&2
    exit 1
  fi
done

cmp -s "$CPU_OUT" "$AUTO_HIGH_OUT"
cmp -s "$MANUAL_OUT" "$AUTO_LOW_OUT"
cmp -s "$CPU_OUT" "$AUTO_LOW_EXACT_OUT"

echo "ok"
