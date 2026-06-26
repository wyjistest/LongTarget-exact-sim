#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_pipeline_smoke"}"
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
mkdir -p "$WORK/baseline" "$WORK/trace"

run_case() {
  local label="$1"
  local trace_enabled="$2"
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
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE="$trace_enabled" \
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_EXPORT="$out_dir/flush_pipeline.tsv" \
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_JSON="$out_dir/flush_pipeline_trace.json" \
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_LIMIT=2 \
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_CHROME_LIMIT=1 \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0
run_case trace 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
trace_lite="$(find "$WORK/trace" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$trace_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$trace_lite"; then
  echo "telemetry changed lite output" >&2
  exit 1
fi

requested="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_requested)"
active="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_active)"
flushes="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_flushes)"
export_rows="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_export_rows)"
export_truncated="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_export_truncated)"
chrome_events="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_chrome_trace_events)"
chrome_truncated="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_chrome_trace_truncated)"
queue_supported="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_queue_supported)"
synchronous_flush_path="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_synchronous_flush_path)"
synchronous_wait_seconds="$(metric_value "$WORK/trace/stderr.log" benchmark.fasim_gasal2_flush_pipeline_total_gasal2_synchronous_wait_seconds)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "flush pipeline telemetry did not activate: requested=$requested active=$active" >&2
  exit 1
fi
if (( flushes < 1 )); then
  echo "expected at least one flush, got $flushes" >&2
  exit 1
fi
if (( export_rows < 1 || export_rows > 2 )); then
  echo "export rows outside cap: $export_rows" >&2
  exit 1
fi
if (( chrome_events > 10 )); then
  echo "chrome trace events outside cap: $chrome_events" >&2
  exit 1
fi
if [[ "$queue_supported" != "0" || "$synchronous_flush_path" != "1" ]]; then
  echo "unexpected queue/wait-state flags: queue_supported=$queue_supported synchronous_flush_path=$synchronous_flush_path" >&2
  exit 1
fi
if [[ ! -s "$WORK/trace/flush_pipeline.tsv" ]]; then
  echo "missing flush pipeline TSV" >&2
  exit 1
fi
if [[ ! -s "$WORK/trace/flush_pipeline_trace.json" ]]; then
  echo "missing Chrome trace JSON" >&2
  exit 1
fi

python3 "$ROOT/scripts/summarize_fasim_gasal2_flush_pipeline.py" \
  --flush-tsv "$WORK/trace/flush_pipeline.tsv" \
  --chrome-trace "$WORK/trace/flush_pipeline_trace.json" \
  --output-summary "$WORK/trace/flush_pipeline_summary.txt" \
  --output-tsv "$WORK/trace/flush_pipeline_summary.tsv"

grep -q '^decision=telemetry_incomplete$' "$WORK/trace/flush_pipeline_summary.txt"
grep -q '^simulation_assumption=' "$WORK/trace/flush_pipeline_summary.txt"
grep -q '^queue_supported=0$' "$WORK/trace/flush_pipeline_summary.txt"
grep -q '^synchronous_flush_path=1$' "$WORK/trace/flush_pipeline_summary.txt"

{
  printf 'flush_pipeline_requested=%s\n' "$requested"
  printf 'flush_pipeline_active=%s\n' "$active"
  printf 'flush_pipeline_flushes=%s\n' "$flushes"
  printf 'flush_pipeline_export_rows=%s\n' "$export_rows"
  printf 'flush_pipeline_export_truncated=%s\n' "$export_truncated"
  printf 'flush_pipeline_chrome_events=%s\n' "$chrome_events"
  printf 'flush_pipeline_chrome_truncated=%s\n' "$chrome_truncated"
  printf 'flush_pipeline_queue_supported=%s\n' "$queue_supported"
  printf 'flush_pipeline_synchronous_flush_path=%s\n' "$synchronous_flush_path"
  printf 'flush_pipeline_synchronous_wait_seconds=%s\n' "$synchronous_wait_seconds"
  printf 'lite_sha256=%s\n' "$(sha256sum "$trace_lite" | awk '{print $1}')"
  awk -F= '
    $1 == "total_flush_wall_seconds" ||
    $1 == "total_requests" ||
    $1 == "total_traceback_requests" ||
    $1 == "simulated_two_buffer_speedup" ||
    $1 == "decision" {
      print
    }
  ' "$WORK/trace/flush_pipeline_summary.txt"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_pipeline_smoke: ok"
