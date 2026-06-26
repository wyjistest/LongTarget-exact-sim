#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_convert_cpu_breakdown"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

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
mkdir -p "$WORK/run"

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
  "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/run" \
  >"$WORK/run/stdout.log" 2>"$WORK/run/stderr.log"

require_metric() {
  local key="$1"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$WORK/run/stderr.log" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    echo "missing metric: $key" >&2
    exit 1
  fi
  python3 - "$key" "$value" <<'PY'
import sys
key, value = sys.argv[1], sys.argv[2]
try:
    parsed = float(value)
except ValueError:
    print(f"metric is not numeric: {key}={value}", file=sys.stderr)
    raise SystemExit(1)
if parsed < 0:
    print(f"metric is negative: {key}={value}", file=sys.stderr)
    raise SystemExit(1)
PY
  printf '%s=%s\n' "$key" "$value"
}

require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_selected_scan_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_span_check_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds
require_metric benchmark.fasim_top5_gasal2_phase_gasal2_convert_raw_triplexes_per_second
require_metric benchmark.fasim_top5_gasal2_phase_output_write_seconds
require_metric benchmark.fasim_top5_gasal2_phase_output_close_seconds
require_metric benchmark.fasim_top5_gasal2_phase_query_release_seconds
