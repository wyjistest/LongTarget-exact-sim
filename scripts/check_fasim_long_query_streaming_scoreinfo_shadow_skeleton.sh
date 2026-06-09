#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_shadow_skeleton"}"
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
default_dir="$WORK/default"
candidate_dir="$WORK/candidate"
run_fasim "$baseline_dir"
run_fasim "$default_dir"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
default_digest="$(digest_for_dir "$default_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$default_digest" || "$baseline_digest" != "$candidate_digest" ]]; then
  echo "streaming scoreInfo shadow skeleton changed lite output digest" >&2
  echo "baseline=$baseline_digest default=$default_digest candidate=$candidate_digest" >&2
  exit 1
fi

default_requested="$(metric "$default_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested)"
requested="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested)"
active="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active)"
query_len="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_query_len)"
stripe_len="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripe_len)"
stripes="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripes)"
tasks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
cells="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cells)"
unsupported="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported)"
scoreinfo_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
candidate_missing="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing)"
candidate_extra="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra)"
decision="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"

for value_name in \
  default_requested requested active query_len stripe_len stripes tasks cells unsupported \
  scoreinfo_mismatches candidate_missing candidate_extra decision; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing streaming scoreInfo shadow skeleton metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$default_requested" != "0" ]]; then
  echo "streaming scoreInfo shadow must be default-off, got requested=$default_requested" >&2
  exit 1
fi
if [[ "$requested" != "1" || "$active" != "1" || "$unsupported" != "0" ]]; then
  echo "expected requested=1 active=1 unsupported=0, got requested=$requested active=$active unsupported=$unsupported" >&2
  exit 1
fi
if [[ "$query_len" != "8708" ]]; then
  echo "expected MALAT1 query_len=8708, got $query_len" >&2
  exit 1
fi
if [[ "$stripe_len" -le 0 || "$stripes" -le 1 ]]; then
  echo "expected positive multi-stripe skeleton, got stripe_len=$stripe_len stripes=$stripes" >&2
  exit 1
fi
if [[ "$tasks" -le 0 || "$cells" -le 0 ]]; then
  echo "expected task/cell accounting, got tasks=$tasks cells=$cells" >&2
  exit 1
fi
if [[ "$scoreinfo_mismatches" != "1" || "$candidate_missing" != "0" || "$candidate_extra" != "0" ]]; then
  echo "expected current active shadow checkpoint scoreinfo=1 missing=0 extra=0" >&2
  exit 1
fi
if [[ "$decision" != "streaming_scoreinfo_shadow_mismatch" ]]; then
  echo "unexpected streaming scoreInfo skeleton decision=$decision" >&2
  exit 1
fi

printf 'digest=%s\n' "$candidate_digest"
printf 'requested=%s\n' "$requested"
printf 'active=%s\n' "$active"
printf 'query_len=%s\n' "$query_len"
printf 'stripe_len=%s\n' "$stripe_len"
printf 'stripes=%s\n' "$stripes"
printf 'tasks=%s\n' "$tasks"
printf 'cells=%s\n' "$cells"
printf 'unsupported=%s\n' "$unsupported"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
