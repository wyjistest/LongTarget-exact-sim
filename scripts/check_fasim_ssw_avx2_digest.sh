#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CPU_BIN="${CPU_BIN:-"$ROOT/fasim_longtarget_x86"}"
AVX2_BIN="${AVX2_BIN:-"$ROOT/.tmp/fasim_ssw_avx2_digest/fasim_longtarget_x86_avx2"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_ssw_avx2_digest"}"

rm -rf "$WORK"
mkdir -p "$WORK"

strings "$AVX2_BIN" > "$WORK/strings.txt"
grep -q 'FASIM_SSW_AVX2' "$WORK/strings.txt"
grep -q 'FASIM_SSW_AVX2_MODE' "$WORK/strings.txt"

run_case() {
  local bin="$1"
  local out_dir="$2"
  shift 2
  mkdir -p "$out_dir"
  env "$@" \
      FASIM_VERBOSE=0 \
      FASIM_OUTPUT_MODE=lite \
      "$bin" \
      -f1 "$ROOT/testDNA.fa" \
      -f2 "$ROOT/H19.fa" \
      -r 0 \
      -O "$out_dir" >/dev/null 2>"$out_dir/stderr.log"
  local output_file="$out_dir/hg19-H19-testDNA-TFOsorted.lite"
  if [[ ! -s "$output_file" ]]; then
    echo "expected output missing: $output_file" >&2
    exit 1
  fi
  sha256sum "$output_file" | awk '{print $1}' > "$out_dir/digest.txt"
}

run_case "$CPU_BIN" "$WORK/cpu"
run_case "$AVX2_BIN" "$WORK/avx2" FASIM_SSW_AVX2=1
run_case "$AVX2_BIN" "$WORK/avx2_validate" FASIM_SSW_AVX2=1 FASIM_SSW_AVX2_MODE=forward_only

cmp "$WORK/cpu/digest.txt" "$WORK/avx2/digest.txt"
cmp "$WORK/cpu/digest.txt" "$WORK/avx2_validate/digest.txt"
