#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_cpu_vs_gasal2_full_plain_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
GASAL2_STREAMS="${GASAL2_STREAMS:-1}"

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

ratio_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
num = float(sys.argv[1])
den = float(sys.argv[2])
print("nan" if den == 0.0 else f"{num / den:.6f}")
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

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/compare_fasim_lite_topk.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/cpu" "$WORK/gasal2"

run_case() {
  local label="$1"
  shift
  local out_dir="$WORK/$label"
  local start end lite
  start="$(now_seconds)"
  env "$@" "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"

  lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$lite" || ! -s "$lite" ]]; then
    echo "missing $label lite output" >&2
    exit 1
  fi

  {
    printf 'label=%s\n' "$label"
    printf 'wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")"
    printf 'lite=%s\n' "$lite"
    printf 'lines=%s\n' "$(wc -l <"$lite")"
    printf 'bytes=%s\n' "$(stat -c%s "$lite")"
    printf 'sha256=%s\n' "$(sha256sum "$lite" | awk '{print $1}')"
    printf 'gasal2_active=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_top5_gasal2_gpu_scoreinfo_active 0)"
    printf 'gasal2_requests=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_requests 0)"
    printf 'gasal2_traceback_requests=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
    printf 'gasal2_fallbacks=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_fallbacks 0)"
    printf 'gasal2_length_guard_fallbacks=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_length_guard_fallbacks 0)"
    printf 'gasal2_total_seconds=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_total_seconds 0)"
    printf 'gasal2_extend_wall_seconds=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds 0)"
    printf 'gasal2_convert_wall_seconds=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0)"
    printf 'exact_column_wall_seconds=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds 0)"
    printf 'output_write_seconds=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_output_write_seconds 0)"
  } >"$out_dir/case_metrics.txt"
}

run_case cpu \
  -u FASIM_TOP5_GASAL2_GPU_SCOREINFO \
  -u FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE \
  -u FASIM_GASAL2_EQUIVALENCE_FIRST_CONVERT \
  -u FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0

run_case gasal2 \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
  FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
  FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH"

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$(metric_or_default "$WORK/cpu/case_metrics.txt" lite "")" \
  --candidate "$(metric_or_default "$WORK/gasal2/case_metrics.txt" lite "")" \
  --k 5 \
  >"$WORK/top5_compare.txt"

LC_ALL=C sort "$(metric_or_default "$WORK/cpu/case_metrics.txt" lite "")" >"$WORK/cpu.sorted"
LC_ALL=C sort "$(metric_or_default "$WORK/gasal2/case_metrics.txt" lite "")" >"$WORK/gasal2.sorted"
comm -23 "$WORK/cpu.sorted" "$WORK/gasal2.sorted" >"$WORK/cpu_only.txt"
comm -13 "$WORK/cpu.sorted" "$WORK/gasal2.sorted" >"$WORK/gasal2_only.txt"

cpu_wall="$(metric_or_default "$WORK/cpu/case_metrics.txt" wall_seconds 0)"
gasal2_wall="$(metric_or_default "$WORK/gasal2/case_metrics.txt" wall_seconds 0)"

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  printf 'cpu_wall_seconds=%s\n' "$cpu_wall"
  printf 'gasal2_wall_seconds=%s\n' "$gasal2_wall"
  printf 'run_wall_speedup=%s\n' "$(ratio_seconds "$cpu_wall" "$gasal2_wall")"
  printf 'cpu_lines=%s\n' "$(metric_or_default "$WORK/cpu/case_metrics.txt" lines 0)"
  printf 'gasal2_lines=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" lines 0)"
  baseline_unique_rows="$(metric_or_default "$WORK/top5_compare.txt" baseline_unique_rows 0)"
  missing_rows="$(metric_or_default "$WORK/top5_compare.txt" missing_rows 0)"
  printf 'common_rows=%s\n' "$((baseline_unique_rows - missing_rows))"
  printf 'cpu_only_rows=%s\n' "$missing_rows"
  printf 'gasal2_only_rows=%s\n' "$(metric_or_default "$WORK/top5_compare.txt" extra_rows 0)"
  printf 'top5_score_equal=%s\n' "$(metric_or_default "$WORK/top5_compare.txt" top5_score_equal false)"
  printf 'top5_stability_equal=%s\n' "$(metric_or_default "$WORK/top5_compare.txt" top5_stability_equal false)"
  printf 'top5_nt_score_equal=%s\n' "$(metric_or_default "$WORK/top5_compare.txt" top5_nt_score_equal false)"
  printf 'gasal2_active=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_active 0)"
  printf 'gasal2_requests=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_requests 0)"
  printf 'gasal2_traceback_requests=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_traceback_requests 0)"
  printf 'gasal2_fallbacks=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_fallbacks 0)"
  printf 'gasal2_length_guard_fallbacks=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_length_guard_fallbacks 0)"
  printf 'gasal2_total_seconds=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_total_seconds 0)"
  printf 'gasal2_extend_wall_seconds=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_extend_wall_seconds 0)"
  printf 'gasal2_convert_wall_seconds=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" gasal2_convert_wall_seconds 0)"
  printf 'exact_column_wall_seconds=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" exact_column_wall_seconds 0)"
  printf 'output_write_seconds=%s\n' "$(metric_or_default "$WORK/gasal2/case_metrics.txt" output_write_seconds 0)"
  printf 'decision=%s\n' "top5_equivalent_fast_path_not_full_row_equivalent"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
