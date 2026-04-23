#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-profile-branch-rollup-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_ab_summary() {
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

write_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "run_profile_mode_ab",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.12004659617132386,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "unknown",
    "terminal_path_state_update_share_of_candidate_index": 0.0400000000,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.08247717076126315,
    "terminal_timer_closure_status": "closed"
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

write_state_update_bookkeeping_classification_decision() {
  local path="$1"
  local recommended_next_action="$2"
  local branch_kind="${3:-profiler_only_overhead}"
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "current_branch": "terminal_path_state_update",
  "state_update_bookkeeping_kind": "${branch_kind}",
  "recommended_next_action": "${recommended_next_action}",
  "runtime_prototype_allowed": false
}
EOF
}

assert_rollup_decision() {
  local output_dir="$1"
  local expected_exhausted="$2"
  local expected_next="$3"
  local expected_branch_decision="$4"
  local expected_action="$5"
  python3 - "$output_dir" "$expected_exhausted" "$expected_next" "$expected_branch_decision" "$expected_action" <<'PY'
import json
import sys
from pathlib import Path

decision = json.loads((Path(sys.argv[1]) / "branch_rollup_decision.json").read_text(encoding="utf-8"))
summary = json.loads((Path(sys.argv[1]) / "branch_rollup.json").read_text(encoding="utf-8"))
assert decision["current_exhausted_subtree"] == sys.argv[2], decision
assert decision["next_candidate_branch"] == sys.argv[3], decision
expected_branch_decision = None if sys.argv[4] == "none" else sys.argv[4]
assert decision["next_candidate_branch_decision"] == expected_branch_decision, decision
assert decision["recommended_next_action"] == sys.argv[5], decision
assert decision["runtime_prototype_allowed"] is False, decision
assert summary["current_exhausted_subtree"] == sys.argv[2], summary
assert summary["next_candidate_branch"] == sys.argv[3], summary
assert summary["next_candidate_branch_decision"] == expected_branch_decision, summary
assert summary["recommended_next_action"] == sys.argv[5], summary
assert summary["runtime_prototype_allowed"] is False, summary
PY
}

assert_rollup_row() {
  local output_dir="$1"
  local path_name="$2"
  local expected_status="$3"
  local expected_kind="${4:-}"
  local expected_actionability="${5:-}"
  python3 - "$output_dir" "$path_name" "$expected_status" <<'PY'
import csv
import sys
from pathlib import Path

rows_path = Path(sys.argv[1]) / "branch_rollup.tsv"
expected_kind = sys.argv[4] if len(sys.argv) > 4 else ""
expected_actionability = sys.argv[5] if len(sys.argv) > 5 else ""
with rows_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
for row in rows:
    if row["path"] == sys.argv[2]:
        assert row["subtree_status"] == sys.argv[3], row
        if expected_kind:
            assert row["branch_kind"] == expected_kind, row
        if expected_actionability:
            assert row["branch_actionability"] == expected_actionability, row
        break
else:
    raise SystemExit(f"missing row for {sys.argv[2]}")
PY
}

AB_SUMMARY="$WORK/profile_mode_ab_summary.json"
LIFECYCLE_SUMMARY="$WORK/candidate_index_lifecycle_summary.json"
TERMINAL_TELEMETRY_CLASSIFICATION_DECISION="$WORK/terminal_telemetry_classification_decision.json"
STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION="$WORK/state_update_bookkeeping_classification_decision.json"
OUT_DIR="$WORK/out"

write_ab_summary "$AB_SUMMARY"
write_lifecycle_summary "$LIFECYCLE_SUMMARY"
write_terminal_telemetry_classification_decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION"

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "terminal_path_start_index_write" \
  "profile_start_index_store_path" \
  "profile_start_index_store_path"
assert_rollup_row \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "distributed_overhead_no_stable_leaf" \
  "exhausted" \
  "exhausted"
assert_rollup_row \
  "$OUT_DIR" \
  "terminal_path_telemetry_overhead" \
  "not_profiled" \
  "profiler_only_overhead" \
  "reduce_profiler_overhead_first"
assert_rollup_row \
  "$OUT_DIR" \
  "terminal_path_start_index_write" \
  "not_profiled" \
  "runtime_candidate" \
  "actionable"

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "run_profile_mode_ab",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.12004659617132386,
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
    "terminal_path_state_update_share_of_candidate_index": 0.0400000000,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.08247717076126315,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "lookup_miss_candidate_set_full_probe" \
  "none" \
  "profile_lookup_miss_candidate_set_full_probe"
assert_rollup_row \
  "$OUT_DIR" \
  "terminal_path_start_index_write" \
  "distributed_overhead_no_stable_leaf" \
  "distributed_store_overhead" \
  "exhausted"
python3 - <<'PY' "$OUT_DIR/branch_rollup_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["current_exhausted_subtrees"] == [
    "gap_before_a00_span_0_alt_right",
    "terminal_path_start_index_write",
], decision
PY

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "profile_candidate_set_full_scan_path",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.024,
    "terminal_path_state_update_share_of_candidate_index": 0.0400000000,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.08247717076126315,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.62,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.15,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.13,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.10,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.58,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.05,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 64.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "lookup_miss_candidate_set_full_probe" \
  "profile_candidate_set_full_scan_path" \
  "profile_candidate_set_full_scan_path"

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": null,
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.0504221335,
    "terminal_path_start_index_write_share_of_candidate_index": 0.12004659617132386,
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
    "terminal_path_state_update_share_of_candidate_index": 0.0623433403,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.10366287911752718,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.3294131298,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.1395116215,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.1899011759,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.3411725766,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 9.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "terminal_path_state_update" \
  "none" \
  "profile_terminal_path_state_update"

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "profile_heap_update_path",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.0400000000,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "unknown",
    "terminal_path_state_update_share_of_candidate_index": 0.0700000000,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_heap_build_share": 0.10,
    "terminal_path_state_update_heap_update_share": 0.62,
    "terminal_path_state_update_start_index_rebuild_share": 0.18,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.10,
    "terminal_path_state_update_dominant_child": "heap_update",
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.0500000000,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.20,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.20,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.20,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.20,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 8.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "terminal_path_state_update" \
  "profile_heap_update_path" \
  "profile_heap_update_path"

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "classify_terminal_path_state_update_bookkeeping",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.0400000000,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "unknown",
    "terminal_path_state_update_share_of_candidate_index": 0.0700000000,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_heap_build_share": 0.0,
    "terminal_path_state_update_heap_update_share": 0.1147,
    "terminal_path_state_update_start_index_rebuild_share": 0.0100,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.8753,
    "terminal_path_state_update_dominant_child": "trace_or_profile_bookkeeping",
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.0500000000,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.20,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.20,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.20,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.20,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 8.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

write_state_update_bookkeeping_classification_decision \
  "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  "profile_production_state_update_bookkeeping_path" \
  "production_state_bookkeeping"

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "terminal_path_state_update" \
  "profile_production_state_update_bookkeeping_path" \
  "profile_production_state_update_bookkeeping_path"
python3 - <<'PY' "$OUT_DIR/branch_rollup_decision.json" "$AB_SUMMARY" "$LIFECYCLE_SUMMARY" "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["authoritative_sources"] == {
    "profile_mode_ab_summary": sys.argv[2],
    "sampled_lifecycle_summary": sys.argv[3],
    "terminal_telemetry_classification_decision": sys.argv[4],
    "state_update_bookkeeping_classification_decision": sys.argv[5],
}, decision
PY

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": null,
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.0400000000,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "unknown",
    "terminal_path_state_update_share_of_candidate_index": 0.0700000000,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_heap_build_share": 0.0,
    "terminal_path_state_update_heap_update_share": 0.1147,
    "terminal_path_state_update_start_index_rebuild_share": 0.0100,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.8753,
    "terminal_path_state_update_dominant_child": "trace_or_profile_bookkeeping",
    "production_state_update_sampled_count_closure_status": "closed",
    "production_state_update_coverage_source": "event_level_sampled",
    "production_state_update_unexplained_share": 0.0,
    "production_state_update_benchmark_counter_share": 0.4993,
    "production_state_update_trace_replay_required_state_share": 0.5007,
    "production_state_update_dominant_child": "trace_replay_required_state",
    "production_state_update_case_weighted_dominant_child": "trace_replay_required_state",
    "production_state_update_seconds_weighted_dominant_child": "trace_replay_required_state",
    "production_state_update_event_weighted_dominant_child": "trace_replay_required_state",
    "production_state_update_child_margin_share": 0.0014,
    "production_state_update_dominance_status": "near_tie",
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.0200000000,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/branch_rollup_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["current_exhausted_subtree"] == "gap_before_a00_span_0_alt_right", decision
assert "terminal_path_state_update" in decision["current_exhausted_subtrees"], decision
assert decision["next_candidate_branch"] is None, decision
assert decision["next_candidate_branch_decision"] is None, decision
assert (
    decision["recommended_next_action"]
    == "no_single_stable_leaf_found_under_current_profiler"
), decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": "profile_trace_replay_required_state_update_path",
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.0400000000,
    "terminal_path_start_index_write_sampled_count_closure_status": "closed",
    "terminal_path_start_index_write_unexplained_share": 0.0,
    "terminal_path_start_index_write_probe_or_locate_share": 0.0,
    "terminal_path_start_index_write_entry_store_share": 1.0,
    "terminal_path_start_index_store_sampled_count_closure_status": "unknown",
    "terminal_path_state_update_share_of_candidate_index": 0.0700000000,
    "terminal_path_state_update_sampled_count_closure_status": "closed",
    "terminal_path_state_update_unexplained_share": 0.0,
    "terminal_path_state_update_heap_build_share": 0.0,
    "terminal_path_state_update_heap_update_share": 0.1147,
    "terminal_path_state_update_start_index_rebuild_share": 0.0100,
    "terminal_path_state_update_trace_or_profile_bookkeeping_share": 0.8753,
    "terminal_path_state_update_dominant_child": "trace_or_profile_bookkeeping",
    "production_state_update_sampled_count_closure_status": "closed",
    "production_state_update_unexplained_share": 0.0,
    "production_state_update_benchmark_counter_share": 0.15,
    "production_state_update_trace_replay_required_state_share": 0.72,
    "production_state_update_dominant_child": "trace_replay_required_state",
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.0500000000,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.20,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.20,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.20,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.20,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 8.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "terminal_path_state_update" \
  "profile_trace_replay_required_state_update_path" \
  "profile_trace_replay_required_state_update_path"

cat >"$LIFECYCLE_SUMMARY" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "terminal_timer_closure_status": "closed",
  "recommended_next_action": null,
  "candidate_index": {
    "seconds": 6.9319,
    "share_of_total_seconds": 0.6363993021424829,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.041366407478469105,
    "terminal_path_start_index_write_share_of_candidate_index": 0.12004659617132386,
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
    "terminal_path_state_update_share_of_candidate_index": 0.0400000000,
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.0,
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index": 0.10366287911752718,
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": "closed",
    "lookup_miss_candidate_set_full_probe_unexplained_share": 0.0,
    "lookup_miss_candidate_set_full_probe_scan_share": 0.3294131298,
    "lookup_miss_candidate_set_full_probe_compare_share": 0.1395116215,
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share": 0.1899011759,
    "lookup_miss_candidate_set_full_probe_bookkeeping_share": 0.3411725766,
    "lookup_miss_candidate_set_full_probe_full_scan_share": 0.0,
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": 0.0,
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90": 9.0,
    "terminal_timer_closure_status": "closed"
  }
}
EOF

python3 ./scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --output-dir "$OUT_DIR"

assert_rollup_decision \
  "$OUT_DIR" \
  "gap_before_a00_span_0_alt_right" \
  "lookup_miss_candidate_set_full_probe" \
  "no_single_stable_leaf_found_under_current_profiler" \
  "stop_leaf_level_candidate_index_profiling"
python3 - <<'PY' "$OUT_DIR/branch_rollup_decision.json" "$AB_SUMMARY" "$LIFECYCLE_SUMMARY" "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["optional_next_action"] == "profile_candidate_index_common_memory_behavior", decision
assert decision["leaf_level_candidate_index_profiling_status"] == "stopped", decision
assert (
    decision["leaf_level_candidate_index_profiling_detail"]
    == "candidate_index_material_but_no_single_stable_leaf_found"
), decision
assert decision["active_frontier"] is None, decision
assert (
    decision["stop_reason"]
    == "no_single_stable_leaf_found_under_current_profiler"
), decision
assert decision["exhausted_or_non_actionable_branches"] == [
    "gap_before_a00_span_0_alt_right",
    "terminal_path_start_index_write",
    "terminal_path_telemetry_overhead",
    "lookup_miss_candidate_set_full_probe",
], decision
assert decision["authoritative_sources"] == {
    "profile_mode_ab_summary": sys.argv[2],
    "sampled_lifecycle_summary": sys.argv[3],
    "terminal_telemetry_classification_decision": sys.argv[4],
}, decision
PY

echo "check_summarize_sim_initial_host_merge_profile_branch_rollup: PASS"
