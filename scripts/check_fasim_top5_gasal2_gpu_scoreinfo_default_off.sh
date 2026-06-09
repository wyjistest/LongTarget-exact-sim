#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="$ROOT/.tmp/check_fasim_top5_gasal2_gpu_scoreinfo_default_off"

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
mkdir -p "$WORK/default"

env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  "$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 0 -O "$WORK/default" \
  >"$WORK/default/stdout.log" 2>"$WORK/default/stderr.log"

out="$WORK/default/hg19-H19-testDNA-TFOsorted.lite"
if [[ ! -s "$out" ]]; then
  echo "expected lite output missing: $out" >&2
  exit 1
fi

grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=0$' "$WORK/default/stderr.log"
grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=0$' "$WORK/default/stderr.log"
grep -q '^benchmark\.fasim_gasal2_enabled=0$' "$WORK/default/stderr.log"
grep -q '^benchmark\.fasim_gasal2_requests=0$' "$WORK/default/stderr.log"
grep -q '^benchmark\.fasim_gasal2_traceback_requests=0$' "$WORK/default/stderr.log"

digest="$(sha256sum "$out" | awk '{print $1}')"
lines="$(wc -l < "$out")"
if [[ "$digest" != "ed351b98877c7c3c5f9bfeb05c0d23c36b61c20f30c6ee22f584bd18183a77c4" ]]; then
  echo "unexpected default output digest: $digest" >&2
  exit 1
fi
if [[ "$lines" != "146" ]]; then
  echo "unexpected default output line count: $lines" >&2
  exit 1
fi

echo "ok"
