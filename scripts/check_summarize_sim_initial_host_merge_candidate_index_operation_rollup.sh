#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-candidate-index-operation-rollup-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_profile_mode_ab_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "profile_mode_overhead_status": "ok",
  "trusted_span_timing": true,
  "trusted_span_source": "sampled"
}
EOF
}

write_memory_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "recommended_next_action": "stop_leaf_level_candidate_index_profiling",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_timer_closure_status": "closed",
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.18,
    "terminal_path_start_index_write_share_of_candidate_index": 0.28,
    "terminal_path_start_index_write_probe_or_locate_share": 0.10,
    "terminal_path_start_index_write_entry_store_share": 0.90,
    "terminal_path_start_index_store_insert_share": 0.55,
    "terminal_path_start_index_store_clear_share": 0.25,
    "terminal_path_start_index_store_overwrite_share": 0.20,
    "terminal_path_state_update_share_of_candidate_index": 0.24,
    "terminal_path_state_update_heap_build_share": 0.10,
    "terminal_path_state_update_heap_update_share": 0.15,
    "terminal_path_state_update_start_index_rebuild_share": 0.15,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.60,
    "production_state_update_share_of_candidate_index": 0.18,
    "production_state_update_benchmark_counter_share": 0.60,
    "production_state_update_trace_replay_required_state_share": 0.40,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.08,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.50,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.20,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.20,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.10,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.05
  }
}
EOF
}

write_control_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "recommended_next_action": "stop_leaf_level_candidate_index_profiling",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_timer_closure_status": "closed",
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.04,
    "terminal_path_start_index_write_share_of_candidate_index": 0.06,
    "terminal_path_start_index_write_probe_or_locate_share": 0.60,
    "terminal_path_start_index_write_entry_store_share": 0.40,
    "terminal_path_start_index_store_insert_share": 0.34,
    "terminal_path_start_index_store_clear_share": 0.33,
    "terminal_path_start_index_store_overwrite_share": 0.33,
    "terminal_path_state_update_share_of_candidate_index": 0.06,
    "terminal_path_state_update_heap_build_share": 0.20,
    "terminal_path_state_update_heap_update_share": 0.20,
    "terminal_path_state_update_start_index_rebuild_share": 0.10,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.50,
    "production_state_update_share_of_candidate_index": 0.03,
    "production_state_update_benchmark_counter_share": 0.50,
    "production_state_update_trace_replay_required_state_share": 0.50,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.42,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.50,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.28,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.18,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.04,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.02
  }
}
EOF
}

write_near_tie_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "recommended_next_action": "stop_leaf_level_candidate_index_profiling",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_timer_closure_status": "closed",
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.10,
    "terminal_path_start_index_write_share_of_candidate_index": 0.12,
    "terminal_path_start_index_write_probe_or_locate_share": 0.15,
    "terminal_path_start_index_write_entry_store_share": 0.85,
    "terminal_path_start_index_store_insert_share": 0.34,
    "terminal_path_start_index_store_clear_share": 0.33,
    "terminal_path_start_index_store_overwrite_share": 0.33,
    "terminal_path_state_update_share_of_candidate_index": 0.17,
    "terminal_path_state_update_heap_build_share": 0.10,
    "terminal_path_state_update_heap_update_share": 0.10,
    "terminal_path_state_update_start_index_rebuild_share": 0.10,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.70,
    "production_state_update_share_of_candidate_index": 0.10,
    "production_state_update_benchmark_counter_share": 0.50,
    "production_state_update_trace_replay_required_state_share": 0.50,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.21,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.45,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.30,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.20,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.05,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.03
  }
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

assert_action() {
  local out_dir="$1"
  local expected="$2"
  local expected_optional="${3:-}"
  python3 - "$out_dir" "$expected" "$expected_optional" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "candidate_index_operation_rollup_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "candidate_index_operation_rollup.json").read_text(encoding="utf-8"))
assert decision["recommended_next_action"] == sys.argv[2], decision
assert decision["runtime_prototype_allowed"] is False, decision
assert summary["recommended_next_action"] == sys.argv[2], summary
expected_optional = sys.argv[3]
expected_optional = expected_optional if expected_optional else None
assert decision.get("optional_next_action") == expected_optional, decision
assert summary.get("optional_next_action") == expected_optional, summary
PY
}

assert_row() {
  local out_dir="$1"
  local family="$2"
  python3 - "$out_dir" "$family" <<'PY'
import csv
import sys
from pathlib import Path

rows_path = Path(sys.argv[1]) / "candidate_index_operation_rollup.tsv"
with rows_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
for row in rows:
    if row["operation_family"] == sys.argv[2]:
        break
else:
    raise SystemExit(f"missing row for {sys.argv[2]}")
PY
}

AB_SUMMARY="$WORK/profile_mode_ab_summary.json"
LIFECYCLE_SUMMARY="$WORK/candidate_index_lifecycle_summary.json"
TERMINAL_TELEMETRY_DECISION="$WORK/terminal_telemetry_classification_decision.json"
OUT_DIR="$WORK/out"

write_profile_mode_ab_summary "$AB_SUMMARY"
write_terminal_telemetry_classification_decision "$TERMINAL_TELEMETRY_DECISION"

write_memory_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_DECISION" \
  --output-dir "$OUT_DIR"
assert_action "$OUT_DIR" "profile_candidate_index_common_memory_behavior"
assert_row "$OUT_DIR" "candidate_slot_overwrite"
assert_row "$OUT_DIR" "benchmark_counter"
assert_row "$OUT_DIR" "trace_replay_required_state"

write_control_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_DECISION" \
  --output-dir "$OUT_DIR"
assert_action \
  "$OUT_DIR" \
  "stop_candidate_index_structural_profiling" \
  "profile_candidate_index_common_control_flow_behavior"
assert_row "$OUT_DIR" "scan"
assert_row "$OUT_DIR" "compare"
assert_row "$OUT_DIR" "branch_or_guard"
python3 - <<'PY' "$OUT_DIR"
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "candidate_index_operation_rollup.json").read_text(encoding="utf-8"))
assert summary["dominant_operation_group"] == "control_flow", summary
assert summary["dominance_status"] == "stable", summary
PY

write_near_tie_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_DECISION" \
  --output-dir "$OUT_DIR"
assert_action "$OUT_DIR" "stop_candidate_index_structural_profiling"

echo "check_summarize_sim_initial_host_merge_candidate_index_operation_rollup: PASS"
