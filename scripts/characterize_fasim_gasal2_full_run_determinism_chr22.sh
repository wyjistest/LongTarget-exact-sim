#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_full_run_determinism_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
REPEATS="${REPEATS:-3}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
REUSE_RUNS="${REUSE_RUNS:-}"

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

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/compare_fasim_full_run_determinism.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

run_paths=()
if [[ -n "$REUSE_RUNS" ]]; then
  IFS=: read -r -a run_paths <<<"$REUSE_RUNS"
else
  for repeat in $(seq 1 "$REPEATS"); do
    out_dir="$WORK/run_${repeat}"
    mkdir -p "$out_dir"
    start="$(now_seconds)"
    env \
      FASIM_OUTPUT_MODE=lite \
      FASIM_VERBOSE=0 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
      FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
      FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
      "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
    end="$(now_seconds)"
    lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
    if [[ -z "$lite" || ! -s "$lite" ]]; then
      echo "missing lite output for repeat $repeat" >&2
      exit 1
    fi
    run_paths+=("$lite")
    {
      printf 'repeat=%s\n' "$repeat"
      printf 'wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")"
      printf 'lite=%s\n' "$lite"
      printf 'lines=%s\n' "$(wc -l <"$lite")"
      printf 'sha256=%s\n' "$(sha256sum "$lite" | awk '{print $1}')"
      printf 'gasal2_requests=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_requests 0)"
      printf 'gasal2_traceback_requests=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
      printf 'gasal2_fallbacks=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_fallbacks 0)"
      printf 'gasal2_length_guard_fallbacks=%s\n' "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_length_guard_fallbacks 0)"
    } >"$out_dir/case_metrics.txt"
  done
fi

compare_args=()
for path in "${run_paths[@]}"; do
  compare_args+=(--run "$path")
done

python3 "$ROOT/scripts/compare_fasim_full_run_determinism.py" \
  "${compare_args[@]}" \
  --k 5 \
  --output-summary "$WORK/determinism_summary.txt" \
  --output-pairs "$WORK/determinism_pairs.tsv"

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'repeats=%s\n' "${#run_paths[@]}"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  cat "$WORK/determinism_summary.txt"
  printf 'decision=%s\n' "determinism_oracle_recorded"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
