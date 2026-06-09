#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_fused_minscore_boundary"}"
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

metric() {
  local out_dir="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$out_dir/stderr.log" | tail -n 1
}

baseline_dir="$WORK/baseline"
candidate_dir="$WORK/candidate"
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "fused minScore boundary changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

tasks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
requested="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested)"
active="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_active)"
used="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_used)"
fallbacks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_fallbacks)"
score_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_score_mismatches)"
min_score_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_min_score_mismatches)"
scoreinfo_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
candidate_missing="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing)"
candidate_extra="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra)"
decision="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"
error="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_error)"

for value_name in \
  tasks requested active used fallbacks score_mismatches min_score_mismatches \
  scoreinfo_mismatches candidate_missing candidate_extra decision error; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing fused minScore boundary metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" || "$active" != "1" || "$fallbacks" != "0" ]]; then
  echo "expected fused requested=1 active=1 fallbacks=0, got requested=$requested active=$active fallbacks=$fallbacks" >&2
  exit 1
fi
if [[ "$used" -le 0 || "$used" -ge "$tasks" ]]; then
  echo "expected partial fused minScore use to expose mismatch boundary, got used=$used tasks=$tasks" >&2
  exit 1
fi
if [[ "$score_mismatches" -le 0 || "$min_score_mismatches" -le 0 ]]; then
  echo "expected fused minScore mismatch boundary, got score=$score_mismatches min_score=$min_score_mismatches" >&2
  exit 1
fi
if [[ "$scoreinfo_mismatches" -le 0 || "$candidate_missing" != "0" || "$candidate_extra" != "0" ]]; then
  echo "expected fused scoreInfo mismatch boundary under CPU authority, got scoreinfo=$scoreinfo_mismatches missing=$candidate_missing extra=$candidate_extra" >&2
  exit 1
fi
if [[ "$decision" != "streaming_scoreinfo_shadow_mismatch" ]]; then
  echo "expected fused scoreInfo mismatch decision, got $decision" >&2
  exit 1
fi
if [[ "$error" != "none" ]]; then
  echo "expected fused minScore launch error=none, got $error" >&2
  exit 1
fi

printf 'digest=%s\n' "$candidate_digest"
printf 'tasks=%s\n' "$tasks"
printf 'fused requested=%s active=%s used=%s fallbacks=%s\n' \
  "$requested" "$active" "$used" "$fallbacks"
printf 'fused score_mismatches=%s min_score_mismatches=%s\n' \
  "$score_mismatches" "$min_score_mismatches"
printf 'scoreinfo_boundary_mismatches=%s candidate_missing=%s candidate_extra=%s\n' \
  "$scoreinfo_mismatches" "$candidate_missing" "$candidate_extra"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
