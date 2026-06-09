#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_exact_tile_overlap_probe"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
EXACT_TILE_OVERLAP="${EXACT_TILE_OVERLAP:-1406}"
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
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT=1 \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_CANDIDATE_EQUIVALENCE=1 \
  FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_OVERLAP="$EXACT_TILE_OVERLAP"

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
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "overlap probe changed lite output digest" >&2
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
tile_overlap="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_overlap)"
tiles="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tiles)"
tile_descriptors="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptors)"
tile_max_query_len="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_max_query_len)"
descriptor_digest="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptor_digest)"
cpu_oracle_candidates="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_cpu_oracle_candidates)"
tile_candidates="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_candidates)"
candidate_missing="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_missing)"
candidate_extra="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_extra)"
position_missing="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_missing)"
position_extra="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_extra)"
position_score_mismatches="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_score_mismatches)"
fallback="$(metric benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_fallback)"

for value_name in \
  requested active query_len tile_len tile_overlap tiles tile_descriptors \
  tile_max_query_len descriptor_digest cpu_oracle_candidates tile_candidates \
  candidate_missing candidate_extra position_missing position_extra \
  position_score_mismatches fallback; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing exact-tile overlap probe metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "expected requested=1 active=1, got requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$query_len" != "8708" || "$tile_len" != "2812" ]]; then
  echo "unexpected query/tile lengths: query_len=$query_len tile_len=$tile_len" >&2
  exit 1
fi
if [[ "$tile_overlap" != "$EXACT_TILE_OVERLAP" ]]; then
  echo "expected tile_overlap=$EXACT_TILE_OVERLAP, got $tile_overlap" >&2
  exit 1
fi
if [[ "$tiles" -le 1 || "$tile_descriptors" != "$tiles" ]]; then
  echo "unexpected tile counts: tiles=$tiles tile_descriptors=$tile_descriptors" >&2
  exit 1
fi
if [[ "$tile_max_query_len" -gt "$tile_len" ]]; then
  echo "tile max query length exceeds tile_len: max=$tile_max_query_len tile_len=$tile_len" >&2
  exit 1
fi
if [[ "$descriptor_digest" == "0" ]]; then
  echo "missing stable descriptor digest" >&2
  exit 1
fi
if [[ "$cpu_oracle_candidates" -le 0 || "$tile_candidates" -le 0 ]]; then
  echo "expected candidate counts > 0, got cpu=$cpu_oracle_candidates tile=$tile_candidates" >&2
  exit 1
fi
if [[ "$fallback" != "0" ]]; then
  echo "overlap probe should be fallback clean, got fallback=$fallback" >&2
  exit 1
fi

decision="exact_tile_overlap_candidate_equivalence_go"
if [[ "$candidate_missing" != "0" || "$candidate_extra" != "0" ]]; then
  decision="exact_tile_overlap_candidate_equivalence_no_go"
fi

printf 'decision=%s\n' "$decision"
printf 'digest=%s\n' "$candidate_digest"
printf 'tile_overlap=%s\n' "$tile_overlap"
printf 'tiles=%s\n' "$tiles"
printf 'tile_descriptor_digest=%s\n' "$descriptor_digest"
printf 'cpu_oracle_candidates=%s\n' "$cpu_oracle_candidates"
printf 'tile_candidates=%s\n' "$tile_candidates"
printf 'candidate_missing=%s\n' "$candidate_missing"
printf 'candidate_extra=%s\n' "$candidate_extra"
printf 'position_missing=%s\n' "$position_missing"
printf 'position_extra=%s\n' "$position_extra"
printf 'position_score_mismatches=%s\n' "$position_score_mismatches"
printf 'ok\n'
