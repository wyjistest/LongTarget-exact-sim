#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-refresh-candidate-index-structural-phase-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_profile_mode_ab_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "profile_mode_overhead_status": "ok",
  "trusted_span_timing": true,
  "trusted_span_source": "sampled",
  "sampled_count_closure_status": "closed",
  "gap_before_a00_sampled_count_closure_status": "closed",
  "gap_before_a00_span_0_sampled_count_closure_status": "closed",
  "gap_before_a00_span_0_alt_sampled_count_closure_status": "closed",
  "gap_before_a00_span_0_alt_right_sampled_count_closure_status": "closed",
  "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status": "closed",
  "gap_before_a00_span_0_alt_right_dominance_status": "near_tie",
  "gap_before_a00_span_0_alt_right_repart_dominance_status": "near_tie",
  "gap_before_a00_span_0_alt_right_repartition_attempt_count": 2,
  "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count": 2,
  "gap_before_a00_span_0_alt_right_subtree_status": "distributed_overhead_no_stable_leaf",
  "terminal_first_half_span_a0_gap_before_a00_parent_seconds": 0.01233156,
  "terminal_first_half_span_a0_gap_before_a00_span_0_share": 0.6593545342195148,
  "gap_before_a00_span_0_alt_left_share": 0.3304310241364434,
  "gap_before_a00_span_0_alt_right_share": 0.6695689758635566,
  "recommended_next_action": "mark_gap_before_a00_span_0_alt_right_as_distributed_overhead",
  "runtime_prototype_allowed": false
}
EOF
}

write_terminal_telemetry_classification_decision() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "current_branch": "terminal_path_telemetry_overhead",
  "telemetry_branch_kind": "profiler_only_overhead",
  "recommended_next_action": "reduce_or_cold_path_profiler_telemetry",
  "runtime_prototype_allowed": false
}
EOF
}

write_state_update_bookkeeping_classification_decision() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "current_branch": "terminal_path_state_update",
  "state_update_bookkeeping_kind": "production_state_bookkeeping",
  "recommended_next_action": "mark_production_state_update_as_distributed_overhead",
  "runtime_prototype_allowed": false
}
EOF
}

write_leaf_stop_branch_rollup_decision() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "leaf_level_candidate_index_profiling_status": "stopped",
  "leaf_level_candidate_index_profiling_detail": "candidate_index_material_but_no_single_stable_leaf_found",
  "recommended_next_action": "profile_candidate_index_operation_rollup",
  "current_phase": "candidate_index_structural_profiling",
  "current_phase_status": "active",
  "current_focus": "operation_rollup",
  "runtime_prototype_allowed": false,
  "active_frontier": null,
  "stop_reason": "no_single_stable_leaf_found_under_current_profiler",
  "authoritative_sources": {
    "branch_rollup_decision": "branch_rollup_decision.json"
  }
}
EOF
}

write_memory_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_timer_closure_status": "closed",
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.0413664075,
    "terminal_path_start_index_write_share_of_candidate_index": 0.1200465962,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "closed",
    "terminal_path_start_index_store_unexplained_share": 0.0,
    "terminal_path_start_index_store_insert_share": 0.4992572803,
    "terminal_path_start_index_store_clear_share": 0.5007427197,
    "terminal_path_start_index_store_overwrite_share": 0.0,
    "terminal_path_start_index_store_case_weighted_dominant_child": "clear",
    "terminal_path_start_index_store_seconds_weighted_dominant_child": "clear",
    "terminal_path_start_index_store_event_weighted_dominant_child": "clear",
    "terminal_path_start_index_store_case_majority_share": 0.6,
    "terminal_path_start_index_store_child_margin_share": 0.0014854394,
    "terminal_path_start_index_store_dominance_status": "near_tie",
    "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": 0.0,
    "terminal_path_state_update_share_of_candidate_index": 0.24,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_heap_build_share": 0.10,
    "terminal_path_state_update_heap_update_share": 0.15,
    "terminal_path_state_update_start_index_rebuild_share": 0.15,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.60,
    "production_state_update_share_of_candidate_index": 0.18,
    "production_state_update_coverage_source": "event_level_sampled",
    "production_state_update_sampled_count_closure_status": "closed",
    "production_state_update_unexplained_share": 0.0,
    "production_state_update_dominance_status": "near_tie",
    "production_state_update_benchmark_counter_share": 0.60,
    "production_state_update_trace_replay_required_state_share": 0.40,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.1036628791,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.3294131298,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.1395116215,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.1899011759,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.3411725766,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 9.0,
    "terminal_path_candidate_bytes_written": 3200,
    "terminal_path_start_index_bytes_written": 6400,
    "terminal_path_start_index_store_unique_entry_count": 120,
    "terminal_path_start_index_store_same_entry_rewrite_count": 18,
    "terminal_path_start_index_store_same_cacheline_rewrite_count": 12,
    "terminal_path_start_index_write_count": 300
  }
}
EOF
}

write_control_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_timer_closure_status": "closed",
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.04,
    "terminal_path_start_index_write_share_of_candidate_index": 0.04,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.60,
    "terminal_path_start_index_write_entry_store_share": 0.40,
    "terminal_path_start_index_store_sampled_count_closure_status": "closed",
    "terminal_path_start_index_store_unexplained_share": 0.0,
    "terminal_path_start_index_store_insert_share": 0.34,
    "terminal_path_start_index_store_clear_share": 0.33,
    "terminal_path_start_index_store_overwrite_share": 0.33,
    "terminal_path_start_index_store_case_weighted_dominant_child": "insert",
    "terminal_path_start_index_store_seconds_weighted_dominant_child": "insert",
    "terminal_path_start_index_store_event_weighted_dominant_child": "insert",
    "terminal_path_start_index_store_case_majority_share": 0.34,
    "terminal_path_start_index_store_child_margin_share": 0.01,
    "terminal_path_start_index_store_dominance_status": "near_tie",
    "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": 0.0,
    "terminal_path_state_update_share_of_candidate_index": 0.04,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.60,
    "production_state_update_coverage_source": "event_level_sampled",
    "production_state_update_sampled_count_closure_status": "closed",
    "production_state_update_unexplained_share": 0.0,
    "production_state_update_dominance_status": "near_tie",
    "production_state_update_share_of_candidate_index": 0.03,
    "production_state_update_benchmark_counter_share": 0.50,
    "production_state_update_trace_replay_required_state_share": 0.50,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.42,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.35,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.30,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.27,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.08,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 9.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.42,
    "terminal_path_candidate_bytes_written": 1600,
    "terminal_path_start_index_bytes_written": 2400,
    "terminal_path_start_index_store_unique_entry_count": 90,
    "terminal_path_start_index_store_same_entry_rewrite_count": 10,
    "terminal_path_start_index_store_same_cacheline_rewrite_count": 4,
    "terminal_path_start_index_write_count": 120
  }
}
EOF
}

assert_memory_refresh() {
  local out_root="$1"
  python3 - "$out_root" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
op_decision = json.loads((root / "candidate_index_operation_rollup" / "candidate_index_operation_rollup_decision.json").read_text(encoding="utf-8"))
mem_decision = json.loads((root / "candidate_index_common_memory_behavior" / "candidate_index_common_memory_behavior_decision.json").read_text(encoding="utf-8"))
phase_decision = json.loads((root / "candidate_index_structural_phase" / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))
rollup_decision = json.loads((root / "branch_rollup" / "branch_rollup_decision.json").read_text(encoding="utf-8"))

assert op_decision["recommended_next_action"] == "profile_candidate_index_common_memory_behavior", op_decision
assert mem_decision["recommended_next_action"] == "instrument_candidate_index_state_update_memory_counters", mem_decision
assert phase_decision["current_focus"] == "common_memory_behavior", phase_decision
assert phase_decision["recommended_next_action"] == "instrument_candidate_index_state_update_memory_counters", phase_decision
assert rollup_decision["current_phase"] == "candidate_index_structural_profiling", rollup_decision
assert rollup_decision["current_phase_status"] == "active", rollup_decision
assert rollup_decision["current_focus"] == "common_memory_behavior", rollup_decision
assert rollup_decision["recommended_next_action"] == "instrument_candidate_index_state_update_memory_counters", rollup_decision
assert rollup_decision["runtime_prototype_allowed"] is False, rollup_decision
PY
}

assert_control_flow_refresh() {
  local out_root="$1"
  python3 - "$out_root" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
op_decision = json.loads((root / "candidate_index_operation_rollup" / "candidate_index_operation_rollup_decision.json").read_text(encoding="utf-8"))
mem_decision = json.loads((root / "candidate_index_common_memory_behavior" / "candidate_index_common_memory_behavior_decision.json").read_text(encoding="utf-8"))
phase_decision = json.loads((root / "candidate_index_structural_phase" / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))
rollup_decision = json.loads((root / "branch_rollup" / "branch_rollup_decision.json").read_text(encoding="utf-8"))

assert op_decision["recommended_next_action"] == "stop_candidate_index_structural_profiling", op_decision
assert op_decision["optional_next_action"] == "profile_candidate_index_common_control_flow_behavior", op_decision
assert mem_decision["selection_status"] == "inactive", mem_decision
assert mem_decision["recommended_next_action"] == "stop_candidate_index_structural_profiling", mem_decision
assert phase_decision["phase_status"] == "stopped", phase_decision
assert phase_decision["current_focus"] is None, phase_decision
assert phase_decision["optional_next_action"] == "profile_candidate_index_common_control_flow_behavior", phase_decision
assert rollup_decision["current_phase_status"] == "stopped", rollup_decision
assert rollup_decision["current_focus"] is None, rollup_decision
assert rollup_decision["recommended_next_action"] == "stop_candidate_index_structural_profiling", rollup_decision
assert rollup_decision["optional_next_action"] == "profile_candidate_index_common_control_flow_behavior", rollup_decision
assert rollup_decision["runtime_prototype_allowed"] is False, rollup_decision
PY
}

AB_SUMMARY="$WORK/profile_mode_ab_summary.json"
LIFECYCLE_SUMMARY="$WORK/candidate_index_lifecycle_summary.json"
TERMINAL_TELEMETRY_DECISION="$WORK/terminal_telemetry_classification_decision.json"
STATE_UPDATE_BOOKKEEPING_DECISION="$WORK/state_update_bookkeeping_classification_decision.json"
LEAF_STOP_BRANCH_ROLLUP_DECISION="$WORK/leaf_stop_branch_rollup_decision.json"
OUT_ROOT="$WORK/out"

write_profile_mode_ab_summary "$AB_SUMMARY"
write_terminal_telemetry_classification_decision "$TERMINAL_TELEMETRY_DECISION"
write_state_update_bookkeeping_classification_decision "$STATE_UPDATE_BOOKKEEPING_DECISION"
write_leaf_stop_branch_rollup_decision "$LEAF_STOP_BRANCH_ROLLUP_DECISION"

write_memory_lifecycle_summary "$LIFECYCLE_SUMMARY"
./scripts/refresh_sim_initial_host_merge_candidate_index_structural_phase.sh \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_DECISION" \
  --branch-rollup-decision "$LEAF_STOP_BRANCH_ROLLUP_DECISION" \
  --output-root "$OUT_ROOT"
assert_memory_refresh "$OUT_ROOT"

write_control_lifecycle_summary "$LIFECYCLE_SUMMARY"
./scripts/refresh_sim_initial_host_merge_candidate_index_structural_phase.sh \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_DECISION" \
  --branch-rollup-decision "$LEAF_STOP_BRANCH_ROLLUP_DECISION" \
  --output-root "$OUT_ROOT"
assert_control_flow_refresh "$OUT_ROOT"

echo "check_refresh_sim_initial_host_merge_candidate_index_structural_phase: PASS"
