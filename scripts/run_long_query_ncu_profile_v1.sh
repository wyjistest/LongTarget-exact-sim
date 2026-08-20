#!/usr/bin/env bash
set -euo pipefail

NCU=${NCU:-/opt/nvidia/nsight-compute/2024.2.1/ncu}
SECTIONS=(
  LaunchStats
  Occupancy
  SpeedOfLight
  MemoryWorkloadAnalysis
  ComputeWorkloadAnalysis
  SchedulerStats
  WarpStateStats
  SourceCounters
)

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

required_env() {
  local name=$1
  [[ -n ${!name:-} ]] || fail "missing environment variable: $name"
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

profiling_admin_only() {
  local params=/proc/driver/nvidia/params
  local value=
  if [[ -r $params ]]; then
    value=$(awk -F': *' '$1 == "RmProfilingAdminOnly" {print $2}' "$params")
  fi
  if [[ $value == 0 || $value == 1 ]]; then
    printf '%s\n' "$value"
  else
    printf 'unknown\n'
  fi
}

preflight() {
  [[ -x $NCU ]] || fail "Nsight Compute is not executable: $NCU"
  local version
  version=$($NCU --version | awk '/Version/{print $2; exit}')
  [[ -n $version ]] || fail "cannot determine Nsight Compute version"
  local available
  available=$($NCU --list-sections)
  local section
  for section in "${SECTIONS[@]}"; do
    grep -Eq "^${section}[[:space:]]" <<<"$available" || \
      fail "missing Nsight Compute section: $section"
  done
  local admin_only
  admin_only=$(profiling_admin_only)
  printf 'ncu_path=%s\n' "$NCU"
  printf 'ncu_version=%s\n' "$version"
  printf 'sections=%s\n' "$(IFS=,; printf '%s' "${SECTIONS[*]}")"
  printf 'profiling_admin_only=%s\n' "$admin_only"
  if [[ $EUID -eq 0 || $admin_only == 0 ]]; then
    printf 'execution_authorized=1\n'
    printf 'execution_blocker=none\n'
  else
    printf 'execution_authorized=0\n'
    if [[ $admin_only == 1 ]]; then
      printf 'execution_blocker=hardware_counters_require_admin\n'
    else
      printf 'execution_blocker=cannot_verify_hardware_counter_permission\n'
    fi
  fi
}

if [[ ${1:-} == --preflight ]]; then
  preflight
  exit 0
fi

[[ ${1:-} == --execute ]] || \
  fail "usage: $0 --preflight | --execute main|f1-round0"
STAGE=${2:-}
case $STAGE in
  main)
    KERNEL_REGEX='regex:.*prealign_cuda_column_max_legacy_byte_batch_kernel.*'
    ;;
  f1-round0)
    KERNEL_REGEX='regex:.*prealign_cuda_exact_attempt_forward_byte_kernel.*'
    ;;
  *)
    fail "unknown stage: $STAGE"
    ;;
esac

preflight_output=$(preflight)
printf '%s\n' "$preflight_output"
grep -Fxq 'execution_authorized=1' <<<"$preflight_output" || \
  fail "Nsight Compute hardware counters are not authorized"

for name in BIN BIN_SHA256 SOURCE_COMMIT TARGET TARGET_SHA256 QUERY QUERY_SHA256 \
  EXPECTED_TFOSORTED_SHA256 WORK GPU CPU_SET GPU_UUID RESOURCE_LOCK
do
  required_env "$name"
done
[[ -x $BIN ]] || fail "binary is not executable: $BIN"
[[ -f $TARGET ]] || fail "target is missing: $TARGET"
[[ -f $QUERY ]] || fail "query is missing: $QUERY"
[[ ! -e $WORK ]] || fail "immutable work directory already exists: $WORK"
[[ $(sha256_file "$BIN") == "$BIN_SHA256" ]] || fail "binary digest drift"
[[ $(sha256_file "$TARGET") == "$TARGET_SHA256" ]] || fail "target digest drift"
[[ $(sha256_file "$QUERY") == "$QUERY_SHA256" ]] || fail "query digest drift"
observed_uuid=$(nvidia-smi --id="$GPU" --query-gpu=uuid --format=csv,noheader | tr -d '[:space:]')
[[ $observed_uuid == "$GPU_UUID" ]] || fail "GPU UUID drift"
if nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -Eq '[0-9]'; then
  fail "a CUDA compute process is already active"
fi

mkdir -p "$(dirname "$RESOURCE_LOCK")"
exec 9>"$RESOURCE_LOCK"
flock -n 9 || fail "GPU resource lock is already held: $RESOURCE_LOCK"
mkdir -p "$WORK/runtime_output"

{
  printf 'field\tvalue\n'
  printf 'schema_version\tlong_query_ncu_profile_plan_v1\n'
  printf 'stage\t%s\n' "$STAGE"
  printf 'source_commit\t%s\n' "$SOURCE_COMMIT"
  printf 'binary_sha256\t%s\n' "$BIN_SHA256"
  printf 'target_sha256\t%s\n' "$TARGET_SHA256"
  printf 'query_sha256\t%s\n' "$QUERY_SHA256"
  printf 'expected_tfosorted_sha256\t%s\n' "$EXPECTED_TFOSORTED_SHA256"
  printf 'gpu\t%s\n' "$GPU"
  printf 'gpu_uuid\t%s\n' "$GPU_UUID"
  printf 'cpu_set\t%s\n' "$CPU_SET"
  printf 'kernel_filter\t%s\n' "$KERNEL_REGEX"
  printf 'started_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$WORK/plan.tsv"

section_args=()
for section in "${SECTIONS[@]}"; do
  section_args+=(--section "$section")
done

set +e
taskset -c "$CPU_SET" env \
  CUDA_VISIBLE_DEVICES="$GPU" \
  OMP_NUM_THREADS=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_WRITE_TFOSORTED_LITE=0 \
  FASIM_VERBOSE=0 \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ENABLE_PREALIGN_CUDA=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_MINSCORE_UINT8_GLOBAL=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_MINSCORE_UINT8_GLOBAL_MIN_QUERY_LENGTH=8000 \
  FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE=0 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_LEGACY_CPU_REPLAY=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_ROUND_PROFILE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=0 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO=1 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=0 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_REPORT="$WORK/f1.tsv" \
  "$NCU" \
    --target-processes application-only \
    --replay-mode kernel \
    --kernel-name-base function \
    --kernel-name "$KERNEL_REGEX" \
    --launch-count 1 \
    --cache-control all \
    --clock-control base \
    --apply-rules no \
    "${section_args[@]}" \
    --export "$WORK/profile" \
    --force-overwrite \
    "$BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 \
    -O "$WORK/runtime_output" >"$WORK/stdout.log" 2>"$WORK/stderr.log"
exit_code=$?
set -e
printf 'exit_code\t%s\ncompleted_utc\t%s\n' \
  "$exit_code" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$WORK/status.tsv"
[[ $exit_code -eq 0 ]] || fail "Nsight Compute run exited with $exit_code"

mapfile -d '' artifacts < <(
  find "$WORK/runtime_output" -maxdepth 1 -type f -name '*-TFOsorted' -print0
)
[[ ${#artifacts[@]} -eq 1 && -s ${artifacts[0]} ]] || \
  fail "expected one nonempty TFOsorted artifact"
[[ $(sha256_file "${artifacts[0]}") == "$EXPECTED_TFOSORTED_SHA256" ]] || \
  fail "profile run output is not exact"
[[ -s $WORK/f1.tsv ]] || fail "F1 report is missing"
grep -Fxq 'finished normally' "$WORK/stdout.log" || fail "normal completion marker is missing"
grep -Fxq 'benchmark.fasim_long_query_gpu_consumer_f1_pipeline_failures=0' \
  "$WORK/stderr.log" || fail "F1 technical failure marker is missing"
grep -Fxq 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches=0' \
  "$WORK/stderr.log" || fail "scoreInfo fallback marker is missing"
[[ -s $WORK/profile.ncu-rep ]] || fail "Nsight Compute report is missing"
"$NCU" --import "$WORK/profile.ncu-rep" --csv --page raw \
  >"$WORK/profile.raw.csv"
sha256sum "${artifacts[0]}" "$WORK/f1.tsv" "$WORK/profile.ncu-rep" \
  "$WORK/profile.raw.csv" >"$WORK/checksums.sha256"
printf 'profile_complete=1\n'
