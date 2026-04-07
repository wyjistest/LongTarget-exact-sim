#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_throughput_preset"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/out"

cp "$ROOT/testDNA.fa" "$WORK/inputs/testDNA.fa"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

(
  cd "$WORK/inputs"
  BIN="$BIN" "$ROOT/scripts/run_fasim_throughput_preset.sh" \
    -f1 testDNA.fa -f2 H19.fa -r 1 -O "$WORK/out" >"$WORK/stdout.log" 2>"$WORK/stderr.log"
)

OUT_FILE="$WORK/out/hg19-H19-testDNA-TFOsorted.lite"
if [[ ! -s "$OUT_FILE" ]]; then
  echo "expected throughput preset lite output missing: $OUT_FILE" >&2
  ls -la "$WORK/out" >&2 || true
  exit 1
fi

if [[ -e "$WORK/out/hg19-H19-testDNA-TFOsorted" ]]; then
  echo "unexpected full TFOsorted produced by throughput preset" >&2
  exit 1
fi

if [[ -s "$WORK/stdout.log" ]]; then
  echo "expected throughput preset stdout to stay quiet" >&2
  cat "$WORK/stdout.log" >&2
  exit 1
fi

set +e
(
  cd "$WORK/inputs"
  BIN="$BIN" FASIM_THRESHOLD_POLICY=bogus "$ROOT/scripts/run_fasim_throughput_preset.sh" \
    -f1 testDNA.fa -f2 H19.fa -r 1 -O "$WORK/out_invalid" >"$WORK/stdout_invalid.log" 2>"$WORK/stderr_invalid.log"
)
status=$?
set -e

if [[ $status -eq 0 ]]; then
  echo "expected invalid FASIM_THRESHOLD_POLICY to fail" >&2
  exit 1
fi

grep -q "unsupported FASIM_THRESHOLD_POLICY" "$WORK/stderr_invalid.log"

echo "ok"
