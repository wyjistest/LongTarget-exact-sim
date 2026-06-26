#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
DNA="${DNA:?DNA must point to a target FASTA}"
RNA="${RNA:?RNA must point to an RNA/query FASTA}"
RULE="${RULE:-0}"
WORK="${WORK:-"$ROOT/.tmp/calibrate_fasim_gasal2_traceback_threshold"}"
THRESHOLDS="${THRESHOLDS:-80 90 100 110 115 116 117 118 120}"
MAX_RECORDS="${MAX_RECORDS:-1}"
MAX_BASES="${MAX_BASES:-0}"
WINDOWS="${WINDOWS:-8}"
MIN_TRACEBACK_REQUESTS="${MIN_TRACEBACK_REQUESTS:-1}"
ANCHOR_TSV="${ANCHOR_TSV:-}"
ANCHOR_WINDOW_BASES="${ANCHOR_WINDOW_BASES:-250000}"
ANCHOR_MAX_WINDOWS="${ANCHOR_MAX_WINDOWS:-0}"
ESTIMATOR_REQUIRE_FAILING_BOUNDARY="${ESTIMATOR_REQUIRE_FAILING_BOUNDARY:-1}"

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
}

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.perf_counter():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

CAL_DNA="$WORK/calibration_target.fa"
sample_args=(
  python3 "$ROOT/scripts/sample_fasta_windows.py"
  --input "$DNA"
  --output "$CAL_DNA"
  --max-records "$MAX_RECORDS"
  --max-bases "$MAX_BASES"
  --windows "$WINDOWS"
  --manifest "$WORK/calibration_target_windows.tsv"
  --metrics "$WORK/calibration_target_sample_metrics.txt"
  --anchor-window-bases "$ANCHOR_WINDOW_BASES"
  --anchor-max-windows "$ANCHOR_MAX_WINDOWS"
)
if [[ -n "$ANCHOR_TSV" ]]; then
  sample_args+=(--anchor-tsv "$ANCHOR_TSV")
fi
"${sample_args[@]}"

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
    "$BIN" -f1 "$CAL_DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

baseline_dir="$WORK/threshold_0"
baseline_start="$(now_seconds)"
run_case "$baseline_dir"
baseline_end="$(now_seconds)"
baseline_wall="$(elapsed_seconds "$baseline_start" "$baseline_end")"
baseline_lite="$(find "$baseline_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || ! -s "$baseline_lite" ]]; then
  echo "missing threshold-0 baseline lite output" >&2
  exit 1
fi
baseline_traceback="$(metric_or_default "$baseline_dir/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"

summary="$WORK/summary.tsv"
printf 'threshold\twall_seconds\tvs_baseline_gasal2_wall\ttraceback_requests\ttraceback_reduction\ttraceback_reduction_fraction\tmin_score_skipped\ttop5_score_equal\ttop5_stability_equal\ttop5_nt_score_equal\tmissing_rows\textra_rows\n' >"$summary"

for threshold in $THRESHOLDS; do
  out_dir="$WORK/threshold_${threshold}"
  start="$(now_seconds)"
  run_case "$out_dir" \
    FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE="$threshold"
  end="$(now_seconds)"
  candidate_lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$candidate_lite" || ! -s "$candidate_lite" ]]; then
    echo "missing threshold=$threshold lite output" >&2
    exit 1
  fi
  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$baseline_lite" \
    --candidate "$candidate_lite" \
    --k 5 \
    >"$out_dir/top5_compare.txt" || true
  wall="$(elapsed_seconds "$start" "$end")"
  traceback="$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
  min_skipped="$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_limited_traceback_min_prealign_score_skipped 0)"
  score_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_score_equal false)"
  stability_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_stability_equal false)"
  nt_equal="$(metric_or_default "$out_dir/top5_compare.txt" top5_nt_score_equal false)"
  missing_rows="$(metric_or_default "$out_dir/top5_compare.txt" missing_rows 0)"
  extra_rows="$(metric_or_default "$out_dir/top5_compare.txt" extra_rows 0)"
  python3 - "$summary" "$threshold" "$wall" "$baseline_wall" "$baseline_traceback" "$traceback" "$min_skipped" "$score_equal" "$stability_equal" "$nt_equal" "$missing_rows" "$extra_rows" <<'PY'
import sys
from pathlib import Path

summary = Path(sys.argv[1])
threshold = sys.argv[2]
wall = float(sys.argv[3])
baseline_wall = float(sys.argv[4])
baseline_traceback = int(float(sys.argv[5]))
traceback = int(float(sys.argv[6]))
min_skipped = sys.argv[7]
score_equal = sys.argv[8]
stability_equal = sys.argv[9]
nt_equal = sys.argv[10]
missing_rows = sys.argv[11]
extra_rows = sys.argv[12]
reduction = max(baseline_traceback - traceback, 0)
wall_ratio = "nan" if baseline_wall == 0.0 else f"{wall / baseline_wall:.6f}"
reduction_fraction = "nan" if baseline_traceback == 0 else f"{reduction / baseline_traceback:.6f}"
with summary.open("a", encoding="utf-8") as handle:
    handle.write(
        "\t".join([
            threshold,
            f"{wall:.6f}",
            wall_ratio,
            str(traceback),
            str(reduction),
            reduction_fraction,
            min_skipped,
            score_equal,
            stability_equal,
            nt_equal,
            missing_rows,
            extra_rows,
        ])
        + "\n"
    )
PY
done

estimator_args=(
  python3 "$ROOT/scripts/estimate_fasim_gasal2_traceback_threshold.py"
  --summary "$summary"
  --query-label "$(basename "$RNA")"
  --query-fasta "$RNA"
  --output "$WORK/estimate.txt"
  --min-baseline-traceback-requests "$MIN_TRACEBACK_REQUESTS"
)
if [[ "$ESTIMATOR_REQUIRE_FAILING_BOUNDARY" == "1" ]]; then
  estimator_args+=(--require-failing-boundary)
fi
"${estimator_args[@]}"

cat "$WORK/estimate.txt"
