#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_exact_column_multigpu_guard"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/out"

cp "$ROOT/testDNA.fa" "$WORK/inputs/testDNA.fa"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

strings "$BIN" >"$WORK/strings.txt"
grep -q 'FASIM_EXACT_COLUMN_EXTEND_BATCH' "$WORK/strings.txt"

set +e
(
  cd "$WORK/inputs"
  env \
    FASIM_VERBOSE=0 \
    FASIM_OUTPUT_MODE=lite \
    FASIM_EXACT_COLUMN_EXTEND_BATCH=1 \
    FASIM_CUDA_DEVICES=0,1 \
    "$BIN" -f1 testDNA.fa -f2 H19.fa -r 1 -O "$WORK/out" \
    >"$WORK/stdout.log" 2>"$WORK/stderr.log"
)
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  echo "expected FASIM_EXACT_COLUMN_EXTEND_BATCH + FASIM_CUDA_DEVICES=0,1 to fail" >&2
  exit 1
fi

grep -q 'exact-column batch requires a single visible CUDA device per Fasim process' "$WORK/stderr.log"
grep -q 'Use process-level sharding with CUDA_VISIBLE_DEVICES per worker' "$WORK/stderr.log"

echo "ok"
