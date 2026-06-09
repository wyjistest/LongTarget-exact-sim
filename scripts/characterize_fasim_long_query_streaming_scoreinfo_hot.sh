#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_hot"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-8 16 32 64}"
WORKLOAD_SPECS="${WORKLOAD_SPECS:-}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	record_limit	digest	tasks	gpu_batches	gpu_scoreinfo_groups	cpu_scoreinfo_groups	scoreinfo_mismatches	candidate_missing	candidate_extra	gpu_minscore_used	gpu_minscore_fallbacks	gpu_minscore_score_mismatches	gpu_minscore_min_score_mismatches	gpu_hot_total_seconds	gpu_minscore_wall_seconds	gpu_call_seconds	kernel_seconds	validation_seconds	validation_minscore_seconds	cpu_prealign_seconds	hot_path_speedup	decision" \
  >"$summary"

metric() {
  local stderr="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1
}

run_spec() {
  local workload="$1"
  local limit="$2"
  local rna_input="$3"
  local dna_input="$4"
  local expected_query_len="$5"
  local legacy_byte_shared="$6"

  case "$limit" in
    ''|*[!0-9]*)
      echo "record limits must contain positive integers, got: $limit" >&2
      exit 1
      ;;
  esac
  if [[ "$limit" -le 0 ]]; then
    echo "record limits must contain positive integers, got: $limit" >&2
    exit 1
  fi
  if [[ ! -s "$rna_input" || ! -s "$dna_input" ]]; then
    echo "missing inputs for $workload: RNA=$rna_input DNA=$dna_input" >&2
    exit 1
  fi

  run_work="$WORK/${workload,,}_first${limit}"
  child_work="$run_work/run"
  mkdir -p "$run_work"
  echo "running ${workload} first${limit}" >&2
  extra_env="FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1"
  if [[ "$legacy_byte_shared" == "1" ]]; then
    extra_env="$extra_env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1"
  fi
  MALAT1_RECORD_LIMIT="$limit" \
  WORKLOAD_NAME="$workload" \
  RECORD_LIMIT="$limit" \
  RNA_INPUT="$rna_input" \
  DNA_INPUT="$dna_input" \
  EXPECTED_QUERY_LEN="$expected_query_len" \
  WORK="$child_work" \
  BIN="$BIN" \
  BUILD_BIN=0 \
  EXTRA_SHADOW_ENV="$extra_env" \
  EXPECTED_SCOREINFO_MISMATCHES=0 \
  EXPECTED_DECISION=streaming_scoreinfo_shadow_active \
  EXPECTED_LEGACY_BYTE_SHARED="$legacy_byte_shared" \
  EXPECTED_GPU_MINSCORE_REQUESTED=1 \
  EXPECTED_GPU_MINSCORE_ACTIVE=1 \
  EXPECTED_GPU_MINSCORE_HOT=1 \
    bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore_hot.sh" \
    >"$run_work/check.stdout" 2>"$run_work/check.stderr"

  stdout="$run_work/check.stdout"
  stderr="$child_work/candidate/stderr.log"
  if [[ ! -s "$stdout" || ! -s "$stderr" ]]; then
    echo "missing output for ${workload} first${limit}" >&2
    exit 1
  fi

  digest="$(sed -n 's/^digest=//p' "$stdout" | tail -n 1)"
  tasks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
  gpu_batches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_batches)"
  gpu_scoreinfo_groups="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups)"
  cpu_scoreinfo_groups="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups)"
  scoreinfo_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
  candidate_missing="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing)"
  candidate_extra="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra)"
  gpu_minscore_used="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used)"
  gpu_minscore_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks)"
  gpu_minscore_score_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches)"
  gpu_minscore_min_score_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches)"
  gpu_hot_total_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds)"
  gpu_minscore_wall_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds)"
  gpu_call_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds)"
  kernel_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds)"
  validation_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds)"
  validation_minscore_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds)"
  cpu_prealign_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds)"
  decision="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"

  for name in \
    digest tasks gpu_batches gpu_scoreinfo_groups cpu_scoreinfo_groups \
    scoreinfo_mismatches candidate_missing candidate_extra gpu_minscore_used \
    gpu_minscore_fallbacks gpu_minscore_score_mismatches \
    gpu_minscore_min_score_mismatches gpu_hot_total_seconds \
    gpu_minscore_wall_seconds gpu_call_seconds kernel_seconds validation_seconds \
    validation_minscore_seconds cpu_prealign_seconds decision; do
    if [[ -z "${!name}" ]]; then
      echo "missing metric $name for MALAT1 first${limit}" >&2
      exit 1
    fi
  done

  hot_path_speedup="$(
    awk -v cpu="$cpu_prealign_seconds" -v gpu="$gpu_hot_total_seconds" 'BEGIN {
      if ((gpu + 0.0) <= 0.0) {
        print "0";
      } else {
        printf "%.6f", (cpu + 0.0) / (gpu + 0.0);
      }
    }'
  )"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%sx\t%s\n' \
    "${workload,,}_first${limit}" \
    "$limit" \
    "$digest" \
    "$tasks" \
    "$gpu_batches" \
    "$gpu_scoreinfo_groups" \
    "$cpu_scoreinfo_groups" \
    "$scoreinfo_mismatches" \
    "$candidate_missing" \
    "$candidate_extra" \
    "$gpu_minscore_used" \
    "$gpu_minscore_fallbacks" \
    "$gpu_minscore_score_mismatches" \
    "$gpu_minscore_min_score_mismatches" \
    "$gpu_hot_total_seconds" \
    "$gpu_minscore_wall_seconds" \
    "$gpu_call_seconds" \
    "$kernel_seconds" \
    "$validation_seconds" \
    "$validation_minscore_seconds" \
    "$cpu_prealign_seconds" \
    "$hot_path_speedup" \
    "$decision" \
    >>"$summary"
}

if [[ -n "$WORKLOAD_SPECS" ]]; then
  while IFS='|' read -r workload limit rna_input dna_input expected_query_len legacy_byte_shared; do
    if [[ -z "$workload" ]]; then
      continue
    fi
    run_spec "$workload" "$limit" "$rna_input" "$dna_input" "$expected_query_len" "${legacy_byte_shared:-0}"
  done <<< "$WORKLOAD_SPECS"
else
  for limit in $MALAT1_RECORD_LIMITS; do
    run_spec \
      "MALAT1" \
      "$limit" \
      "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
      "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
      "8708" \
      "1"
  done
fi

cat "$summary"
