#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_ssw_profile_context_digest"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/base" "$WORK/context" "$WORK/context_validate"

cp "$ROOT/testDNA.fa" "$WORK/inputs/testDNA.fa"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

run_case() {
  local out_dir="$1"
  shift
  (
    cd "$WORK/inputs"
    env "$@" \
      FASIM_VERBOSE=0 \
      FASIM_OUTPUT_MODE=lite \
      "$BIN" -f1 testDNA.fa -f2 H19.fa -r 1 -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  )
}

run_case "$WORK/base"
run_case "$WORK/context" FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_PROFILE_CONTEXT=1
run_case "$WORK/context_validate" FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_SSW_PROFILE_CONTEXT_VALIDATE=1

BASE_OUT="$WORK/base/hg19-H19-testDNA-TFOsorted.lite"
CONTEXT_OUT="$WORK/context/hg19-H19-testDNA-TFOsorted.lite"
VALIDATE_OUT="$WORK/context_validate/hg19-H19-testDNA-TFOsorted.lite"

for path in "$BASE_OUT" "$CONTEXT_OUT" "$VALIDATE_OUT"; do
  if [[ ! -s "$path" ]]; then
    echo "expected output missing: $path" >&2
    exit 1
  fi
done

cmp -s "$BASE_OUT" "$CONTEXT_OUT"
cmp -s "$BASE_OUT" "$VALIDATE_OUT"

echo "ok"
