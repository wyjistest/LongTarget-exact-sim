#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_nvtx"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_nvtx_trace_smoke"}"
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
    make build-fasim-gasal2-nvtx \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_NVTX_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/nvtx" "$WORK/baseline_no_probe" "$WORK/two_slot_nvtx"

run_case() {
  local label="$1"
  local nvtx_enabled="$2"
  local two_slot_enabled="${3:-0}"
  local archive_probe="${4:-1}"
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
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE="$archive_probe" \
    FASIM_GASAL2_NVTX_TRACE="$nvtx_enabled" \
    FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP="$two_slot_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0 0 1
run_case nvtx 1 0 1
run_case baseline_no_probe 0 0 0
run_case two_slot_nvtx 1 1 0

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
nvtx_lite="$(find "$WORK/nvtx" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
baseline_no_probe_lite="$(find "$WORK/baseline_no_probe" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
two_slot_lite="$(find "$WORK/two_slot_nvtx" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$nvtx_lite" || -z "$baseline_no_probe_lite" || -z "$two_slot_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$nvtx_lite"; then
  echo "NVTX trace changed lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_no_probe_lite" "$two_slot_lite"; then
  echo "two-slot NVTX trace changed lite output" >&2
  exit 1
fi

requested="$(metric_value "$WORK/nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_requested)"
compiled="$(metric_value "$WORK/nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_compiled)"
active="$(metric_value "$WORK/nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_active)"
ranges="$(metric_value "$WORK/nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_ranges)"
decision="$(metric_value "$WORK/nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_decision)"
two_slot_requested="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_requested)"
two_slot_active_nvtx="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_active)"
two_slot_ranges="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_nvtx_trace_ranges)"
two_slot_overlap_active="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_flush_two_slot_overlap_active)"
two_slot_gpu_cpu_supported="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported)"
two_slot_gpu_cpu_overlap="$(metric_value "$WORK/two_slot_nvtx/stderr.log" benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds)"

if [[ "$requested" != "1" || "$compiled" != "1" || "$active" != "1" ]]; then
  echo "NVTX telemetry did not activate: requested=$requested compiled=$compiled active=$active" >&2
  exit 1
fi
if (( ranges < 1 )); then
  echo "expected at least one NVTX range, got $ranges" >&2
  exit 1
fi
if [[ "$decision" != "nvtx_ranges_emitted_for_nsight" ]]; then
  echo "unexpected NVTX decision: $decision" >&2
  exit 1
fi
if [[ "$two_slot_requested" != "1" || "$two_slot_active_nvtx" != "1" || "$two_slot_overlap_active" != "1" ]]; then
  echo "two-slot NVTX telemetry did not activate: nvtx_requested=$two_slot_requested nvtx_active=$two_slot_active_nvtx two_slot_active=$two_slot_overlap_active" >&2
  exit 1
fi
if (( two_slot_ranges <= ranges )); then
  echo "expected two-slot NVTX run to emit more ranges: normal=$ranges two_slot=$two_slot_ranges" >&2
  exit 1
fi
if [[ "$two_slot_gpu_cpu_supported" != "0" || "$two_slot_gpu_cpu_overlap" != "unavailable" ]]; then
  echo "unexpected two-slot GPU/CPU overlap marker: supported=$two_slot_gpu_cpu_supported overlap=$two_slot_gpu_cpu_overlap" >&2
  exit 1
fi

{
  printf 'nvtx_requested=%s\n' "$requested"
  printf 'nvtx_compiled=%s\n' "$compiled"
  printf 'nvtx_active=%s\n' "$active"
  printf 'nvtx_ranges=%s\n' "$ranges"
  printf 'two_slot_nvtx_ranges=%s\n' "$two_slot_ranges"
  printf 'two_slot_overlap_active=%s\n' "$two_slot_overlap_active"
  printf 'nvtx_decision=%s\n' "$decision"
  printf 'lite_sha256=%s\n' "$(sha256sum "$two_slot_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_nvtx_trace_smoke: ok"
