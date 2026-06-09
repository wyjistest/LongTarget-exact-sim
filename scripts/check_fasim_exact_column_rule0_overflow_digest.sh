#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_exact_column_rule0_overflow_digest"
rm -rf "$WORK"
mkdir -p "$WORK/cpu" "$WORK/gpu"

run_case() {
  local out_dir="$1"
  shift
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 0 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/cpu"
run_case "$WORK/gpu" \
  FASIM_GPU_DP_COLUMN_AUTO=1 \
  FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 \
  FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 \
  FASIM_EXACT_COLUMN_EXTEND_BATCH=1 \
  FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1 \
  FASIM_PREALIGN_CUDA_TOPK=64

CPU_OUT="$WORK/cpu/hg19-H19-testDNA-TFOsorted.lite"
GPU_OUT="$WORK/gpu/hg19-H19-testDNA-TFOsorted.lite"

for path in "$CPU_OUT" "$GPU_OUT"; do
  if [[ ! -s "$path" ]]; then
    echo "expected output missing: $path" >&2
    exit 1
  fi
done

if grep -q 'exact_batch] validate mismatch' "$WORK/gpu/stderr.log"; then
  echo "exact-column validation mismatch in rule 0 overflow regression" >&2
  grep 'exact_batch] validate mismatch' "$WORK/gpu/stderr.log" >&2
  exit 1
fi

cmp -s "$CPU_OUT" "$GPU_OUT"

echo "ok"
