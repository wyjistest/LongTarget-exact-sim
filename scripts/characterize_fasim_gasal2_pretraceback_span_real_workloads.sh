#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_pretraceback_span_real_workloads"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
GASAL2_DIR="${GASAL2_DIR:-"$ROOT/.tmp/GASAL2"}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-"$ROOT/.tmp"}"
RESULT_TSV="${RESULT_TSV:-"$WORK/pretraceback_span_real_workloads.tsv"}"
SUMMARIZER="$ROOT/scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py"
RUN_WORKLOADS="${RUN_WORKLOADS:-0}"
CHR22_TARGET="${CHR22_TARGET:-"$ROOT/.tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa"}"
H19_RNA="${H19_RNA:-"$ROOT/H19.fa"}"
MALAT1_DNA="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"
MALAT1_RNA="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
NEAT1_DNA="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
NEAT1_RNA="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
NEAT1_RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-64}"
EXPORT_LIMIT="${EXPORT_LIMIT:-100}"

mkdir -p "$WORK"

first_records() {
  local input="$1"
  local limit="$2"
  local output="$3"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$input" >"$output"
}

find_lite_output() {
  local out_dir="$1"
  find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1
}

write_count_summary() {
  local baseline="$1"
  local candidate="$2"
  local out="$3"
  if [[ -s "$baseline" && -s "$candidate" ]]; then
    python3 "$ROOT/scripts/compare_fasim_lite_full_equivalence.py" \
      --baseline "$baseline" \
      --candidate "$candidate" \
      >"$out"
  else
    {
      echo "baseline_rows=unknown"
      echo "candidate_rows=unknown"
      echo "missing_rows=unknown"
      echo "extra_rows=unknown"
    } >"$out"
  fi
}

write_top5_summary() {
  local baseline="$1"
  local candidate="$2"
  local out="$3"
  if [[ -s "$baseline" && -s "$candidate" ]]; then
    if ! python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
      --baseline "$baseline" \
      --candidate "$candidate" \
      --k 5 \
      >"$out"; then
      true
    fi
    {
      grep -E '^top5_score_equal=' "$out" || echo "top5_score_equal=unknown"
      grep -E '^top5_stability_equal=' "$out" || echo "top5_stability_equal=unknown"
      grep -E '^top5_nt_score_equal=' "$out" || echo "top5_nt_score_equal=unknown"
    } >"$out.tmp"
    mv "$out.tmp" "$out"
  else
    {
      echo "top5_score_equal=unknown"
      echo "top5_stability_equal=unknown"
      echo "top5_nt_score_equal=unknown"
    } >"$out"
  fi
}

build_bin_if_needed() {
  if [[ -x "$BIN" ]]; then
    return
  fi
  make -C "$ROOT" build-fasim-gasal2 \
    FASIM_GASAL2_TARGET="$BIN" \
    GASAL2_DIR="$GASAL2_DIR"
}

run_direct_lite_pair() {
  local workload="$1"
  local target="$2"
  local query="$3"
  local rule="$4"
  local case_dir="$WORK/$workload"
  local baseline_dir="$case_dir/baseline"
  local candidate_dir="$case_dir/candidate"

  build_bin_if_needed
  for path in "$BIN" "$target" "$query"; do
    if [[ ! -e "$path" ]]; then
      echo "missing dependency for $workload: $path" >&2
      return 1
    fi
  done

  rm -rf "$case_dir"
  mkdir -p "$baseline_dir" "$candidate_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1 \
    "$BIN" -f1 "$target" -f2 "$query" -r "$rule" -O "$baseline_dir" \
    >"$baseline_dir/stdout.log" 2>"$baseline_dir/stderr.log"

  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1 \
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1 \
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT="$case_dir/eligibility.tsv" \
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT="$EXPORT_LIMIT" \
    "$BIN" -f1 "$target" -f2 "$query" -r "$rule" -O "$candidate_dir" \
    >"$candidate_dir/stdout.log" 2>"$candidate_dir/stderr.log"

  local baseline_lite candidate_lite
  baseline_lite="$(find_lite_output "$baseline_dir")"
  candidate_lite="$(find_lite_output "$candidate_dir")"
  write_top5_summary "$baseline_lite" "$candidate_lite" "$candidate_dir/top5.summary"
  write_count_summary "$baseline_lite" "$candidate_lite" "$candidate_dir/full_lite.summary"
  cp "$candidate_dir/full_lite.summary" "$candidate_dir/tfosorted.summary"
  printf '%s\n' "$candidate_dir/stderr.log"
}

runner_merged_output() {
  local report="$1"
  python3 - "$report" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["merged_output"])
PY
}

write_runner_summaries() {
  local baseline_report="$1"
  local candidate_report="$2"
  local out_dir="$3"
  python3 "$ROOT/scripts/compare_fasim_lite_full_equivalence.py" \
    --baseline-report "$baseline_report" \
    --candidate-report "$candidate_report" \
    >"$out_dir/full_lite.summary"
  cp "$out_dir/full_lite.summary" "$out_dir/tfosorted.summary"
  local baseline_output candidate_output
  baseline_output="$(runner_merged_output "$baseline_report")"
  candidate_output="$(runner_merged_output "$candidate_report")"
  if ! python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$baseline_output" \
    --candidate "$candidate_output" \
    --k 5 \
    >"$out_dir/top5.summary"; then
    true
  fi
}

run_malat1_group32_pair() {
  local workload="$1"
  local target="$2"
  local query="$3"
  local case_dir="$WORK/$workload"
  local baseline_report="$case_dir/baseline.report.json"
  local candidate_report="$case_dir/candidate.report.json"

  build_bin_if_needed
  for path in "$BIN" "$target" "$query"; do
    if [[ ! -e "$path" ]]; then
      echo "missing dependency for $workload: $path" >&2
      return 1
    fi
  done
  rm -rf "$case_dir"
  mkdir -p "$case_dir/candidate"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$query" \
    --rule 0 \
    --output-mode lite \
    --workers 1 \
    --work-dir "$case_dir/baseline" \
    --manifest "$case_dir/baseline/run_manifest.json" \
    --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32 \
    >"$baseline_report"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$query" \
    --rule 0 \
    --output-mode lite \
    --workers 1 \
    --work-dir "$case_dir/candidate" \
    --manifest "$case_dir/candidate/run_manifest.json" \
    --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32 \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1 \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT="$case_dir/eligibility.tsv" \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT="$EXPORT_LIMIT" \
    >"$candidate_report"
  write_runner_summaries "$baseline_report" "$candidate_report" "$case_dir/candidate"
  printf '%s\n' "$candidate_report"
}

run_neat1_attempt_consumer_pair() {
  local workload="$1"
  local target="$2"
  local query="$3"
  local case_dir="$WORK/$workload"
  local baseline_report="$case_dir/baseline.report.json"
  local candidate_report="$case_dir/candidate.report.json"

  build_bin_if_needed
  for path in "$BIN" "$target" "$query"; do
    if [[ ! -e "$path" ]]; then
      echo "missing dependency for $workload: $path" >&2
      return 1
    fi
  done
  rm -rf "$case_dir"
  mkdir -p "$case_dir/candidate"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$query" \
    --rule 0 \
    --output-mode lite \
    --workers 1 \
    --work-dir "$case_dir/baseline" \
    --manifest "$case_dir/baseline/run_manifest.json" \
    >"$baseline_report"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$query" \
    --rule 0 \
    --output-mode lite \
    --workers 1 \
    --work-dir "$case_dir/candidate" \
    --manifest "$case_dir/candidate/run_manifest.json" \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_EXTEND_ATTEMPT_PROBE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_FULL_REPLAY_PROBE=1 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS=0 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN=2812 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP=512 \
    --env FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS=0 \
    --env FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1 \
    --env FASIM_ALIGN_GASAL2=1 \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1 \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT="$case_dir/eligibility.tsv" \
    --env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT="$EXPORT_LIMIT" \
    >"$candidate_report"
  write_runner_summaries "$baseline_report" "$candidate_report" "$case_dir/candidate"
  printf '%s\n' "$candidate_report"
}

run_workload_if_requested() {
  local workload="$1"
  local target="$2"
  local query="$3"
  local rule="$4"
  if [[ "$RUN_WORKLOADS" != "1" ]]; then
    return 1
  fi
  case "$workload" in
    malat1_group32_two_contract)
      run_malat1_group32_pair "$workload" "$target" "$query"
      ;;
    neat1_attempt_consumer_control)
      run_neat1_attempt_consumer_pair "$workload" "$target" "$query"
      ;;
    *)
      run_direct_lite_pair "$workload" "$target" "$query" "$rule"
      ;;
  esac
}

has_eligibility_metrics() {
  local stderr="$1"
  [[ -s "$stderr" ]] && grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_' "$stderr"
}

find_metric_stderr() {
  local pattern="$1"
  find "$ARTIFACT_ROOT" -path "$pattern" -name 'stderr.log' -type f 2>/dev/null |
    while IFS= read -r stderr; do
      if has_eligibility_metrics "$stderr"; then
        printf '%s\n' "$stderr"
        return 0
      fi
    done
}

write_missing_row() {
  local workload="$1"
  local target="$2"
  local query="$3"
  local mode="$4"
  local workers="$5"
  local group_target_records="$6"
  local output_mode="$7"
  local notes="$8"
  local out="$WORK/$workload.row.tsv"
  python3 "$SUMMARIZER" \
    --workload-name "$workload" \
    --status missing \
    --target "$target" \
    --query "$query" \
    --mode "$mode" \
    --workers "$workers" \
    --group-target-records "$group_target_records" \
    --output-mode "$output_mode" \
    --gasal2-runtime-env "FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1" \
    --artifact-provenance "$ARTIFACT_ROOT" \
    --notes "$notes" \
    --output "$out"
  printf '%s\n' "$out"
}

write_complete_row() {
  local workload="$1"
  local stderr="$2"
  local target="$3"
  local query="$4"
  local mode="$5"
  local workers="$6"
  local group_target_records="$7"
  local output_mode="$8"
  local notes="$9"
  local out="$WORK/$workload.row.tsv"
  local artifact_dir
  artifact_dir="$(dirname "$stderr")"
  local runner_report_args=()
  local stderr_args=("--stderr" "$stderr")
  if [[ "$stderr" == *.json ]]; then
    runner_report_args=("--runner-report" "$stderr")
    stderr_args=()
  fi
  python3 "$SUMMARIZER" \
    --workload-name "$workload" \
    --status complete \
    "${stderr_args[@]}" \
    "${runner_report_args[@]}" \
    --top5-summary "$artifact_dir/top5.summary" \
    --full-lite-summary "$artifact_dir/full_lite.summary" \
    --tfosorted-summary "$artifact_dir/tfosorted.summary" \
    --target "$target" \
    --query "$query" \
    --mode "$mode" \
    --workers "$workers" \
    --group-target-records "$group_target_records" \
    --output-mode "$output_mode" \
    --gasal2-runtime-env "FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1" \
    --artifact-provenance "$artifact_dir" \
    --notes "$notes" \
    --output "$out"
  printf '%s\n' "$out"
}

collect_row() {
  local workload="$1"
  local find_pattern="$2"
  local target="$3"
  local query="$4"
  local mode="$5"
  local workers="$6"
  local group_target_records="$7"
  local output_mode="$8"
  local missing_notes="$9"
  local runnable_target="${10:-}"
  local runnable_query="${11:-}"
  local rule="${12:-0}"
  local stderr
  local notes="reused artifact with #171 eligibility counters"
  stderr="$(find_metric_stderr "$find_pattern" | head -n 1 || true)"
  if [[ -z "$stderr" && -n "$runnable_target" && -n "$runnable_query" ]]; then
    stderr="$(run_workload_if_requested "$workload" "$runnable_target" "$runnable_query" "$rule" || true)"
    notes="fresh RUN_WORKLOADS=1 run with #171 eligibility counters"
  fi
  if [[ -n "$stderr" ]]; then
    write_complete_row \
      "$workload" \
      "$stderr" \
      "$target" \
      "$query" \
      "$mode" \
      "$workers" \
      "$group_target_records" \
      "$output_mode" \
      "$notes"
  else
    write_missing_row \
      "$workload" \
      "$target" \
      "$query" \
      "$mode" \
      "$workers" \
      "$group_target_records" \
      "$output_mode" \
      "$missing_notes"
  fi
}

if [[ "$RUN_WORKLOADS" == "1" ]]; then
  mkdir -p "$WORK/inputs"
  if [[ -s "$MALAT1_DNA" ]]; then
    first_records "$MALAT1_DNA" "$MALAT1_RECORD_LIMIT" "$WORK/inputs/malat1_first${MALAT1_RECORD_LIMIT}.fa"
  fi
  if [[ -s "$NEAT1_DNA" ]]; then
    first_records "$NEAT1_DNA" "$NEAT1_RECORD_LIMIT" "$WORK/inputs/neat1_first${NEAT1_RECORD_LIMIT}.fa"
  fi
fi

rows=()
rows+=("$(collect_row \
  chr22_full_plain \
  '*/chr22*/*' \
  chr22.fa \
  H19.fa \
  full_plain \
  1 \
  null \
  lite \
  'no chr22 full stderr with PR #171 eligibility counters found; older speed artifacts are context only' \
  "$CHR22_TARGET" \
  "$H19_RNA" \
  0)")

rows+=("$(collect_row \
  malat1_group32_two_contract \
  '*/malat1*/*' \
  MALAT1-DNAseq.fa \
  MALAT1.fa \
  group32_two_contract \
  1 \
  32 \
  lite \
  'no MALAT1 group32 stderr with PR #171 eligibility counters found' \
  "$WORK/inputs/malat1_first${MALAT1_RECORD_LIMIT}.fa" \
  "$MALAT1_RNA" \
  0)")

rows+=("$(collect_row \
  neat1_attempt_consumer_control \
  '*/neat1*/*' \
  NEAT1-DNAseq.fa \
  NEAT1.fa \
  attempt_consumer_control \
  1 \
  null \
  lite \
  'no NEAT1 attempt-consumer stderr with PR #171 eligibility counters found' \
  "$WORK/inputs/neat1_first${NEAT1_RECORD_LIMIT}.fa" \
  "$NEAT1_RNA" \
  0)")

{
  head -n 1 "${rows[0]}"
  for row in "${rows[@]}"; do
    tail -n +2 "$row"
  done
} >"$RESULT_TSV"

printf 'result_tsv=%s\n' "$RESULT_TSV"
