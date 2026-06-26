#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
NVTX_BIN="${NVTX_BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_nvtx"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix_v2"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
REPEATS="${REPEATS:-3}"
VALIDATE_REPEATS="${VALIDATE_REPEATS:-1}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
RUN_NSIGHT="${RUN_NSIGHT:-1}"
NSIGHT_WORKLOADS="${NSIGHT_WORKLOADS:-chr22_full}"
WORKLOAD_SPECS="${WORKLOAD_SPECS:-chr21_full:$ROOT/.tmp/gasal2_hg38_archive_first_rule0_run/shards/chr21.fa:$REPEATS,chr22_full:$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa:$REPEATS,chr11_full:$ROOT/.tmp/gasal2_hg38_archive_first_rule0_run/shards/chr11.fa:$REPEATS}"

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

contains_workload() {
  local needle="$1"
  local item
  IFS=',' read -ra items <<<"$NSIGHT_WORKLOADS"
  for item in "${items[@]}"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

if [[ "$RUN_NSIGHT" == "1" && ! -x "$NVTX_BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2-nvtx FASIM_GASAL2_NVTX_TARGET="$NVTX_BIN"
  )
fi

for path in "$BIN" "$RNA" "$ROOT/scripts/compare_fasim_lite_topk.py" "$ROOT/scripts/compare_fasim_full_run_determinism.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

runs_tsv="$WORK/runs.tsv"
topk_tsv="$WORK/topk_compare.tsv"
nsight_tsv="$WORK/nsight.tsv"

printf '%s\n' \
  "schema_version	workload	mode	repeat	target	wall_seconds	max_rss_kb	lite	lines	bytes	sha256	phase_flushes	gasal2_requests	gasal2_traceback_requests	gasal2_fallbacks	gasal2_length_guard_fallbacks	gasal2_total_seconds	gasal2_extend_wall_seconds	gasal2_convert_wall_seconds	exact_column_wall_seconds	output_write_seconds	extracted_requested	extracted_active	extracted_validate_requested	extracted_validate_active	extracted_ready_flushes	extracted_observed_flushes	extracted_eligible_flushes	extracted_committed_flushes	extracted_unsupported_flushes	extracted_legacy_fallback_flushes	extracted_legacy_finalizer_executed	extracted_extracted_finalizer_executed	extracted_comparison_performed	extracted_extracted_active_flushes	extracted_legacy_rows	extracted_extracted_rows	extracted_committed_rows	extracted_missing_rows	extracted_extra_rows	extracted_order_mismatches	extracted_cigar_mismatches	extracted_coordinate_mismatches	extracted_counter_mismatches	extracted_archive_descriptor_mismatches	extracted_legacy_seconds	extracted_extracted_seconds	extracted_compare_seconds	extracted_decision	two_slot_requested	two_slot_active	two_slot_validate_requested	two_slot_validate_active	two_slot_serialized_control_requested	two_slot_serialized_control_active	two_slot_disabled_reason	two_slot_flushes_total	two_slot_gpu_submitted	two_slot_finalized	two_slot_committed	two_slot_slot0_submit_count	two_slot_slot1_submit_count	two_slot_slot0_finalize_count	two_slot_slot1_finalize_count	two_slot_slot0_commit_count	two_slot_slot1_commit_count	two_slot_unsupported	two_slot_legacy_fallback	two_slot_state_transition_violations	two_slot_order_violations	two_slot_wait_for_free_slot_seconds	two_slot_wait_for_finalizer_seconds	two_slot_wait_for_ordered_commit_seconds	two_slot_pipeline_fill_seconds	two_slot_pipeline_drain_seconds	two_slot_gpu_stage_seconds	two_slot_cpu_finalizer_seconds	two_slot_gpu_cpu_overlap_measurement_supported	two_slot_gpu_cpu_overlap_seconds	two_slot_overlap_fraction	two_slot_host_scheduling_overlap_seconds	two_slot_finalizer_covered_by_next_flush_seconds	two_slot_producer_covered_by_finalizer_seconds	two_slot_slot0_peak_bytes	two_slot_slot1_peak_bytes	two_slot_slot0_peak_live_bytes	two_slot_slot1_peak_live_bytes	two_slot_host_peak_bytes	two_slot_total_peak_live_bytes	two_slot_pinned_peak_bytes	two_slot_device_peak_bytes	two_slot_allocation_failures	two_slot_max_live_slots	two_slot_time_with_0_live_slots_seconds	two_slot_time_with_1_live_slot_seconds	two_slot_time_with_2_live_slots_seconds	two_slot_missing_rows	two_slot_extra_rows	two_slot_order_mismatches	two_slot_cigar_mismatches	two_slot_coordinate_mismatches	two_slot_counter_mismatches	two_slot_archive_descriptor_mismatches	two_slot_decision	ordered_ready_flushes	ordered_committed_flushes	ordered_order_violations	ordered_precommit_rows	ordered_appended_rows	ordered_result_bytes_p50	ordered_result_bytes_p90	ordered_result_bytes_max	ordered_traceback_bytes_p50	ordered_traceback_bytes_p90	ordered_traceback_bytes_max	ordered_result_bytes_includes_traceback	ordered_precommit_rows_bytes_p50	ordered_precommit_rows_bytes_p90	ordered_precommit_rows_bytes_max	ordered_projected_two_slot_peak_bytes	ordered_finalize_seconds	ordered_write_task_seconds	ordered_archive_seconds	ordered_counter_seconds	ordered_total_seconds" \
  >"$runs_tsv"

printf '%s\n' \
  "schema_version	workload	mode	repeat	baseline	case_lite	top5_score_equal	top5_stability_equal	top5_nt_score_equal	missing_rows	extra_rows	baseline_unique_rows	candidate_unique_rows	status" \
  >"$topk_tsv"

printf '%s\n' \
  "schema_version	workload	profile	sqlite	host_scheduling_overlap_seconds	gpu_activity_union_seconds	kernel_union_seconds	memcpy_union_seconds	cpu_finalizer_seconds	cpu_finalizer_gpu_activity_overlap_seconds	cpu_finalizer_kernel_overlap_seconds	cpu_finalizer_memcpy_overlap_seconds	cpu_finalizer_gpu_activity_overlap_fraction" \
  >"$nsight_tsv"

run_paths=()
run_workloads=()
run_modes=()
run_repeats=()
workload_names=()
workload_targets=()
workload_repeats=()

IFS=',' read -ra spec_items <<<"$WORKLOAD_SPECS"
for spec in "${spec_items[@]}"; do
  IFS=':' read -r workload_name workload_target workload_repeats_value <<<"$spec"
  if [[ -z "$workload_name" || -z "$workload_target" || -z "$workload_repeats_value" ]]; then
    echo "bad workload spec: $spec" >&2
    exit 1
  fi
  if [[ ! -s "$workload_target" ]]; then
    echo "missing workload target: $workload_name => $workload_target" >&2
    exit 1
  fi
  workload_names+=("$workload_name")
  workload_targets+=("$workload_target")
  workload_repeats+=("$workload_repeats_value")
done

run_case() {
  local workload="$1"
  local target="$2"
  local mode="$3"
  local repeat="$4"
  local extracted_enabled=0
  local extracted_validate=0
  local two_slot_enabled=0
  local two_slot_validate=0
  local serialized_control=0
  local out_dir="$WORK/$workload/$mode/run_$repeat"
  local start end lite time_log

  case "$mode" in
    extracted)
      extracted_enabled=1
      ;;
    two_slot_serialized)
      serialized_control=1
      ;;
    two_slot)
      two_slot_enabled=1
      ;;
    two_slot_validate)
      two_slot_enabled=1
      two_slot_validate=1
      ;;
    *)
      echo "bad mode: $mode" >&2
      exit 1
      ;;
  esac

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
        "$BIN" -f1 "$target" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
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
      "$BIN" -f1 "$target" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
    : >"$out_dir/time.txt"
  fi
  end="$(now_seconds)"

  lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$lite" || ! -s "$lite" ]]; then
    echo "missing lite output for $workload $mode repeat $repeat" >&2
    exit 1
  fi

  run_paths+=("$lite")
  run_workloads+=("$workload")
  run_modes+=("$mode")
  run_repeats+=("$repeat")
  time_log="$out_dir/time.txt"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
    "2" \
    "$workload" \
    "$mode" \
    "$repeat" \
    "$target" \
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
  printf 'completed %s %s repeat %s: %s\n' "$workload" "$mode" "$repeat" "$lite"
}

run_nsight_case() {
  local workload="$1"
  local target="$2"
  local out_dir="$WORK/$workload/nsight_two_slot"
  local sqlite="$out_dir/profile.sqlite"
  local summary="$out_dir/overlap_summary.txt"
  mkdir -p "$out_dir/out"
  nsys profile \
    --trace=cuda,nvtx,osrt \
    --sample=none \
    --force-overwrite=true \
    --output="$out_dir/profile" \
    env \
      FASIM_GASAL2_NVTX_TRACE=1 \
      FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1 \
      FASIM_OUTPUT_MODE=lite \
      FASIM_VERBOSE=0 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
      FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
      FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
      "$NVTX_BIN" -f1 "$target" -f2 "$RNA" -r "$RULE" -O "$out_dir/out" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  nsys export \
    --type sqlite \
    --force-overwrite=true \
    --output "$sqlite" \
    "$out_dir/profile.nsys-rep"
  python3 "$ROOT/scripts/summarize_fasim_gasal2_nvtx_overlap.py" \
    "$sqlite" \
    --output "$summary"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "2" \
    "$workload" \
    "$out_dir/profile.nsys-rep" \
    "$sqlite" \
    "$(metric_or_default "$out_dir/stderr.log" benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds 0)" \
    "$(metric_or_default "$summary" gpu_activity_union_seconds 0)" \
    "$(metric_or_default "$summary" kernel_union_seconds 0)" \
    "$(metric_or_default "$summary" memcpy_union_seconds 0)" \
    "$(metric_or_default "$summary" two_slot_cpu_finalizer_seconds 0)" \
    "$(metric_or_default "$summary" two_slot_cpu_finalizer_gpu_activity_overlap_seconds 0)" \
    "$(metric_or_default "$summary" two_slot_cpu_finalizer_kernel_overlap_seconds 0)" \
    "$(metric_or_default "$summary" two_slot_cpu_finalizer_memcpy_overlap_seconds 0)" \
    "$(metric_or_default "$summary" two_slot_cpu_finalizer_gpu_activity_overlap_fraction 0)" \
    >>"$nsight_tsv"
  printf 'completed %s nsight profile: %s\n' "$workload" "$out_dir/profile.nsys-rep"
}

for i in "${!workload_names[@]}"; do
  workload="${workload_names[$i]}"
  target="${workload_targets[$i]}"
  repeats="${workload_repeats[$i]}"
  for repeat in $(seq 1 "$repeats"); do
    run_case "$workload" "$target" extracted "$repeat"
    run_case "$workload" "$target" two_slot_serialized "$repeat"
    run_case "$workload" "$target" two_slot "$repeat"
  done
  for repeat in $(seq 1 "$VALIDATE_REPEATS"); do
    run_case "$workload" "$target" two_slot_validate "$repeat"
  done
  if [[ "$RUN_NSIGHT" == "1" ]] && contains_workload "$workload"; then
    run_nsight_case "$workload" "$target"
  fi
done

for i in "${!run_paths[@]}"; do
  workload="${run_workloads[$i]}"
  mode="${run_modes[$i]}"
  repeat="${run_repeats[$i]}"
  lite="${run_paths[$i]}"
  baseline_lite=""
  for j in "${!run_paths[@]}"; do
    if [[ "${run_workloads[$j]}" == "$workload" &&
          "${run_modes[$j]}" == "extracted" &&
          "${run_repeats[$j]}" == "1" ]]; then
      baseline_lite="${run_paths[$j]}"
      break
    fi
  done
  if [[ -z "$baseline_lite" ]]; then
    echo "missing extracted baseline for $workload" >&2
    exit 1
  fi
  compare_out="$WORK/${workload}_${mode}_run_${repeat}_topk_compare.txt"
  status="clean"
  if ! python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
      --baseline "$baseline_lite" \
      --candidate "$lite" \
      --k 5 \
      >"$compare_out"; then
    status="mismatch"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "2" \
    "$workload" \
    "$mode" \
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
  if (( $# <= 1 )); then
    {
      printf 'runs=%s\n' "$#"
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
      printf 'classification=%s\n' "$([[ $# == 1 ]] && printf single_run_no_pairwise_variability || printf insufficient_runs)"
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

for workload in "${workload_names[@]}"; do
  for mode in extracted two_slot_serialized two_slot; do
    paths=()
    for i in "${!run_paths[@]}"; do
      if [[ "${run_workloads[$i]}" == "$workload" && "${run_modes[$i]}" == "$mode" ]]; then
        paths+=("${run_paths[$i]}")
      fi
    done
    make_determinism "${workload}_${mode}" "${paths[@]}"
  done
done

python3 - "$runs_tsv" "$topk_tsv" "$nsight_tsv" "$WORK/summary.txt" <<'PY'
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

runs = list(csv.DictReader(Path(sys.argv[1]).open(), delimiter="\t"))
topk = list(csv.DictReader(Path(sys.argv[2]).open(), delimiter="\t"))
nsight = list(csv.DictReader(Path(sys.argv[3]).open(), delimiter="\t"))
summary_path = Path(sys.argv[4])

def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "0") or "0")
    except ValueError:
        return 0.0

def med(rows: list[dict[str, str]], key: str) -> float:
    values = [f(row, key) for row in rows]
    return statistics.median(values) if values else 0.0

def fmt(value: float) -> str:
    return f"{value:.6f}"

out: list[tuple[str, str]] = []
workloads = sorted({row["workload"] for row in runs})
out.append(("schema_version", "2"))
out.append(("runtime_device_overlap_supported", "false"))
out.append(("host_scheduling_overlap_available", "true"))
out.append(("device_overlap_measurement", "nsight" if nsight else "not_run"))
out.append(("workloads", ",".join(workloads)))
out.append(("runs", str(len(runs))))
strong_go = 0
for workload in workloads:
    out.append((f"{workload}_runs", str(sum(1 for row in runs if row["workload"] == workload))))
    modes = {}
    for mode in ("extracted", "two_slot_serialized", "two_slot", "two_slot_validate"):
        rows = [row for row in runs if row["workload"] == workload and row["mode"] == mode]
        modes[mode] = rows
        if rows:
            out.append((f"{workload}_{mode}_runs", str(len(rows))))
            out.append((f"{workload}_{mode}_wall_median_seconds", fmt(med(rows, "wall_seconds"))))
            out.append((f"{workload}_{mode}_rows_min", str(min(int(float(row["lines"])) for row in rows))))
            out.append((f"{workload}_{mode}_rows_max", str(max(int(float(row["lines"])) for row in rows))))
    extracted = med(modes["extracted"], "wall_seconds")
    serialized = med(modes["two_slot_serialized"], "wall_seconds")
    two_slot = med(modes["two_slot"], "wall_seconds")
    if extracted and two_slot:
        improvement = (extracted - two_slot) / extracted
        out.append((f"{workload}_two_slot_wall_saving_seconds_vs_extracted", fmt(extracted - two_slot)))
        out.append((f"{workload}_two_slot_wall_improvement_fraction_vs_extracted", fmt(improvement)))
        if improvement >= 0.05:
            strong_go += 1
    if serialized and two_slot:
        out.append((f"{workload}_two_slot_wall_saving_seconds_vs_serialized", fmt(serialized - two_slot)))
        out.append((f"{workload}_two_slot_wall_improvement_fraction_vs_serialized", fmt((serialized - two_slot) / serialized)))
    out.append((f"{workload}_two_slot_host_scheduling_overlap_seconds_median", fmt(med(modes["two_slot"], "two_slot_host_scheduling_overlap_seconds"))))
    out.append((f"{workload}_two_slot_cpu_finalizer_seconds_median", fmt(med(modes["two_slot"], "two_slot_cpu_finalizer_seconds"))))
    out.append((f"{workload}_two_slot_host_peak_bytes_median", fmt(med(modes["two_slot"], "two_slot_host_peak_bytes"))))
    out.append((f"{workload}_two_slot_max_live_slots_median", fmt(med(modes["two_slot"], "two_slot_max_live_slots"))))
    topk_rows = [row for row in topk if row["workload"] == workload and row["mode"] in {"two_slot", "two_slot_serialized", "two_slot_validate"}]
    topk_clean = all(
        row.get("top5_score_equal") == "true" and
        row.get("top5_stability_equal") == "true" and
        row.get("top5_nt_score_equal") == "true"
        for row in topk_rows
    )
    out.append((f"{workload}_top5_clean", "true" if topk_clean else "false"))

for row in nsight:
    workload = row["workload"]
    out.append((f"{workload}_nsight_cpu_finalizer_gpu_activity_overlap_seconds", row["cpu_finalizer_gpu_activity_overlap_seconds"]))
    out.append((f"{workload}_nsight_cpu_finalizer_kernel_overlap_seconds", row["cpu_finalizer_kernel_overlap_seconds"]))
    out.append((f"{workload}_nsight_cpu_finalizer_memcpy_overlap_seconds", row["cpu_finalizer_memcpy_overlap_seconds"]))
    out.append((f"{workload}_nsight_cpu_finalizer_gpu_activity_overlap_fraction", row["cpu_finalizer_gpu_activity_overlap_fraction"]))

out.append(("strong_go_workloads", str(strong_go)))
out.append(("decision", "broader_matrix_recorded"))
summary_path.write_text("\n".join(f"{key}={value}" for key, value in out) + "\n")
PY

{
  printf 'schema_version=2\n'
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'repeats=%s\n' "$REPEATS"
  printf 'validate_repeats=%s\n' "$VALIDATE_REPEATS"
  printf 'run_nsight=%s\n' "$RUN_NSIGHT"
  printf 'nsight_workloads=%s\n' "$NSIGHT_WORKLOADS"
  printf 'runtime_device_overlap_supported=false\n'
  printf 'host_scheduling_overlap_available=true\n'
  cat "$WORK/summary.txt"
} >"$WORK/report.txt"

cat "$WORK/report.txt"
