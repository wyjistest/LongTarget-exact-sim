#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/calc_score_cuda_telemetry"
NORMAL_OUTPUT_DIR="$WORK_DIR/normal_output"
EMPTY_OUTPUT_DIR="$WORK_DIR/empty_output"
NORMAL_STDERR_LOG="$WORK_DIR/normal.stderr.log"
EMPTY_STDERR_LOG="$WORK_DIR/empty.stderr.log"
EMPTY_DNA="$WORK_DIR/empty_dna.fa"
EMPTY_RNA="$WORK_DIR/empty_rna.fa"

mkdir -p "$WORK_DIR"
rm -rf "$NORMAL_OUTPUT_DIR" "$EMPTY_OUTPUT_DIR"
mkdir -p "$NORMAL_OUTPUT_DIR" "$EMPTY_OUTPUT_DIR"
rm -f "$NORMAL_STDERR_LOG" "$EMPTY_STDERR_LOG" "$EMPTY_DNA" "$EMPTY_RNA"

cd "$ROOT_DIR"

require_field()
{
  log_file="$1"
  pattern="$2"
  grep -Eq "$pattern" "$log_file"
}

require_uint_gt_zero()
{
  log_file="$1"
  key="$2"
  value="$(sed -n "s/^benchmark\\.$key=//p" "$log_file" | tail -n 1)"
  awk "BEGIN { exit !(\"$value\" + 0 > 0) }"
}

require_uint_eq()
{
  log_file="$1"
  key="$2"
  expected="$3"
  value="$(sed -n "s/^benchmark\\.$key=//p" "$log_file" | tail -n 1)"
  test "$value" = "$expected"
}

check_common_fields()
{
  log_file="$1"
  require_field "$log_file" '^benchmark\.calc_score_backend=(cpu|cuda|mixed|skipped)$'
  require_field "$log_file" '^benchmark\.calc_score_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_tasks_total=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_tasks=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cpu_fallback_tasks=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_target_h2d_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_permutation_h2d_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_kernel_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_score_d2h_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_sync_wait_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_host_encode_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_host_shuffle_plan_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_host_mle_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_enabled=[01]$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_shadow_enabled=[01]$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_used_groups=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_fallbacks=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_shadow_comparisons=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_shadow_mismatches=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_kernel_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_score_d2h_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pipeline_v2_host_reduce_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_groups=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_pairs=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_target_bytes_h2d=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_permutation_bytes_h2d=[0-9]+$'
  require_field "$log_file" '^benchmark\.calc_score_cuda_score_bytes_d2h=[0-9]+$'
}

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 1 -O "$NORMAL_OUTPUT_DIR" >/dev/null 2>"$NORMAL_STDERR_LOG"

check_common_fields "$NORMAL_STDERR_LOG"
require_uint_gt_zero "$NORMAL_STDERR_LOG" "calc_score_tasks_total"

cat >"$EMPTY_DNA" <<'EOF_DNA'
>test|chr1|1-
AAAAAAAA
EOF_DNA

cat >"$EMPTY_RNA" <<'EOF_RNA'
>empty_rna
ACGTACGT
EOF_RNA

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
"$TARGET" -f1 "$EMPTY_DNA" -f2 "$EMPTY_RNA" -r 1 -O "$EMPTY_OUTPUT_DIR" >/dev/null 2>"$EMPTY_STDERR_LOG"

check_common_fields "$EMPTY_STDERR_LOG"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_tasks_total" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_groups" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pairs" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_target_bytes_h2d" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_permutation_bytes_h2d" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_score_bytes_d2h" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_enabled" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_enabled" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_used_groups" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_fallbacks" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_comparisons" "0"
require_uint_eq "$EMPTY_STDERR_LOG" "calc_score_cuda_pipeline_v2_shadow_mismatches" "0"
