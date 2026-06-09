#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_exact_column_scoreinfo_shadow_smem_optin"}"
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
  FASIM_ENABLE_PREALIGN_CUDA=1 \
  FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW_SMEM_OPTIN=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS=16

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
  echo "long-query exact-column scoreInfo smem opt-in shadow changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log" | tail -n 1
}

requested="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_requested)"
active="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_active)"
query_len="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_query_len)"
gpu_batches="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_batches)"
gpu_tasks="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_tasks)"
scoreinfo_mismatches="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_scoreinfo_mismatches)"
required_smem="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_required_smem)"
default_smem_limit="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_default_smem_limit)"
optin_smem_limit="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_optin_smem_limit)"
resource_fit="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_resource_fit)"
smem_optin_requested="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_requested)"
smem_optin_active="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_active)"
error="$(metric benchmark.fasim_long_query_exact_column_scoreinfo_shadow_error)"

for value_name in \
  requested active query_len gpu_batches gpu_tasks scoreinfo_mismatches \
  required_smem default_smem_limit optin_smem_limit resource_fit \
  smem_optin_requested smem_optin_active error; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing smem opt-in shadow metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" || "$smem_optin_requested" != "1" ]]; then
  echo "expected requested smem opt-in shadow, got requested=$requested smem_optin_requested=$smem_optin_requested" >&2
  exit 1
fi
if [[ "$query_len" != "8708" ]]; then
  echo "unexpected query_len=$query_len" >&2
  exit 1
fi
if [[ "$required_smem" -le "$default_smem_limit" || "$required_smem" -gt "$optin_smem_limit" ]]; then
  echo "unexpected smem boundary: required=$required_smem default=$default_smem_limit optin=$optin_smem_limit" >&2
  exit 1
fi
if [[ "$resource_fit" != "1" ]]; then
  echo "expected resource_fit=1 under opt-in boundary, got $resource_fit" >&2
  exit 1
fi
if [[ "$active" != "1" || "$smem_optin_active" != "1" ]]; then
  echo "expected active opt-in shadow, got active=$active smem_optin_active=$smem_optin_active error=$error" >&2
  exit 1
fi
if [[ "$gpu_batches" -le 0 || "$gpu_tasks" -le 0 ]]; then
  echo "expected GPU batches/tasks with opt-in, got gpu_batches=$gpu_batches gpu_tasks=$gpu_tasks" >&2
  exit 1
fi
if [[ "$scoreinfo_mismatches" -le 0 ]]; then
  echo "expected opt-in shadow to remain scoreInfo no-go, got mismatches=$scoreinfo_mismatches" >&2
  exit 1
fi

decision="smem_optin_scoreinfo_no_go"
printf 'digest=%s\n' "$candidate_digest"
printf 'requested=%s\n' "$requested"
printf 'active=%s\n' "$active"
printf 'query_len=%s\n' "$query_len"
printf 'gpu_batches=%s\n' "$gpu_batches"
printf 'gpu_tasks=%s\n' "$gpu_tasks"
printf 'scoreinfo_mismatches=%s\n' "$scoreinfo_mismatches"
printf 'required_smem=%s\n' "$required_smem"
printf 'default_smem_limit=%s\n' "$default_smem_limit"
printf 'optin_smem_limit=%s\n' "$optin_smem_limit"
printf 'resource_fit=%s\n' "$resource_fit"
printf 'smem_optin_requested=%s\n' "$smem_optin_requested"
printf 'smem_optin_active=%s\n' "$smem_optin_active"
printf 'error=%s\n' "$error"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
