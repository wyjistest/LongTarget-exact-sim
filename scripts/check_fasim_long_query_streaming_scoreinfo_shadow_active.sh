#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_shadow_active"}"
BUILD_BIN="${BUILD_BIN:-1}"
EXTRA_SHADOW_ENV="${EXTRA_SHADOW_ENV:-}"
EXPECTED_SCOREINFO_MISMATCHES="${EXPECTED_SCOREINFO_MISMATCHES:-1}"
EXPECTED_DECISION="${EXPECTED_DECISION:-streaming_scoreinfo_shadow_mismatch}"
EXPECTED_LEGACY_BYTE_SHARED="${EXPECTED_LEGACY_BYTE_SHARED:-}"
EXPECTED_GPU_MINSCORE_REQUESTED="${EXPECTED_GPU_MINSCORE_REQUESTED:-}"
EXPECTED_GPU_MINSCORE_ACTIVE="${EXPECTED_GPU_MINSCORE_ACTIVE:-}"
EXPECTED_GPU_MINSCORE_HOT="${EXPECTED_GPU_MINSCORE_HOT:-}"
EXPECTED_GPU_MINSCORE_USED="${EXPECTED_GPU_MINSCORE_USED:-}"
EXPECTED_CPU_SCOREINFO_GROUPS="${EXPECTED_CPU_SCOREINFO_GROUPS:-positive}"
EXPECTED_CPU_PREALIGN_SECONDS="${EXPECTED_CPU_PREALIGN_SECONDS:-positive}"
EXPECTED_COMPARE_SECONDS="${EXPECTED_COMPARE_SECONDS:-positive}"
WORKLOAD_NAME="${WORKLOAD_NAME:-MALAT1}"
RECORD_LIMIT="${RECORD_LIMIT:-${MALAT1_RECORD_LIMIT:-8}}"
RNA_INPUT="${RNA_INPUT:-${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}}"
DNA_INPUT="${DNA_INPUT:-${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}}"
EXPECTED_QUERY_LEN="${EXPECTED_QUERY_LEN:-8708}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing $WORKLOAD_NAME inputs" >&2
  exit 1
fi

sample="$WORK/inputs/${WORKLOAD_NAME,,}_first${RECORD_LIMIT}.fa"
awk -v limit="$RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"

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
    -f2 "$RNA_INPUT" \
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
# shellcheck disable=SC2086
run_fasim "$candidate_dir" \
  $EXTRA_SHADOW_ENV \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "streaming scoreInfo active shadow changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

requested="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested)"
active="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active)"
unsupported="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported)"
query_len="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_query_len)"
tasks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
gpu_batches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_batches)"
gpu_tasks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_tasks)"
gpu_scoreinfo_groups="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups)"
cpu_scoreinfo_groups="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups)"
scoreinfo_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
candidate_missing="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing)"
candidate_extra="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra)"
total_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds)"
minscore_cache_hits="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_hits)"
minscore_cache_misses="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_misses)"
minscore_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds)"
gpu_call_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds)"
kernel_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds)"
validation_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds)"
validation_minscore_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds)"
cpu_prealign_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds)"
compare_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds)"
decision="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"
legacy_byte_shared="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared)"
gpu_minscore_requested="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_requested)"
gpu_minscore_active="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_active)"
gpu_minscore_hot="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot)"
gpu_minscore_used="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used)"
gpu_minscore_fallbacks="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks)"
gpu_minscore_score_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches)"
gpu_minscore_min_score_mismatches="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches)"
gpu_minscore_wall_seconds="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds)"
gpu_minscore_error="$(metric "$candidate_dir" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_error)"

for value_name in \
  requested active unsupported query_len tasks gpu_batches gpu_tasks gpu_scoreinfo_groups \
  cpu_scoreinfo_groups scoreinfo_mismatches candidate_missing candidate_extra total_seconds \
  minscore_cache_hits minscore_cache_misses minscore_seconds gpu_call_seconds \
  kernel_seconds validation_seconds validation_minscore_seconds cpu_prealign_seconds \
  compare_seconds decision legacy_byte_shared gpu_minscore_requested \
  gpu_minscore_active gpu_minscore_hot gpu_minscore_used \
  gpu_minscore_fallbacks gpu_minscore_score_mismatches \
  gpu_minscore_min_score_mismatches gpu_minscore_wall_seconds gpu_minscore_error; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing streaming scoreInfo active shadow metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$requested" != "1" || "$active" != "1" || "$unsupported" != "0" ]]; then
  echo "expected requested=1 active=1 unsupported=0, got requested=$requested active=$active unsupported=$unsupported" >&2
  exit 1
fi
if [[ "$query_len" != "$EXPECTED_QUERY_LEN" ]]; then
  echo "expected $WORKLOAD_NAME query_len=$EXPECTED_QUERY_LEN, got $query_len" >&2
  exit 1
fi
if [[ "$tasks" -le 0 || "$gpu_batches" -le 0 || "$gpu_tasks" -le 0 ]]; then
  echo "expected active GPU task accounting, got tasks=$tasks gpu_batches=$gpu_batches gpu_tasks=$gpu_tasks" >&2
  exit 1
fi
if [[ "$gpu_scoreinfo_groups" -le 0 ]]; then
  echo "expected GPU scoreInfo groups, got gpu=$gpu_scoreinfo_groups" >&2
  exit 1
fi
if [[ "$EXPECTED_CPU_SCOREINFO_GROUPS" == "positive" && "$cpu_scoreinfo_groups" -le 0 ]]; then
  echo "expected positive CPU scoreInfo comparison groups, got cpu=$cpu_scoreinfo_groups" >&2
  exit 1
fi
if [[ "$EXPECTED_CPU_SCOREINFO_GROUPS" != "positive" && "$cpu_scoreinfo_groups" != "$EXPECTED_CPU_SCOREINFO_GROUPS" ]]; then
  echo "expected CPU scoreInfo groups=$EXPECTED_CPU_SCOREINFO_GROUPS, got cpu=$cpu_scoreinfo_groups" >&2
  exit 1
fi
if [[ "$scoreinfo_mismatches" != "$EXPECTED_SCOREINFO_MISMATCHES" || "$candidate_missing" != "0" || "$candidate_extra" != "0" ]]; then
  echo "expected streaming scoreInfo checkpoint scoreinfo=$EXPECTED_SCOREINFO_MISMATCHES missing=0 extra=0, got scoreinfo=$scoreinfo_mismatches missing=$candidate_missing extra=$candidate_extra" >&2
  exit 1
fi
if [[ "$total_seconds" == "0" || "$kernel_seconds" == "0" ]]; then
  echo "expected positive GPU timing, got total=$total_seconds kernel=$kernel_seconds" >&2
  exit 1
fi
if [[ $((minscore_cache_hits + minscore_cache_misses)) -ne "$tasks" ]]; then
  echo "expected minScore cache accounting to equal tasks, got hits=$minscore_cache_hits misses=$minscore_cache_misses tasks=$tasks" >&2
  exit 1
fi
for timing_name in gpu_call_seconds validation_seconds; do
  timing_value="${!timing_name}"
  awk -v name="$timing_name" -v value="$timing_value" 'BEGIN {
    if ((value + 0.0) <= 0.0) {
      printf("expected positive streaming scoreInfo timing %s, got %s\n", name, value) > "/dev/stderr";
      exit 1;
    }
  }'
done
if [[ "$EXPECTED_CPU_PREALIGN_SECONDS" == "positive" ]]; then
  awk -v value="$cpu_prealign_seconds" 'BEGIN {
    if ((value + 0.0) <= 0.0) {
      printf("expected positive streaming scoreInfo timing cpu_prealign_seconds, got %s\n", value) > "/dev/stderr";
      exit 1;
    }
  }'
elif [[ "$EXPECTED_CPU_PREALIGN_SECONDS" != "$cpu_prealign_seconds" ]]; then
  echo "expected cpu_prealign_seconds=$EXPECTED_CPU_PREALIGN_SECONDS, got $cpu_prealign_seconds" >&2
  exit 1
fi
if [[ "$EXPECTED_COMPARE_SECONDS" == "positive" ]]; then
  awk -v value="$compare_seconds" 'BEGIN {
    if ((value + 0.0) <= 0.0) {
      printf("expected positive streaming scoreInfo timing compare_seconds, got %s\n", value) > "/dev/stderr";
      exit 1;
    }
  }'
elif [[ "$EXPECTED_COMPARE_SECONDS" != "$compare_seconds" ]]; then
  echo "expected compare_seconds=$EXPECTED_COMPARE_SECONDS, got $compare_seconds" >&2
  exit 1
fi
awk -v value="$minscore_seconds" 'BEGIN {
  if ((value + 0.0) < 0.0) {
    printf("expected nonnegative minscore_seconds, got %s\n", value) > "/dev/stderr";
    exit 1;
  }
}'
awk -v value="$validation_minscore_seconds" 'BEGIN {
  if ((value + 0.0) < 0.0) {
    printf("expected nonnegative validation_minscore_seconds, got %s\n", value) > "/dev/stderr";
    exit 1;
  }
}'
if [[ "$decision" != "$EXPECTED_DECISION" ]]; then
  echo "unexpected streaming scoreInfo active decision=$decision expected=$EXPECTED_DECISION" >&2
  exit 1
fi
if [[ -n "$EXPECTED_LEGACY_BYTE_SHARED" && "$legacy_byte_shared" != "$EXPECTED_LEGACY_BYTE_SHARED" ]]; then
  echo "unexpected legacy-byte shared mode=$legacy_byte_shared expected=$EXPECTED_LEGACY_BYTE_SHARED" >&2
  exit 1
fi
if [[ -n "$EXPECTED_GPU_MINSCORE_REQUESTED" && "$gpu_minscore_requested" != "$EXPECTED_GPU_MINSCORE_REQUESTED" ]]; then
  echo "unexpected GPU minScore requested=$gpu_minscore_requested expected=$EXPECTED_GPU_MINSCORE_REQUESTED" >&2
  exit 1
fi
if [[ -n "$EXPECTED_GPU_MINSCORE_ACTIVE" && "$gpu_minscore_active" != "$EXPECTED_GPU_MINSCORE_ACTIVE" ]]; then
  echo "unexpected GPU minScore active=$gpu_minscore_active expected=$EXPECTED_GPU_MINSCORE_ACTIVE" >&2
  exit 1
fi
if [[ -n "$EXPECTED_GPU_MINSCORE_HOT" && "$gpu_minscore_hot" != "$EXPECTED_GPU_MINSCORE_HOT" ]]; then
  echo "unexpected GPU minScore hot=$gpu_minscore_hot expected=$EXPECTED_GPU_MINSCORE_HOT" >&2
  exit 1
fi
if [[ -n "$EXPECTED_GPU_MINSCORE_USED" && "$gpu_minscore_used" != "$EXPECTED_GPU_MINSCORE_USED" ]]; then
  echo "unexpected GPU minScore used=$gpu_minscore_used expected=$EXPECTED_GPU_MINSCORE_USED" >&2
  exit 1
fi

printf 'digest=%s\n' "$candidate_digest"
printf 'requested=%s active=%s unsupported=%s\n' "$requested" "$active" "$unsupported"
printf 'legacy_byte_shared=%s\n' "$legacy_byte_shared"
printf 'gpu_minscore requested=%s active=%s hot=%s used=%s fallbacks=%s score_mismatches=%s min_score_mismatches=%s wall_seconds=%s error=%s\n' \
  "$gpu_minscore_requested" "$gpu_minscore_active" "$gpu_minscore_hot" "$gpu_minscore_used" "$gpu_minscore_fallbacks" \
  "$gpu_minscore_score_mismatches" "$gpu_minscore_min_score_mismatches" "$gpu_minscore_wall_seconds" "$gpu_minscore_error"
printf 'query_len=%s tasks=%s gpu_batches=%s gpu_tasks=%s\n' "$query_len" "$tasks" "$gpu_batches" "$gpu_tasks"
printf 'gpu_scoreinfo_groups=%s cpu_scoreinfo_groups=%s\n' "$gpu_scoreinfo_groups" "$cpu_scoreinfo_groups"
printf 'scoreinfo_mismatches=%s candidate_missing=%s candidate_extra=%s\n' "$scoreinfo_mismatches" "$candidate_missing" "$candidate_extra"
printf 'total_seconds=%s minscore_cache_hits=%s minscore_cache_misses=%s minscore_seconds=%s gpu_call_seconds=%s kernel_seconds=%s\n' \
  "$total_seconds" "$minscore_cache_hits" "$minscore_cache_misses" "$minscore_seconds" "$gpu_call_seconds" "$kernel_seconds"
printf 'validation_seconds=%s validation_minscore_seconds=%s cpu_prealign_seconds=%s compare_seconds=%s\n' \
  "$validation_seconds" "$validation_minscore_seconds" "$cpu_prealign_seconds" "$compare_seconds"
printf 'decision=%s\n' "$decision"
printf 'ok\n'
