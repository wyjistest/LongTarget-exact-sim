#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/calc_score_cuda_v2_shadow"
OUTPUT_DIR="$WORK_DIR/output"
STDERR_LOG="$WORK_DIR/stderr.log"

mkdir -p "$WORK_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
rm -f "$STDERR_LOG"

cd "$ROOT_DIR"

require_uint_eq()
{
  log_file="$1"
  key="$2"
  expected="$3"
  value="$(sed -n "s/^benchmark\\.$key=//p" "$log_file" | tail -n 1)"
  test "$value" = "$expected"
}

require_uint_gt_zero()
{
  log_file="$1"
  key="$2"
  value="$(sed -n "s/^benchmark\\.$key=//p" "$log_file" | tail -n 1)"
  awk "BEGIN { exit !(\"$value\" + 0 > 0) }"
}

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2=1 \
LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW=1 \
LONGTARGET_CUDA_VALIDATE=1 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 1 -O "$OUTPUT_DIR" >/dev/null 2>"$STDERR_LOG"

require_uint_eq "$STDERR_LOG" "calc_score_cuda_pipeline_v2_enabled" "1"
require_uint_eq "$STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_enabled" "1"
require_uint_gt_zero "$STDERR_LOG" "calc_score_cuda_pipeline_v2_used_groups"
require_uint_eq "$STDERR_LOG" "calc_score_cuda_pipeline_v2_fallbacks" "0"
require_uint_gt_zero "$STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_comparisons"
require_uint_eq "$STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_mismatches" "0"
require_uint_gt_zero "$STDERR_LOG" "calc_score_cuda_pipeline_v2_kernel_seconds"
require_uint_gt_zero "$STDERR_LOG" "calc_score_cuda_pipeline_v2_score_d2h_seconds"
require_uint_gt_zero "$STDERR_LOG" "calc_score_cuda_pipeline_v2_host_reduce_seconds"
