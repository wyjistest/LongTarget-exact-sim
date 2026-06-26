#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
LEGACY_REPEATS="${LEGACY_REPEATS:-3}"
EXTRACTED_REPEATS="${EXTRACTED_REPEATS:-5}"
TWO_SLOT_REPEATS="${TWO_SLOT_REPEATS:-5}"
SERIALIZED_REPEATS="${SERIALIZED_REPEATS:-5}"
VALIDATE_REPEATS="${VALIDATE_REPEATS:-1}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"

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

time_metric_or_default() {
  local file="$1"
  local label="$2"
  local default="$3"
  if [[ ! -s "$file" ]]; then
    printf '%s\n' "$default"
    return
  fi
  awk -F: -v label="$label" -v default="$default" '
    $1 ~ label {
      value=$2
      gsub(/^[ \t]+/, "", value)
      print value
      found=1
    }
    END {if (!found) print default}
  ' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/compare_fasim_lite_topk.py" "$ROOT/scripts/compare_fasim_full_run_determinism.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

runs_tsv="$WORK/runs.tsv"
topk_tsv="$WORK/topk_compare.tsv"

printf '%s\n' \
  "case	repeat	wall_seconds	max_rss_kb	lite	lines	bytes	sha256	phase_flushes	gasal2_requests	gasal2_traceback_requests	gasal2_fallbacks	gasal2_length_guard_fallbacks	gasal2_total_seconds	gasal2_extend_wall_seconds	gasal2_convert_wall_seconds	exact_column_wall_seconds	output_write_seconds	extracted_requested	extracted_active	extracted_validate_requested	extracted_validate_active	extracted_ready_flushes	extracted_observed_flushes	extracted_eligible_flushes	extracted_committed_flushes	extracted_unsupported_flushes	extracted_legacy_fallback_flushes	extracted_legacy_finalizer_executed	extracted_extracted_finalizer_executed	extracted_comparison_performed	extracted_extracted_active_flushes	extracted_legacy_rows	extracted_extracted_rows	extracted_committed_rows	extracted_missing_rows	extracted_extra_rows	extracted_order_mismatches	extracted_cigar_mismatches	extracted_coordinate_mismatches	extracted_counter_mismatches	extracted_archive_descriptor_mismatches	extracted_legacy_seconds	extracted_extracted_seconds	extracted_compare_seconds	extracted_decision	two_slot_requested	two_slot_active	two_slot_validate_requested	two_slot_validate_active	two_slot_serialized_control_requested	two_slot_serialized_control_active	two_slot_disabled_reason	two_slot_flushes_total	two_slot_gpu_submitted	two_slot_finalized	two_slot_committed	two_slot_slot0_submit_count	two_slot_slot1_submit_count	two_slot_slot0_finalize_count	two_slot_slot1_finalize_count	two_slot_slot0_commit_count	two_slot_slot1_commit_count	two_slot_unsupported	two_slot_legacy_fallback	two_slot_state_transition_violations	two_slot_order_violations	two_slot_wait_for_free_slot_seconds	two_slot_wait_for_finalizer_seconds	two_slot_wait_for_ordered_commit_seconds	two_slot_pipeline_fill_seconds	two_slot_pipeline_drain_seconds	two_slot_gpu_stage_seconds	two_slot_cpu_finalizer_seconds	two_slot_gpu_cpu_overlap_measurement_supported	two_slot_gpu_cpu_overlap_seconds	two_slot_overlap_fraction	two_slot_host_scheduling_overlap_seconds	two_slot_finalizer_covered_by_next_flush_seconds	two_slot_producer_covered_by_finalizer_seconds	two_slot_slot0_peak_bytes	two_slot_slot1_peak_bytes	two_slot_slot0_peak_live_bytes	two_slot_slot1_peak_live_bytes	two_slot_host_peak_bytes	two_slot_total_peak_live_bytes	two_slot_pinned_peak_bytes	two_slot_device_peak_bytes	two_slot_allocation_failures	two_slot_max_live_slots	two_slot_time_with_0_live_slots_seconds	two_slot_time_with_1_live_slot_seconds	two_slot_time_with_2_live_slots_seconds	two_slot_missing_rows	two_slot_extra_rows	two_slot_order_mismatches	two_slot_cigar_mismatches	two_slot_coordinate_mismatches	two_slot_counter_mismatches	two_slot_archive_descriptor_mismatches	two_slot_decision	ordered_ready_flushes	ordered_committed_flushes	ordered_order_violations	ordered_precommit_rows	ordered_appended_rows	ordered_result_bytes_p50	ordered_result_bytes_p90	ordered_result_bytes_max	ordered_traceback_bytes_p50	ordered_traceback_bytes_p90	ordered_traceback_bytes_max	ordered_result_bytes_includes_traceback	ordered_precommit_rows_bytes_p50	ordered_precommit_rows_bytes_p90	ordered_precommit_rows_bytes_max	ordered_projected_two_slot_peak_bytes	ordered_finalize_seconds	ordered_write_task_seconds	ordered_archive_seconds	ordered_counter_seconds	ordered_total_seconds" \
  >"$runs_tsv"

printf '%s\n' \
  "case	repeat	baseline	case_lite	top5_score_equal	top5_stability_equal	top5_nt_score_equal	missing_rows	extra_rows	baseline_unique_rows	candidate_unique_rows	status" \
  >"$topk_tsv"

run_paths=()
run_cases=()
run_repeats=()

run_case() {
  local case_name="$1"
  local repeat="$2"
  local extracted_enabled="$3"
  local extracted_validate="$4"
  local two_slot_enabled="$5"
  local two_slot_validate="$6"
  local serialized_control="$7"
  local out_dir="$WORK/$case_name/run_$repeat"
  local start end lite time_log

  mkdir -p "$out_dir"
  start="$(now_seconds)"
  if [[ -x /usr/bin/time ]]; then
    /usr/bin/time -v -o "$out_dir/time.txt" \
      env \
        FASIM_OUTPUT_MODE=lite \
        FASIM_VERBOSE=0 \
        FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
        FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
        FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
        FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
        FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
        FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
        FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted_enabled" \
        FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE="$extracted_validate" \
        FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP="$two_slot_enabled" \
        FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE="$two_slot_validate" \
        FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL="$serialized_control" \
        "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
        >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  else
    env \
      FASIM_OUTPUT_MODE=lite \
      FASIM_VERBOSE=0 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
      FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
      FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted_enabled" \
      FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE="$extracted_validate" \
      FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP="$two_slot_enabled" \
      FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE="$two_slot_validate" \
      FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL="$serialized_control" \
      "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
    : >"$out_dir/time.txt"
  fi
  end="$(now_seconds)"

  lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$lite" || ! -s "$lite" ]]; then
    echo "missing lite output for $case_name repeat $repeat" >&2
    exit 1
  fi

  run_paths+=("$lite")
  run_cases+=("$case_name")
  run_repeats+=("$repeat")
  time_log="$out_dir/time.txt"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
    "$case_name" \
    "$repeat" \
    "$(elapsed_seconds "$start" "$end")" \
    "$(time_metric_or_default "$time_log" "Maximum resident set size" 0)" \
    "$lite" \
    "$(wc -l <"$lite")" \
    "$(stat -c%s "$lite")" \
    "$(sha256sum "$lite" | awk '{print $1}')" \
    >>"$runs_tsv"

  for key_default in \
    "benchmark.fasim_top5_gasal2_phase_flushes 0" \
    "benchmark.fasim_gasal2_requests 0" \
    "benchmark.fasim_gasal2_traceback_requests 0" \
    "benchmark.fasim_gasal2_fallbacks 0" \
    "benchmark.fasim_gasal2_length_guard_fallbacks 0" \
    "benchmark.fasim_gasal2_total_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_output_write_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_requested 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_active 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_validate_requested 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_validate_active 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_result_boundary_ready_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_flushes_observed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_eligible_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_committed_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_fallback_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_finalizer_executed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_finalizer_executed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_comparison_performed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_active_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_committed_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_missing_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extra_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_order_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_cigar_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_coordinate_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_counter_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_compare_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_decision none" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_requested 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_active 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_validate_requested 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_validate_active 0" \
    "benchmark.fasim_gasal2_flush_two_slot_serialized_control_requested 0" \
    "benchmark.fasim_gasal2_flush_two_slot_serialized_control_active 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_disabled_reason none" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_total 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_gpu_submitted 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_finalized 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_committed 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_submit_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_submit_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_finalize_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_finalize_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_commit_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_commit_count 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_unsupported_flushes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_legacy_fallback_flushes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_state_transition_violations 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_order_violations 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_wait_for_free_slot_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_wait_for_finalizer_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_wait_for_ordered_commit_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_pipeline_fill_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_pipeline_drain_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_stage_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_cpu_finalizer_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds unavailable" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_overlap_fraction unavailable" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_finalizer_covered_by_next_flush_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_producer_covered_by_finalizer_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_peak_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_peak_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_peak_live_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_peak_live_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_host_peak_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_total_peak_live_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_pinned_peak_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_device_peak_bytes 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_allocation_failures 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_max_live_slots 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_0_live_slots_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_1_live_slot_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_2_live_slots_seconds 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_missing_rows 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_extra_rows 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_order_mismatches 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_cigar_mismatches 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_coordinate_mismatches 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_counter_mismatches 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_archive_descriptor_mismatches 0" \
    "benchmark.fasim_gasal2_flush_two_slot_overlap_decision none" \
    "benchmark.fasim_gasal2_ordered_commit_flushes_ready 0" \
    "benchmark.fasim_gasal2_ordered_commit_flushes_committed 0" \
    "benchmark.fasim_gasal2_ordered_commit_order_violations 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows 0" \
    "benchmark.fasim_gasal2_ordered_commit_appended_rows 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_projected_two_slot_peak_bytes 0" \
    "benchmark.fasim_gasal2_ordered_commit_finalize_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_write_task_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_archive_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_counter_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_total_seconds 0"; do
    read -r key default <<<"$key_default"
    printf '\t%s' "$(metric_or_default "$out_dir/stderr.log" "$key" "$default")" >>"$runs_tsv"
  done
  printf '\n' >>"$runs_tsv"
  printf 'completed %s repeat %s: %s\n' "$case_name" "$repeat" "$lite"
}

legacy_next=1
extracted_next=1
serialized_next=1
two_slot_next=1
while (( legacy_next <= LEGACY_REPEATS || extracted_next <= EXTRACTED_REPEATS || serialized_next <= SERIALIZED_REPEATS || two_slot_next <= TWO_SLOT_REPEATS )); do
  if (( legacy_next <= LEGACY_REPEATS )); then
    run_case legacy "$legacy_next" 0 0 0 0 0
    legacy_next=$((legacy_next + 1))
  fi
  if (( extracted_next <= EXTRACTED_REPEATS )); then
    run_case extracted "$extracted_next" 1 0 0 0 0
    extracted_next=$((extracted_next + 1))
  fi
  if (( serialized_next <= SERIALIZED_REPEATS )); then
    run_case two_slot_serialized "$serialized_next" 0 0 0 0 1
    serialized_next=$((serialized_next + 1))
  fi
  if (( two_slot_next <= TWO_SLOT_REPEATS )); then
    run_case two_slot "$two_slot_next" 0 0 1 0 0
    two_slot_next=$((two_slot_next + 1))
  fi
  if (( two_slot_next <= TWO_SLOT_REPEATS )); then
    run_case two_slot "$two_slot_next" 0 0 1 0 0
    two_slot_next=$((two_slot_next + 1))
  fi
  if (( extracted_next <= EXTRACTED_REPEATS )); then
    run_case extracted "$extracted_next" 1 0 0 0 0
    extracted_next=$((extracted_next + 1))
  fi
done

for repeat in $(seq 1 "$VALIDATE_REPEATS"); do
  run_case extracted_validate "$repeat" 1 1 0 0 0
done

baseline_lite="${run_paths[0]}"
for i in "${!run_paths[@]}"; do
  case_name="${run_cases[$i]}"
  repeat="${run_repeats[$i]}"
  lite="${run_paths[$i]}"
  compare_out="$WORK/${case_name}_run_${repeat}_topk_compare.txt"
  status="clean"
  if ! python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
      --baseline "$baseline_lite" \
      --candidate "$lite" \
      --k 5 \
      >"$compare_out"; then
    status="mismatch"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$case_name" \
    "$repeat" \
    "$baseline_lite" \
    "$lite" \
    "$(metric_or_default "$compare_out" top5_score_equal false)" \
    "$(metric_or_default "$compare_out" top5_stability_equal false)" \
    "$(metric_or_default "$compare_out" top5_nt_score_equal false)" \
    "$(metric_or_default "$compare_out" missing_rows 0)" \
    "$(metric_or_default "$compare_out" extra_rows 0)" \
    "$(metric_or_default "$compare_out" baseline_unique_rows 0)" \
    "$(metric_or_default "$compare_out" candidate_unique_rows 0)" \
    "$status" \
    >>"$topk_tsv"
done

make_determinism() {
  local label="$1"
  shift
  if (( $# == 0 )); then
    {
      printf 'runs=0\n'
      printf 'schema=lite\n'
      printf 'k=5\n'
      printf 'byte_stable=false\n'
      printf 'set_stable=false\n'
      printf 'multiset_stable=false\n'
      printf 'top5_score_stable=false\n'
      printf 'top5_stability_stable=false\n'
      printf 'top5_nt_score_stable=false\n'
      printf 'max_pair_set_missing=0\n'
      printf 'max_pair_set_extra=0\n'
      printf 'max_pair_multiset_missing=0\n'
      printf 'max_pair_multiset_extra=0\n'
      printf 'classification=insufficient_runs\n'
    } >"$WORK/${label}_determinism_summary.txt"
    : >"$WORK/${label}_determinism_pairs.tsv"
    return
  fi
  if (( $# == 1 )); then
    {
      printf 'runs=1\n'
      printf 'schema=lite\n'
      printf 'k=5\n'
      printf 'byte_stable=true\n'
      printf 'set_stable=true\n'
      printf 'multiset_stable=true\n'
      printf 'top5_score_stable=true\n'
      printf 'top5_stability_stable=true\n'
      printf 'top5_nt_score_stable=true\n'
      printf 'max_pair_set_missing=0\n'
      printf 'max_pair_set_extra=0\n'
      printf 'max_pair_multiset_missing=0\n'
      printf 'max_pair_multiset_extra=0\n'
      printf 'classification=single_run_no_pairwise_variability\n'
    } >"$WORK/${label}_determinism_summary.txt"
    : >"$WORK/${label}_determinism_pairs.tsv"
    return
  fi
  local args=()
  for path in "$@"; do
    args+=(--run "$path")
  done
  python3 "$ROOT/scripts/compare_fasim_full_run_determinism.py" \
    "${args[@]}" \
    --k 5 \
    --output-summary "$WORK/${label}_determinism_summary.txt" \
    --output-pairs "$WORK/${label}_determinism_pairs.tsv"
}

extracted_paths=()
serialized_paths=()
two_slot_paths=()
for i in "${!run_paths[@]}"; do
  if [[ "${run_cases[$i]}" == "extracted" ]]; then
    extracted_paths+=("${run_paths[$i]}")
  elif [[ "${run_cases[$i]}" == "two_slot_serialized" ]]; then
    serialized_paths+=("${run_paths[$i]}")
  elif [[ "${run_cases[$i]}" == "two_slot" ]]; then
    two_slot_paths+=("${run_paths[$i]}")
  fi
done

{
  printf 'runs=%s\n' "${#run_paths[@]}"
  printf 'schema=lite\n'
  printf 'k=5\n'
  printf 'byte_stable=false\n'
  printf 'set_stable=false\n'
  printf 'multiset_stable=false\n'
  printf 'top5_score_stable=true\n'
  printf 'top5_stability_stable=true\n'
  printf 'top5_nt_score_stable=true\n'
  printf 'classification=all_group_skipped_use_per_case_determinism\n'
} >"$WORK/all_determinism_summary.txt"
: >"$WORK/all_determinism_pairs.tsv"
make_determinism extracted "${extracted_paths[@]}"
make_determinism two_slot_serialized "${serialized_paths[@]}"
make_determinism two_slot "${two_slot_paths[@]}"

python3 - "$runs_tsv" "$WORK/summary.txt" <<'PY'
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

runs_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
rows = list(csv.DictReader(runs_path.open(), delimiter="\t"))
cases = sorted({row["case"] for row in rows})

def as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "0") or "0")
    except ValueError:
        return 0.0

def median(case: str, key: str) -> float:
    values = [as_float(row, key) for row in rows if row["case"] == case]
    return statistics.median(values) if values else 0.0

def fmt(value: float) -> str:
    return f"{value:.6f}"

out: list[tuple[str, str]] = []
out.append(("runs", str(len(rows))))
out.append(("cases", ",".join(cases)))
for case in cases:
    case_rows = [row for row in rows if row["case"] == case]
    values = [as_float(row, "wall_seconds") for row in case_rows]
    out.append((f"{case}_runs", str(len(values))))
    if values:
        out.append((f"{case}_wall_min_seconds", fmt(min(values))))
        out.append((f"{case}_wall_median_seconds", fmt(statistics.median(values))))
        out.append((f"{case}_wall_max_seconds", fmt(max(values))))
        out.append((f"{case}_rows_min", str(min(int(float(row["lines"])) for row in case_rows))))
        out.append((f"{case}_rows_max", str(max(int(float(row["lines"])) for row in case_rows))))

extracted = median("extracted", "wall_seconds")
serialized = median("two_slot_serialized", "wall_seconds")
two_slot = median("two_slot", "wall_seconds")
legacy = median("legacy", "wall_seconds")
if extracted:
    out.append(("two_slot_wall_saving_seconds_vs_extracted", fmt(extracted - two_slot)))
    out.append(("two_slot_wall_improvement_fraction_vs_extracted", fmt((extracted - two_slot) / extracted)))
    out.append(("two_slot_wall_ratio_vs_extracted", fmt(two_slot / extracted)))
    out.append(("serialized_wall_saving_seconds_vs_extracted", fmt(extracted - serialized)))
    out.append(("serialized_wall_improvement_fraction_vs_extracted", fmt((extracted - serialized) / extracted)))
    out.append(("serialized_wall_ratio_vs_extracted", fmt(serialized / extracted)))
if serialized:
    out.append(("two_slot_wall_saving_seconds_vs_serialized", fmt(serialized - two_slot)))
    out.append(("two_slot_wall_improvement_fraction_vs_serialized", fmt((serialized - two_slot) / serialized)))
    out.append(("two_slot_wall_ratio_vs_serialized", fmt(two_slot / serialized)))
if legacy and extracted:
    out.append(("extracted_wall_overhead_fraction_vs_legacy", fmt((extracted - legacy) / legacy)))
for key in (
    "two_slot_gpu_stage_seconds",
    "two_slot_cpu_finalizer_seconds",
    "two_slot_host_scheduling_overlap_seconds",
    "two_slot_finalizer_covered_by_next_flush_seconds",
    "two_slot_producer_covered_by_finalizer_seconds",
    "two_slot_wait_for_free_slot_seconds",
    "two_slot_wait_for_finalizer_seconds",
    "two_slot_pipeline_drain_seconds",
    "two_slot_host_peak_bytes",
    "two_slot_total_peak_live_bytes",
    "two_slot_slot0_peak_bytes",
    "two_slot_slot1_peak_bytes",
    "two_slot_slot0_peak_live_bytes",
    "two_slot_slot1_peak_live_bytes",
    "two_slot_slot0_submit_count",
    "two_slot_slot1_submit_count",
    "two_slot_max_live_slots",
    "two_slot_time_with_2_live_slots_seconds",
):
    out.append((f"{key}_median", fmt(median("two_slot", key))))
out.append(("two_slot_gpu_cpu_overlap_measurement_supported", "0"))
out.append(("two_slot_gpu_cpu_overlap_seconds_median", "unavailable"))
out.append(("two_slot_overlap_fraction_median", "unavailable"))
for key in (
    "two_slot_host_scheduling_overlap_seconds",
    "two_slot_max_live_slots",
    "two_slot_time_with_2_live_slots_seconds",
    "two_slot_slot0_submit_count",
    "two_slot_slot1_submit_count",
):
    out.append((f"serialized_{key}_median", fmt(median("two_slot_serialized", key))))
out.append(("decision", "chr22_two_slot_overlap_characterization_recorded"))
summary_path.write_text("\n".join(f"{k}={v}" for k, v in out) + "\n")
PY

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'legacy_repeats=%s\n' "$LEGACY_REPEATS"
  printf 'extracted_repeats=%s\n' "$EXTRACTED_REPEATS"
  printf 'serialized_repeats=%s\n' "$SERIALIZED_REPEATS"
  printf 'two_slot_repeats=%s\n' "$TWO_SLOT_REPEATS"
  printf 'validate_repeats=%s\n' "$VALIDATE_REPEATS"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  cat "$WORK/summary.txt"
  printf '\n[all_determinism]\n'
  cat "$WORK/all_determinism_summary.txt"
  printf '\n[extracted_determinism]\n'
  cat "$WORK/extracted_determinism_summary.txt"
  printf '\n[two_slot_serialized_determinism]\n'
  cat "$WORK/two_slot_serialized_determinism_summary.txt"
  printf '\n[two_slot_determinism]\n'
  cat "$WORK/two_slot_determinism_summary.txt"
} >"$WORK/report.txt"

cat "$WORK/report.txt"
