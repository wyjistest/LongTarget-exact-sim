#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
THRESHOLDS="${THRESHOLDS:-80 90 100}"
CPU_BASELINE_LITE="${CPU_BASELINE_LITE:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/cpu/chr22-H19-chr22-TFOsorted.lite"}"
BASELINE_GASAL2_STDERR="${BASELINE_GASAL2_STDERR:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/gasal2/stderr.log"}"
BASELINE_GASAL2_SUMMARY="${BASELINE_GASAL2_SUMMARY:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/summary.txt"}"
BASELINE_GASAL2_CASE_METRICS="${BASELINE_GASAL2_CASE_METRICS:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/gasal2/case_metrics.txt"}"

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
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$CPU_BASELINE_LITE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

baseline_traceback="$(metric_or_default "$BASELINE_GASAL2_STDERR" benchmark.fasim_gasal2_traceback_requests 0)"
baseline_wall="$(metric_or_default "$BASELINE_GASAL2_SUMMARY" gasal2_wall_seconds 0)"
if [[ "$baseline_wall" == "0" || "$baseline_wall" == "0.000000" ]]; then
  baseline_wall="$(metric_or_default "$BASELINE_GASAL2_CASE_METRICS" wall_seconds 0)"
fi

summary="$WORK/summary.tsv"
printf 'threshold\twall_seconds\tvs_baseline_gasal2_wall\ttraceback_requests\ttraceback_reduction\ttraceback_reduction_fraction\tmin_score_skipped\ttop5_score_equal\ttop5_stability_equal\ttop5_nt_score_equal\tmissing_rows\textra_rows\n' >"$summary"

for threshold in $THRESHOLDS; do
  out_dir="$WORK/min_${threshold}"
  mkdir -p "$out_dir"
  start="$(now_seconds)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE="$threshold" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"
  candidate_out="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$candidate_out" || ! -s "$candidate_out" ]]; then
    echo "missing candidate lite output for threshold=$threshold" >&2
    exit 1
  fi
  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$CPU_BASELINE_LITE" \
    --candidate "$candidate_out" \
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
        "\t".join(
            [
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
            ]
        )
        + "\n"
    )
PY
done

cat "$summary"
echo "ok"
