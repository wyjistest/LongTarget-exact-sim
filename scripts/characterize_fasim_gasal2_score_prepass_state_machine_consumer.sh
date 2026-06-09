#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_score_prepass_state_machine_consumer"}"
BUILD_BIN="${BUILD_BIN:-1}"
if [[ -z "${NEAT1_RECORD_LIMITS+x}" ]]; then
  NEAT1_RECORD_LIMITS="1 4 16"
fi
if [[ -z "${MALAT1_RECORD_LIMITS+x}" ]]; then
  MALAT1_RECORD_LIMITS=""
fi
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"
summary="$WORK/summary.tsv"
printf '%s\n' \
  "workload	record_limit	probe_max_tasks	digest	tasks	scoreinfo_mismatches	realpath_fallbacks	length_guard_fallbacks	state_machine_tasks	state_machine_scoreinfos	state_machine_attempts	state_machine_selected_hits	state_machine_cpu_align_attempts	state_machine_fallbacks	state_machine_triplex_mismatches	gasal2_score_requests	gasal2_score_batches	gasal2_score_wait_seconds	realpath_extend_seconds	realpath_extend_align_attempts	state_machine_total_seconds	state_machine_select_seconds	state_machine_cpu_align_seconds	state_machine_convert_seconds	baseline_wall_seconds	candidate_wall_seconds	candidate_vs_baseline" \
  >"$summary"

metric() {
  local stderr="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1
}

require_positive_int() {
  local name="$1"
  local value="$2"
  case "$value" in
    ''|*[!0-9]*)
      echo "$name must be a positive integer, got: $value" >&2
      exit 1
      ;;
  esac
  if [[ "$value" -le 0 ]]; then
    echo "$name must be a positive integer, got: $value" >&2
    exit 1
  fi
}

first_records() {
  local input="$1"
  local limit="$2"
  local output="$3"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$input" >"$output"
  if [[ ! -s "$output" ]]; then
    echo "empty sample generated from $input limit=$limit" >&2
    exit 1
  fi
}

run_fasim() {
  local sample="$1"
  local rna="$2"
  local out_dir="$3"
  shift 3
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
    -f2 "$rna" \
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

wall_seconds() {
  local out_dir="$1"
  local wall
  wall="$(metric "$out_dir/stderr.log" benchmark.total_wall_seconds)"
  if [[ -z "$wall" ]]; then
    wall="$(sed -n 's/^Running time is //p' "$out_dir/stdout.log" | tail -n 1)"
  fi
  if [[ -z "$wall" ]]; then
    echo "missing wall seconds for $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$wall"
}

run_case() {
  local workload="$1"
  local limit="$2"
  local dna="$3"
  local rna="$4"
  require_positive_int "${workload}_record_limit" "$limit"
  if [[ ! -s "$dna" || ! -s "$rna" ]]; then
    echo "missing $workload inputs: dna=$dna rna=$rna" >&2
    exit 1
  fi

  local probe_tasks="$REPLAY_PROBE_MAX_TASKS"
  if [[ -z "$probe_tasks" ]]; then
    probe_tasks="$limit"
  fi
  require_positive_int "${workload}_probe_max_tasks" "$probe_tasks"

  local run_dir="$WORK/${workload}_first${limit}_probe${probe_tasks}"
  mkdir -p "$run_dir/inputs"
  local sample="$run_dir/inputs/${workload}_first${limit}.fa"
  first_records "$dna" "$limit" "$sample"

  echo "running ${workload} first${limit} score-prepass state-machine shadow probe=${probe_tasks}" >&2
  run_fasim "$sample" "$rna" "$run_dir/baseline"
  run_fasim "$sample" "$rna" "$run_dir/candidate" \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$probe_tasks" \
    FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1 \
    FASIM_ALIGN_GASAL2=1

  local baseline_digest candidate_digest
  baseline_digest="$(digest_for_dir "$run_dir/baseline")"
  candidate_digest="$(digest_for_dir "$run_dir/candidate")"
  if [[ "$baseline_digest" != "$candidate_digest" ]]; then
    echo "$workload first${limit} digest mismatch: baseline=$baseline_digest candidate=$candidate_digest" >&2
    exit 1
  fi

  local stderr="$run_dir/candidate/stderr.log"
  local digest="$candidate_digest"
  local tasks scoreinfo_mismatches realpath_fallbacks length_guard_fallbacks
  local state_machine_tasks state_machine_scoreinfos state_machine_attempts
  local state_machine_selected_hits state_machine_cpu_align_attempts
  local state_machine_fallbacks state_machine_triplex_mismatches
  local gasal2_score_requests gasal2_score_batches gasal2_score_wait_seconds
  local realpath_extend_seconds realpath_extend_align_attempts
  local state_machine_total_seconds state_machine_select_seconds
  local state_machine_cpu_align_seconds state_machine_convert_seconds
  local baseline_wall candidate_wall candidate_vs_baseline

  tasks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
  scoreinfo_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
  realpath_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks)"
  length_guard_fallbacks="$(metric "$stderr" benchmark.fasim_gasal2_length_guard_fallbacks)"
  state_machine_tasks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_tasks)"
  state_machine_scoreinfos="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_scoreinfos)"
  state_machine_attempts="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_attempts)"
  state_machine_selected_hits="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_selected_attempts)"
  state_machine_cpu_align_attempts="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_attempts)"
  state_machine_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_fallbacks)"
  state_machine_triplex_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_triplex_mismatches)"
  gasal2_score_requests="$(metric "$stderr" benchmark.fasim_gasal2_score_requests)"
  gasal2_score_batches="$(metric "$stderr" benchmark.fasim_gasal2_score_batches)"
  gasal2_score_wait_seconds="$(metric "$stderr" benchmark.fasim_gasal2_score_wait_seconds)"
  realpath_extend_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds)"
  realpath_extend_align_attempts="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts)"
  state_machine_total_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_total_seconds)"
  state_machine_select_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_select_seconds)"
  state_machine_cpu_align_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_seconds)"
  state_machine_convert_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_convert_seconds)"
  baseline_wall="$(wall_seconds "$run_dir/baseline")"
  candidate_wall="$(wall_seconds "$run_dir/candidate")"

  for name in \
    tasks scoreinfo_mismatches realpath_fallbacks length_guard_fallbacks \
    state_machine_tasks state_machine_scoreinfos state_machine_attempts \
    state_machine_selected_hits state_machine_cpu_align_attempts \
    state_machine_fallbacks state_machine_triplex_mismatches \
    gasal2_score_requests gasal2_score_batches gasal2_score_wait_seconds \
    realpath_extend_seconds realpath_extend_align_attempts \
    state_machine_total_seconds state_machine_select_seconds \
    state_machine_cpu_align_seconds state_machine_convert_seconds \
    baseline_wall candidate_wall; do
    if [[ -z "${!name}" ]]; then
      echo "missing metric $name for $workload first${limit}" >&2
      exit 1
    fi
  done

  if [[ "$scoreinfo_mismatches" != "0" ||
        "$realpath_fallbacks" != "0" ||
        "$length_guard_fallbacks" != "0" ||
        "$state_machine_fallbacks" != "0" ||
        "$state_machine_triplex_mismatches" != "0" ]]; then
    echo "$workload first${limit} failed clean shadow gate: scoreinfo=$scoreinfo_mismatches realpath_fallbacks=$realpath_fallbacks length_guard=$length_guard_fallbacks state_machine_fallbacks=$state_machine_fallbacks triplex=$state_machine_triplex_mismatches" >&2
    exit 1
  fi

  candidate_vs_baseline="$(
    awk -v base="$baseline_wall" -v cand="$candidate_wall" 'BEGIN {
      if ((base + 0.0) <= 0.0 || (cand + 0.0) <= 0.0) {
        print "na";
      } else {
        printf "%.6f", (base + 0.0) / (cand + 0.0);
      }
    }'
  )"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$workload" \
    "$limit" \
    "$probe_tasks" \
    "$digest" \
    "$tasks" \
    "$scoreinfo_mismatches" \
    "$realpath_fallbacks" \
    "$length_guard_fallbacks" \
    "$state_machine_tasks" \
    "$state_machine_scoreinfos" \
    "$state_machine_attempts" \
    "$state_machine_selected_hits" \
    "$state_machine_cpu_align_attempts" \
    "$state_machine_fallbacks" \
    "$state_machine_triplex_mismatches" \
    "$gasal2_score_requests" \
    "$gasal2_score_batches" \
    "$gasal2_score_wait_seconds" \
    "$realpath_extend_seconds" \
    "$realpath_extend_align_attempts" \
    "$state_machine_total_seconds" \
    "$state_machine_select_seconds" \
    "$state_machine_cpu_align_seconds" \
    "$state_machine_convert_seconds" \
    "$baseline_wall" \
    "$candidate_wall" \
    "$candidate_vs_baseline" \
    >>"$summary"
}

for limit in $NEAT1_RECORD_LIMITS; do
  run_case \
    "neat1" \
    "$limit" \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"
done

for limit in $MALAT1_RECORD_LIMITS; do
  run_case \
    "malat1" \
    "$limit" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"
done

cat "$summary"
