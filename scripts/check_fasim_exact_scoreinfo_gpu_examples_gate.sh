#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_exact_scoreinfo_gpu_examples_gate"}"
RULE="${RULE:-0}"
K="${K:-5}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-16}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"

if [[ "$K" != "5" ]]; then
  echo "examples gate requires K=5" >&2
  exit 1
fi

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

first_records_fasta() {
  local input="$1"
  local output="$2"
  local count="$3"
  awk -v limit="$count" '
    /^>/ {
      ++records
    }
    records <= limit {
      print
    }
  ' "$input" >"$output"
}

first_records_fasta \
  "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
  "$WORK/inputs/malat1_first8.fa" \
  8
first_records_fasta \
  "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
  "$WORK/inputs/neat1_first64.fa" \
  64

declare -a LABELS=(
  "meg3_full"
  "malat1_first8"
  "neat1_first64"
)
declare -a TARGETS=(
  "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa"
  "$WORK/inputs/malat1_first8.fa"
  "$WORK/inputs/neat1_first64.fa"
)
declare -a RNAS=(
  "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa"
  "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"
  "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"
)

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	target	rna	rule	baseline_rows	candidate_rows	missing_rows	extra_rows	top5_score_equal	top5_stability_equal	top5_nt_score_equal	query_preflight_supported	query_preflight_query_len	query_preflight_max_query_len	scoreinfo_gasal2_active	gasal2_requests	gasal2_traceback_requests	gasal2_fallbacks	length_guard_fallbacks	exact_scoreinfo_gpu_enabled	exact_scoreinfo_gpu_tasks	exact_scoreinfo_gpu_overflow_batches	exact_scoreinfo_gpu_fallback_batches	exact_scoreinfo_gpu_wall_seconds	exact_scoreinfo_gpu_kernel_seconds	exact_scoreinfo_gpu_d2h_seconds	baseline_wall_seconds	candidate_wall_seconds	speedup_vs_baseline" \
  >"$summary"

for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  target="${TARGETS[$i]}"
  rna="${RNAS[$i]}"

  if [[ ! -s "$target" ]]; then
    echo "missing target: $target" >&2
    exit 1
  fi
  if [[ ! -s "$rna" ]]; then
    echo "missing RNA: $rna" >&2
    exit 1
  fi

  run_dir="$WORK/$label"
  cpu_dir="$run_dir/cpu"
  candidate_dir="$run_dir/exact_scoreinfo_gpu"
  mkdir -p "$cpu_dir" "$candidate_dir"

  cpu_start_seconds="$(date +%s.%N)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$target" -f2 "$rna" -r "$RULE" -O "$cpu_dir" \
    >"$cpu_dir/stdout.log" 2>"$cpu_dir/stderr.log"
  cpu_end_seconds="$(date +%s.%N)"
  baseline_wall_seconds="$(awk -v start="$cpu_start_seconds" -v end="$cpu_end_seconds" 'BEGIN {printf "%.6f", end - start}')"

  candidate_start_seconds="$(date +%s.%N)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_EXACT_COLUMN_SCOREINFO_GPU=1 \
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    "$BIN" -f1 "$target" -f2 "$rna" -r "$RULE" -O "$candidate_dir" \
    >"$candidate_dir/stdout.log" 2>"$candidate_dir/stderr.log"
  candidate_end_seconds="$(date +%s.%N)"
  candidate_wall_seconds="$(awk -v start="$candidate_start_seconds" -v end="$candidate_end_seconds" 'BEGIN {printf "%.6f", end - start}')"

  cpu_out="$(find "$cpu_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  candidate_out="$(find "$candidate_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$cpu_out" || -z "$candidate_out" ]]; then
    echo "expected lite outputs missing for $label" >&2
    exit 1
  fi

  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$cpu_out" \
    --candidate "$candidate_out" \
    --k "$K" \
    >"$run_dir/top5_compare.txt"

  grep -q '^top5_score_equal=true$' "$run_dir/top5_compare.txt"
  grep -q '^top5_stability_equal=true$' "$run_dir/top5_compare.txt"
  grep -q '^top5_nt_score_equal=true$' "$run_dir/top5_compare.txt"

  baseline_rows="$(awk -F= '/^baseline_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  candidate_rows="$(awk -F= '/^candidate_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  missing_rows="$(awk -F= '/^missing_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  extra_rows="$(awk -F= '/^extra_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_score_equal="$(awk -F= '/^top5_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_stability_equal="$(awk -F= '/^top5_stability_equal=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_nt_score_equal="$(awk -F= '/^top5_nt_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"

  metric() {
    local key="$1"
    local default_value="${2:-0}"
    local value
    value="$(awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log")"
    printf '%s' "${value:-$default_value}"
  }

  query_preflight_supported="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported 0)"
  query_preflight_query_len="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len 0)"
  query_preflight_max_query_len="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len 0)"
  gasal2_requests="$(metric benchmark.fasim_gasal2_requests 0)"
  gasal2_traceback_requests="$(metric benchmark.fasim_gasal2_traceback_requests 0)"
  gasal2_fallbacks="$(metric benchmark.fasim_gasal2_fallbacks 0)"
  length_guard_fallbacks="$(metric benchmark.fasim_gasal2_length_guard_fallbacks 0)"
  exact_scoreinfo_gpu_enabled="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled 0)"
  exact_scoreinfo_gpu_tasks="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks 0)"
  exact_scoreinfo_gpu_overflow_batches="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches 0)"
  exact_scoreinfo_gpu_fallback_batches="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches 0)"
  exact_scoreinfo_gpu_wall_seconds="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds 0)"
  exact_scoreinfo_gpu_kernel_seconds="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds 0)"
  exact_scoreinfo_gpu_d2h_seconds="$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds 0)"
  scoreinfo_gasal2_active=0
  if [[ "$query_preflight_supported" == "1" &&
        "$gasal2_requests" != "0" &&
        "$gasal2_traceback_requests" != "0" &&
        "$gasal2_fallbacks" == "0" &&
        "$length_guard_fallbacks" == "0" &&
        "$exact_scoreinfo_gpu_tasks" != "0" &&
        "$exact_scoreinfo_gpu_overflow_batches" == "0" &&
        "$exact_scoreinfo_gpu_fallback_batches" == "0" ]]; then
    scoreinfo_gasal2_active=1
  fi

  if [[ "$label" == "meg3_full" ]]; then
    [[ "$query_preflight_supported" == "1" ]]
    [[ "$scoreinfo_gasal2_active" == "1" ]]
    [[ "$gasal2_requests" != "0" ]]
    [[ "$gasal2_traceback_requests" != "0" ]]
    [[ "$gasal2_fallbacks" == "0" ]]
    [[ "$length_guard_fallbacks" == "0" ]]
    [[ "$exact_scoreinfo_gpu_enabled" == "1" ]]
    [[ "$exact_scoreinfo_gpu_tasks" != "0" ]]
    [[ "$exact_scoreinfo_gpu_overflow_batches" == "0" ]]
    [[ "$exact_scoreinfo_gpu_fallback_batches" == "0" ]]
  else
    [[ "$query_preflight_supported" == "0" ]]
    [[ "$scoreinfo_gasal2_active" == "0" ]]
    [[ "$query_preflight_query_len" -gt "$query_preflight_max_query_len" ]]
    [[ "$gasal2_requests" == "0" ]]
    [[ "$gasal2_traceback_requests" == "0" ]]
    [[ "$gasal2_fallbacks" == "0" ]]
    [[ "$length_guard_fallbacks" == "0" ]]
    [[ "$exact_scoreinfo_gpu_tasks" == "0" ]]
  fi

  speedup_vs_baseline="$(awk -v base="$baseline_wall_seconds" -v cand="$candidate_wall_seconds" 'BEGIN {if (cand > 0) printf "%.6f", base / cand; else print "nan"}')"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$label" \
    "$target" \
    "$rna" \
    "$RULE" \
    "$baseline_rows" \
    "$candidate_rows" \
    "$missing_rows" \
    "$extra_rows" \
    "$top5_score_equal" \
    "$top5_stability_equal" \
    "$top5_nt_score_equal" \
    "$query_preflight_supported" \
    "$query_preflight_query_len" \
    "$query_preflight_max_query_len" \
    "$scoreinfo_gasal2_active" \
    "$gasal2_requests" \
    "$gasal2_traceback_requests" \
    "$gasal2_fallbacks" \
    "$length_guard_fallbacks" \
    "$exact_scoreinfo_gpu_enabled" \
    "$exact_scoreinfo_gpu_tasks" \
    "$exact_scoreinfo_gpu_overflow_batches" \
    "$exact_scoreinfo_gpu_fallback_batches" \
    "$exact_scoreinfo_gpu_wall_seconds" \
    "$exact_scoreinfo_gpu_kernel_seconds" \
    "$exact_scoreinfo_gpu_d2h_seconds" \
    "$baseline_wall_seconds" \
    "$candidate_wall_seconds" \
    "$speedup_vs_baseline" \
    >>"$summary"
done

cat "$summary"
