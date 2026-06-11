#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_scoreinfo_prune_top5_matrix"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-64}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
MATRIX_PRESET="${MATRIX_PRESET:-chr22}"

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
mkdir -p "$WORK"

declare -a LABELS=()
declare -a TARGETS=()
declare -a RNAS=()
declare -a RULES=()

add_case() {
  LABELS+=("$1")
  TARGETS+=("$2")
  RNAS+=("$3")
  RULES+=("$4")
}

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

add_chr22_cases() {
  add_case "chr22_10m_12m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" "$RNA" "$RULE"
  add_case "chr22_10m_20m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_20m.fa" "$RNA" "$RULE"
  add_case "chr22_20m_30m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_20m_30m.fa" "$RNA" "$RULE"
}

add_chr22_2mb_case() {
  add_case "chr22_10m_12m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" "$RNA" "$RULE"
}

add_meg3_case() {
  add_case \
    "meg3_full" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa" \
    "$RULE"
}

add_malat1_case() {
  add_case \
    "malat1_full" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
    "$RULE"
}

add_malat1_first8_case() {
  local sampled="$WORK/inputs/malat1_first8.fa"
  mkdir -p "$(dirname "$sampled")"
  first_records_fasta \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
    "$sampled" \
    8
  add_case \
    "malat1_first8" \
    "$sampled" \
    "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
    "$RULE"
}

add_neat1_case() {
  add_case \
    "neat1_full" \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa" \
    "$RULE"
}

add_neat1_first64_case() {
  local sampled="$WORK/inputs/neat1_first64.fa"
  mkdir -p "$(dirname "$sampled")"
  first_records_fasta \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
    "$sampled" \
    64
  add_case \
    "neat1_first64" \
    "$sampled" \
    "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa" \
    "$RULE"
}

case "$MATRIX_PRESET" in
  chr22)
    add_chr22_cases
    ;;
  chr22_2mb)
    add_chr22_2mb_case
    ;;
  examples)
    add_meg3_case
    add_malat1_first8_case
    add_neat1_first64_case
    ;;
  all)
    add_chr22_cases
    add_meg3_case
    add_malat1_first8_case
    add_neat1_first64_case
    ;;
  meg3)
    add_meg3_case
    ;;
  malat1)
    add_malat1_case
    ;;
  malat1_first8)
    add_malat1_first8_case
    ;;
  neat1)
    add_neat1_case
    ;;
  neat1_first64)
    add_neat1_first64_case
    ;;
  *)
    echo "unknown MATRIX_PRESET: $MATRIX_PRESET" >&2
    exit 1
    ;;
esac

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	target	rna	rule	baseline_rows	candidate_rows	missing_rows	extra_rows	top5_score_equal	top5_stability_equal	top5_nt_score_equal	top5_artifact_equal	top5_artifact_rows	scoreinfo_pruned_groups	query_preflight_supported	query_preflight_query_len	query_preflight_max_query_len	length_guard_fallbacks	length_guard_last_query_len	length_guard_max_query_len	traceback_requests	gasal2_total_seconds	baseline_wall_seconds	candidate_wall_seconds	speedup_vs_baseline" \
  >"$summary"

for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  target="${TARGETS[$i]}"
  rna="${RNAS[$i]}"
  rule="${RULES[$i]}"
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
  candidate_dir="$run_dir/prune"
  mkdir -p "$cpu_dir" "$candidate_dir"

  cpu_start_seconds="$(date +%s.%N)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$target" -f2 "$rna" -r "$rule" -O "$cpu_dir" \
    >"$cpu_dir/stdout.log" 2>"$cpu_dir/stderr.log"
  cpu_end_seconds="$(date +%s.%N)"
  baseline_wall_seconds="$(awk -v start="$cpu_start_seconds" -v end="$cpu_end_seconds" 'BEGIN {printf "%.6f", end - start}')"
  printf '%s\n' "$baseline_wall_seconds" >"$cpu_dir/wall_seconds.txt"

  start_seconds="$(date +%s.%N)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    "$BIN" -f1 "$target" -f2 "$rna" -r "$rule" -O "$candidate_dir" \
    >"$candidate_dir/stdout.log" 2>"$candidate_dir/stderr.log"
  end_seconds="$(date +%s.%N)"
  candidate_wall_seconds="$(awk -v start="$start_seconds" -v end="$end_seconds" 'BEGIN {printf "%.6f", end - start}')"
  printf '%s\n' "$candidate_wall_seconds" >"$candidate_dir/wall_seconds.txt"

  cpu_out="$(find "$cpu_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  candidate_out="$(find "$candidate_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$cpu_out" || -z "$candidate_out" ]]; then
    echo "expected lite outputs missing for $label" >&2
    exit 1
  fi

  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$cpu_out" \
    --candidate "$candidate_out" \
    --k 5 \
    >"$run_dir/top5_compare.txt"

  grep -q '^top5_score_equal=true$' "$run_dir/top5_compare.txt"
  grep -q '^top5_stability_equal=true$' "$run_dir/top5_compare.txt"
  grep -q '^top5_nt_score_equal=true$' "$run_dir/top5_compare.txt"
  cpu_top5_out="$run_dir/cpu.top5.lite"
  candidate_top5_out="$run_dir/candidate.top5.lite"
  python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
    --input "$cpu_out" \
    --output "$cpu_top5_out" \
    --k 5 \
    >"$run_dir/cpu_top5_extract.txt"
  python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
    --input "$candidate_out" \
    --output "$candidate_top5_out" \
    --k 5 \
    >"$run_dir/candidate_top5_extract.txt"
  cmp -s "$cpu_top5_out" "$candidate_top5_out"
  top5_artifact_equal=true
  top5_artifact_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$cpu_top5_out")"
  length_guard_fallbacks="$(awk -F= '/^benchmark\.fasim_gasal2_length_guard_fallbacks=/{print $2}' "$candidate_dir/stderr.log")"
  query_preflight_supported="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=/{print $2}' "$candidate_dir/stderr.log")"
  if [[ "${query_preflight_supported:-0}" == "1" ]]; then
    [[ "${length_guard_fallbacks:-0}" == "0" ]]
    grep -q "^benchmark\\.fasim_top5_gasal2_phase_scoreinfo_prune_enabled=1$" "$candidate_dir/stderr.log"
    grep -q "^benchmark\\.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=$PRUNE_MAX_PER_TASK$" "$candidate_dir/stderr.log"
    grep -q "^benchmark\\.fasim_gasal2_effective_streams=$GASAL2_STREAMS$" "$candidate_dir/stderr.log"
    grep -q "^benchmark\\.fasim_gasal2_effective_batch_size=$GASAL2_BATCH$" "$candidate_dir/stderr.log"
  else
    grep -q "^benchmark\\.fasim_gasal2_requests=0$" "$candidate_dir/stderr.log"
    grep -q "^benchmark\\.fasim_gasal2_fallbacks=0$" "$candidate_dir/stderr.log"
    grep -q "^benchmark\\.fasim_gasal2_length_guard_fallbacks=0$" "$candidate_dir/stderr.log"
  fi

  baseline_rows="$(awk -F= '/^baseline_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  candidate_rows="$(awk -F= '/^candidate_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  missing_rows="$(awk -F= '/^missing_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  extra_rows="$(awk -F= '/^extra_rows=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_score_equal="$(awk -F= '/^top5_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_stability_equal="$(awk -F= '/^top5_stability_equal=/{print $2}' "$run_dir/top5_compare.txt")"
  top5_nt_score_equal="$(awk -F= '/^top5_nt_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"
  scoreinfo_pruned_groups="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_groups=/{print $2}' "$candidate_dir/stderr.log")"
  query_preflight_query_len="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len=/{print $2}' "$candidate_dir/stderr.log")"
  query_preflight_max_query_len="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len=/{print $2}' "$candidate_dir/stderr.log")"
  length_guard_last_query_len="$(awk -F= '/^benchmark\.fasim_gasal2_length_guard_last_query_len=/{print $2}' "$candidate_dir/stderr.log")"
  length_guard_max_query_len="$(awk -F= '/^benchmark\.fasim_gasal2_length_guard_max_query_len=/{print $2}' "$candidate_dir/stderr.log")"
  traceback_requests="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_requests=/{print $2}' "$candidate_dir/stderr.log")"
  gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$candidate_dir/stderr.log")"
  speedup_vs_baseline="$(awk -v base="$baseline_wall_seconds" -v cand="$candidate_wall_seconds" 'BEGIN {if (cand > 0) printf "%.6f", base / cand; else print "nan"}')"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$label" \
    "$target" \
    "$rna" \
    "$rule" \
    "$baseline_rows" \
    "$candidate_rows" \
    "$missing_rows" \
    "$extra_rows" \
    "$top5_score_equal" \
    "$top5_stability_equal" \
    "$top5_nt_score_equal" \
    "$top5_artifact_equal" \
    "$top5_artifact_rows" \
    "$scoreinfo_pruned_groups" \
    "${query_preflight_supported:-0}" \
    "${query_preflight_query_len:-0}" \
    "${query_preflight_max_query_len:-0}" \
    "${length_guard_fallbacks:-0}" \
    "${length_guard_last_query_len:-0}" \
    "${length_guard_max_query_len:-0}" \
    "$traceback_requests" \
    "$gasal2_total_seconds" \
    "$baseline_wall_seconds" \
    "$candidate_wall_seconds" \
    "$speedup_vs_baseline" \
    >>"$summary"
done

cat "$summary"
