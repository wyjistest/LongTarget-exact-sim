#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_result_boundary_smoke"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

metric_value() {
  local file="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/boundary"

run_case() {
  local label="$1"
  local boundary_enabled="$2"
  local out_dir="$WORK/$label"
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
    FASIM_ALIGN_GASAL2_STREAMS=3 \
    FASIM_ALIGN_GASAL2_BATCH=20000 \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_FLUSH_RESULT_BOUNDARY_SHADOW="$boundary_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0
run_case boundary 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
boundary_lite="$(find "$WORK/boundary" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$boundary_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$boundary_lite"; then
  echo "result boundary changed lite output" >&2
  exit 1
fi

stderr="$WORK/boundary/stderr.log"
requested="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_requested)"
active="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_active)"
disabled_reason="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_disabled_reason)"
flushes="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_flushes)"
materialized="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_materialized_flushes)"
consumed="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_finalizer_consumed_result_flushes)"
owned_tasks="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_task_backing_owned_flushes)"
owned_groups="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_score_group_mapping_owned_flushes)"
owned_selected="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_selected_by_task_owned_flushes)"
selected_alignments="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_selected_alignments)"
result_bytes="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_result_bytes)"
traceback_bytes="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_traceback_bytes)"
decision="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_result_boundary_decision)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "unexpected requested/active: requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$disabled_reason" != "none" ]]; then
  echo "unexpected disabled reason: $disabled_reason" >&2
  exit 1
fi
if [[ "$decision" != "go_pure_finalizer_extraction_next" ]]; then
  echo "unexpected decision: $decision" >&2
  exit 1
fi
if (( flushes < 1 || materialized != flushes || consumed != materialized )); then
  echo "flush accounting mismatch: flushes=$flushes materialized=$materialized consumed=$consumed" >&2
  exit 1
fi
if (( owned_tasks != materialized || owned_groups != materialized || owned_selected != materialized )); then
  echo "owned snapshot accounting mismatch" >&2
  exit 1
fi
if (( selected_alignments < 1 || result_bytes < 1 || traceback_bytes < 1 )); then
  echo "expected material selected result bytes" >&2
  exit 1
fi

{
  printf 'result_boundary_requested=%s\n' "$requested"
  printf 'result_boundary_active=%s\n' "$active"
  printf 'result_boundary_disabled_reason=%s\n' "$disabled_reason"
  printf 'result_boundary_flushes=%s\n' "$flushes"
  printf 'result_boundary_materialized_flushes=%s\n' "$materialized"
  printf 'result_boundary_finalizer_consumed_result_flushes=%s\n' "$consumed"
  printf 'result_boundary_selected_alignments=%s\n' "$selected_alignments"
  printf 'result_boundary_result_bytes=%s\n' "$result_bytes"
  printf 'result_boundary_traceback_bytes=%s\n' "$traceback_bytes"
  printf 'result_boundary_decision=%s\n' "$decision"
  printf 'lite_sha256=%s\n' "$(sha256sum "$boundary_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_result_boundary_smoke: ok"
