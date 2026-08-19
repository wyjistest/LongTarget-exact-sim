#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_f1_scoreinfo_pipeline_v1}"
WORK="${WORK:-$ROOT/.tmp/long_query_consumer_f1_scoreinfo_pipeline_v1}"
QUERY="${QUERY:-/data/wenyujianData/linjieData/longtarget_runs/segment_owner_authority_probe_v1/inputs/short_header_cpu_authority/ENSG00000229613.fa}"
TARGET="${TARGET:-$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa}"
BUILD="${BUILD:-1}"
RUN_AUTO_OFF_CHECK="${RUN_AUTO_OFF_CHECK:-1}"

if [[ ! -s "$TARGET" && "$TARGET" == "$ROOT/.tmp/"* ]]; then
  SHARED_TARGET="$(cd "$ROOT/.." && pwd)/LongTarget-exact-sim/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"
  if [[ -s "$SHARED_TARGET" ]]; then
    TARGET="$SHARED_TARGET"
  fi
fi

[[ -s "$QUERY" ]] || { echo "missing query: $QUERY" >&2; exit 1; }
[[ -s "$TARGET" ]] || { echo "missing target: $TARGET" >&2; exit 1; }

if [[ "$BUILD" != 0 ]]; then
  BUILD_CPPFLAGS="${CPPFLAGS:-} -DFASIM_WITH_SSW_FORWARD_CONTINUATION"
  GASAL2_DIR_VALUE="${GASAL2_DIR:-$ROOT/.tmp/GASAL2}"
  if [[ ! -f "$GASAL2_DIR_VALUE/Makefile" && -f "$ROOT/../LongTarget-exact-sim/.tmp/GASAL2/Makefile" ]]; then
    GASAL2_DIR_VALUE="$ROOT/../LongTarget-exact-sim/.tmp/GASAL2"
  fi
  make -C "$ROOT" -j2 build-fasim-gasal2 \
    FASIM_GASAL2_TARGET="$BIN" \
    CPPFLAGS="$BUILD_CPPFLAGS" \
    NVCC="${NVCC:-/usr/local/cuda/bin/nvcc}" \
    CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}" \
    GASAL2_DIR="$GASAL2_DIR_VALUE"
fi
[[ -x "$BIN" ]] || { echo "missing executable: $BIN" >&2; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK"

expect_startup_failure()
{
  local name="$1"
  local expected="$2"
  shift 2
  mkdir -p "$WORK/$name/out"
  set +e
  env "$@" "$BIN" \
    -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 -O "$WORK/$name/out" \
    >"$WORK/$name/stdout.log" 2>"$WORK/$name/stderr.log"
  local status=$?
  set -e
  if [[ "$status" -eq 0 ]]; then
    echo "$name unexpectedly succeeded" >&2
    exit 1
  fi
  grep -Fq "$expected" "$WORK/$name/stderr.log"
  if find "$WORK/$name/out" -type f -name '*-TFOsorted*' -print -quit | grep -q .; then
    echo "$name materialized output before failing" >&2
    exit 1
  fi
}

expect_startup_failure \
  pipeline_without_scheduler \
  "FASIM F1 pipeline requires the F1 scheduler" \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=0

expect_startup_failure \
  pipeline_with_phase_timing \
  "FASIM F1 pipeline is incompatible with shared phase timing state" \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1

env \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=2 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=0 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO=1 \
  FASIM_LONG_QUERY_TASK_DUPLICATE_AUDIT=1 \
  BIN="$BIN" \
  WORK="$WORK/pipeline" \
  QUERY="$QUERY" \
  TARGET="$TARGET" \
  BUILD=0 \
  bash "$ROOT/scripts/check_long_query_consumer_f1_scheduler_v1.sh"

PIPELINE_LOG="$WORK/pipeline/stderr.log"
grep -Eq '^benchmark\.fasim_long_query_gpu_consumer_f1_pipeline_active=1$' "$PIPELINE_LOG"
grep -Eq '^benchmark\.fasim_long_query_gpu_consumer_f1_pipeline_failures=0$' "$PIPELINE_LOG"
grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared=1$' "$PIPELINE_LOG"
grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_requested=1$' "$PIPELINE_LOG"
grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_fallbacks=0$' "$PIPELINE_LOG"
grep -Eq '^benchmark\.fasim_long_query_task_duplicate_audit_duplicate_tasks=0$' "$PIPELINE_LOG"

pipeline_launches="$(awk -F= '$1 == "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_launches" {value=$2} END {print value}' "$PIPELINE_LOG")"
pipeline_commits="$(awk -F= '$1 == "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_commits" {value=$2} END {print value}' "$PIPELINE_LOG")"
duplicate_tasks="$(awk -F= '$1 == "benchmark.fasim_long_query_task_duplicate_audit_tasks" {value=$2} END {print value}' "$PIPELINE_LOG")"
unique_tasks="$(awk -F= '$1 == "benchmark.fasim_long_query_task_duplicate_audit_unique_tasks" {value=$2} END {print value}' "$PIPELINE_LOG")"
cells_before="$(awk -F= '$1 == "benchmark.fasim_long_query_task_duplicate_audit_cells_before" {value=$2} END {print value}' "$PIPELINE_LOG")"
cells_after="$(awk -F= '$1 == "benchmark.fasim_long_query_task_duplicate_audit_cells_after" {value=$2} END {print value}' "$PIPELINE_LOG")"

[[ -n "$pipeline_launches" && "$pipeline_launches" -gt 0 ]]
[[ "$pipeline_commits" == "$pipeline_launches" ]]
[[ -n "$duplicate_tasks" && "$duplicate_tasks" -gt 0 ]]
[[ "$unique_tasks" == "$duplicate_tasks" ]]
[[ -n "$cells_before" && "$cells_before" -gt 0 ]]
[[ "$cells_after" == "$cells_before" ]]

if [[ "$RUN_AUTO_OFF_CHECK" != 0 ]]; then
  env \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=0 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=2 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=0 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO=0 \
    BIN="$BIN" \
    WORK="$WORK/auto_off" \
    QUERY="$QUERY" \
    TARGET="$TARGET" \
    BUILD=0 \
    bash "$ROOT/scripts/check_long_query_consumer_f1_scheduler_v1.sh"

  AUTO_OFF_LOG="$WORK/auto_off/stderr.log"
  grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared=0$' "$AUTO_OFF_LOG"
  grep -Eq '^benchmark\.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_requested=0$' "$AUTO_OFF_LOG"
fi

echo "F1 scoreInfo/pipeline checks passed"
echo "pipeline launches/commits: $pipeline_launches/$pipeline_commits"
echo "duplicate audit unique/tasks: $unique_tasks/$duplicate_tasks"
