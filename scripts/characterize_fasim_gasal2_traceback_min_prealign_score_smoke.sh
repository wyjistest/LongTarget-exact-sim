#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
THRESHOLDS="${THRESHOLDS:-60 70 80 90 100}"

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
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

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline"

run_case() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" ]]; then
  echo "missing baseline lite output" >&2
  exit 1
fi
baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"

summary="$WORK/summary.tsv"
printf 'threshold\ttraceback_requests\ttraceback_reduction\tmin_score_skipped\ttop5_score_equal\ttop5_stability_equal\ttop5_nt_score_equal\tmissing_rows\textra_rows\n' >"$summary"

for threshold in $THRESHOLDS; do
  out_dir="$WORK/min_${threshold}"
  run_case "$out_dir" \
    FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE="$threshold"
  candidate_out="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$candidate_out" ]]; then
    echo "missing candidate lite output for threshold=$threshold" >&2
    exit 1
  fi
  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$baseline_out" \
    --candidate "$candidate_out" \
    --k 5 \
    >"$out_dir/top5_compare.txt" || true
  traceback="$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
  min_skipped="$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_limited_traceback_min_prealign_score_skipped 0)"
  score_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_score_equal false)"
  stability_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_stability_equal false)"
  nt_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_nt_score_equal false)"
  missing_rows="$(metric_or_default "$out_dir/top5_compare.txt" missing_rows 0)"
  extra_rows="$(metric_or_default "$out_dir/top5_compare.txt" extra_rows 0)"
  reduction=$((baseline_traceback - traceback))
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$threshold" "$traceback" "$reduction" "$min_skipped" \
    "$score_equal" "$stability_equal" "$nt_equal" "$missing_rows" "$extra_rows" \
    >>"$summary"
done

cat "$summary"
echo "ok"
