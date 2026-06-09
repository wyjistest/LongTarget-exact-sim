#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_exact_tile_descriptors"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
MALAT1_RNA="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
MALAT1_DNA="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

if [[ ! -s "$MALAT1_RNA" || ! -s "$MALAT1_DNA" ]]; then
  echo "missing MALAT1 inputs" >&2
  exit 1
fi

sample="$WORK/inputs/malat1_first${MALAT1_RECORD_LIMIT}.fa"
awk -v limit="$MALAT1_RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$MALAT1_DNA" >"$sample"

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
    -f2 "$MALAT1_RNA" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

baseline_dir="$WORK/baseline"
candidate_a_dir="$WORK/candidate_a"
candidate_b_dir="$WORK/candidate_b"
run_fasim "$baseline_dir"
run_fasim "$candidate_a_dir" \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1
run_fasim "$candidate_b_dir" \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1

digest_for_dir() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  sha256sum "$out_file" | awk '{print $1}'
}

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_a_digest="$(digest_for_dir "$candidate_a_dir")"
candidate_b_digest="$(digest_for_dir "$candidate_b_dir")"
if [[ "$baseline_digest" != "$candidate_a_digest" || "$baseline_digest" != "$candidate_b_digest" ]]; then
  echo "exact-tile descriptors changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate_a=$candidate_a_digest candidate_b=$candidate_b_digest" >&2
  exit 1
fi

metric() {
  local out_dir="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$out_dir/stderr.log" | tail -n 1
}

requested="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_requested)"
active="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_active)"
query_len="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_query_len)"
tile_len="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_len)"
tiles="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tiles)"
tile_descriptors="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptors)"
tile_max_query_len="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_max_query_len)"
descriptor_digest_a="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptor_digest)"
descriptor_digest_b="$(metric "$candidate_b_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptor_digest)"
fallback="$(metric "$candidate_a_dir" benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_fallback)"

for value_name in \
  requested active query_len tile_len tiles tile_descriptors tile_max_query_len \
  descriptor_digest_a descriptor_digest_b fallback; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing exact-tile descriptor metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" ]]; then
  echo "expected requested=1, got $requested" >&2
  exit 1
fi
if [[ "$active" != "0" ]]; then
  echo "descriptor shadow must not activate tile implementation, got active=$active" >&2
  exit 1
fi
if [[ "$query_len" != "8708" ]]; then
  echo "expected MALAT1 query_len=8708, got $query_len" >&2
  exit 1
fi
if [[ "$tile_len" != "2812" ]]; then
  echo "expected tile_len=2812, got $tile_len" >&2
  exit 1
fi
if [[ "$tiles" -le 1 ]]; then
  echo "expected multiple exact tiles, got $tiles" >&2
  exit 1
fi
if [[ "$tile_descriptors" != "$tiles" ]]; then
  echo "expected tile_descriptors=$tiles, got $tile_descriptors" >&2
  exit 1
fi
if [[ "$tile_max_query_len" -gt "$tile_len" ]]; then
  echo "tile max query length exceeds tile_len: max=$tile_max_query_len tile_len=$tile_len" >&2
  exit 1
fi
if [[ "$descriptor_digest_a" == "0" || "$descriptor_digest_a" != "$descriptor_digest_b" ]]; then
  echo "tile descriptor digest is not stable" >&2
  echo "a=$descriptor_digest_a b=$descriptor_digest_b" >&2
  exit 1
fi
if [[ "$fallback" != "0" ]]; then
  echo "descriptor shadow should be fallback clean, got fallback=$fallback" >&2
  exit 1
fi

printf 'digest=%s\n' "$candidate_a_digest"
printf 'tile_descriptors=%s\n' "$tile_descriptors"
printf 'tile_max_query_len=%s\n' "$tile_max_query_len"
printf 'tile_descriptor_digest=%s\n' "$descriptor_digest_a"
printf 'ok\n'
