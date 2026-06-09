#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_exact_tile_oracle_export"}"
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
candidate_dir="$WORK/candidate"
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1 \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT=1

baseline_out="$(find "$baseline_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
candidate_out="$(find "$candidate_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$candidate_out" ]]; then
  echo "missing lite output" >&2
  exit 1
fi

baseline_digest="$(sha256sum "$baseline_out" | awk '{print $1}')"
candidate_digest="$(sha256sum "$candidate_out" | awk '{print $1}')"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "oracle export changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log" | tail -n 1
}

requested="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_requested)"
active="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_active)"
query_len="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_query_len)"
tile_len="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_len)"
tiles="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tiles)"
cpu_oracle_candidates="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_cpu_oracle_candidates)"
fallback="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_fallback)"

for value_name in requested active query_len tile_len tiles cpu_oracle_candidates fallback; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing exact-tile oracle metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" ]]; then
  echo "expected requested=1, got $requested" >&2
  exit 1
fi
if [[ "$active" != "0" ]]; then
  echo "oracle export must not activate tile implementation, got active=$active" >&2
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
if [[ "$cpu_oracle_candidates" -le 0 ]]; then
  echo "expected CPU oracle candidates > 0, got $cpu_oracle_candidates" >&2
  exit 1
fi
if [[ "$fallback" != "0" ]]; then
  echo "oracle export should be fallback clean, got fallback=$fallback" >&2
  exit 1
fi

printf 'digest=%s\n' "$candidate_digest"
printf 'cpu_oracle_candidates=%s\n' "$cpu_oracle_candidates"
printf 'tiles=%s\n' "$tiles"
printf 'ok\n'
