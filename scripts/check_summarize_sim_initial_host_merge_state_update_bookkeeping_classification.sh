#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-state-update-bookkeeping-classify-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_summary() {
  local path="$1"
  local profile_mode="$2"
  local requested_mode="$3"
  local effective_mode="$4"
  local candidate_index_seconds="$5"
  local terminal_parent_seconds="$6"
  local state_update_parent_seconds="$7"
  local bookkeeping_seconds="$8"
  local heap_update_count="$9"
  local trace_count="${10}"
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "profile_mode_overhead_status": "ok",
  "trusted_span_timing": true,
  "trusted_span_source": "sampled",
  "runtime_prototype_allowed": false,
  "profile_mode": "${profile_mode}",
  "candidate_index": {
    "profile_mode": "${profile_mode}",
    "state_update_bookkeeping_mode_requested": "${requested_mode}",
    "state_update_bookkeeping_mode_effective": "${effective_mode}",
    "seconds": ${candidate_index_seconds},
    "terminal_path_parent_seconds": ${terminal_parent_seconds},
    "terminal_path_state_update_parent_seconds": ${state_update_parent_seconds},
    "terminal_path_state_update_trace_or_profile_bookkeeping_seconds": ${bookkeeping_seconds},
    "terminal_path_state_update_share_of_candidate_index": 0.07
  },
  "cases": [
    {
      "case_id": "case-1",
      "workload_id": "wl-1",
      "profile_mode": "${profile_mode}",
      "state_update_bookkeeping_mode_requested": "${requested_mode}",
      "state_update_bookkeeping_mode_effective": "${effective_mode}",
      "full_set_miss_count": 12,
      "candidate_index_lookup_count": 100,
      "candidate_index_insert_count": 7,
      "candidate_index_erase_count": 7,
      "terminal_path_event_count": 12,
      "terminal_path_candidate_slot_write_count": 12,
      "terminal_path_start_index_write_count": 12,
      "terminal_path_state_update_count": 12,
      "terminal_path_state_update_event_count": 12,
      "terminal_path_state_update_heap_build_count": 0,
      "terminal_path_state_update_heap_update_count": ${heap_update_count},
      "terminal_path_state_update_start_index_rebuild_count": 3,
      "terminal_path_state_update_trace_or_profile_bookkeeping_count": ${trace_count}
    }
  ]
}
EOF
}

assert_ready_decision() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "state_update_bookkeeping_classification_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "state_update_bookkeeping_classification_summary.json").read_text(encoding="utf-8"))

assert decision["current_branch"] == "terminal_path_state_update", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["state_update_bookkeeping_kind"] == "profiler_only_overhead", decision
assert decision["recommended_next_action"] == "reduce_or_cold_path_state_update_bookkeeping", decision
assert (
    summary["decision_context_status"]
    == "ready_but_requires_branch_rollup_context"
), summary
assert (
    decision["decision_context_status"]
    == "ready_but_requires_branch_rollup_context"
), decision
assert summary["authoritative_next_action_source"] == "branch_rollup_decision", summary
assert decision["authoritative_next_action_source"] == "branch_rollup_decision", decision
assert summary["decision_status"] == "ready", summary
assert summary["state_update_bookkeeping_mode_status"] == "matched", summary
assert summary["behavior_consistency_status"] == "matched", summary
assert summary["with_state_update_bookkeeping_mode_effective"] == "on", summary
assert summary["without_state_update_bookkeeping_mode_effective"] == "off", summary
assert float(summary["candidate_index_delta_explains_share"]) >= 0.80, summary
PY
}

assert_semantic_drift_not_ready() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "state_update_bookkeeping_classification_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "state_update_bookkeeping_classification_summary.json").read_text(encoding="utf-8"))

assert decision["runtime_prototype_allowed"] is False, decision
assert decision["state_update_bookkeeping_kind"] == "unknown", decision
assert decision["recommended_next_action"] == "inspect_no_state_update_bookkeeping_semantic_drift", decision
assert (
    summary["decision_context_status"]
    == "ready_but_requires_branch_rollup_context"
), summary
assert (
    decision["decision_context_status"]
    == "ready_but_requires_branch_rollup_context"
), decision
assert summary["authoritative_next_action_source"] == "branch_rollup_decision", summary
assert decision["authoritative_next_action_source"] == "branch_rollup_decision", decision
assert summary["decision_status"] == "not_ready", summary
assert summary["behavior_consistency_status"] == "mismatch", summary
PY
}

WITH_SUMMARY="$WORK/with.json"
WITHOUT_SUMMARY="$WORK/without.json"
OUT_DIR="$WORK/out"

write_summary \
  "$WITH_SUMMARY" \
  "lexical_first_half_sampled" \
  "auto" \
  "on" \
  "8.0" \
  "5.0" \
  "1.2" \
  "0.95" \
  "9" \
  "12"
write_summary \
  "$WITHOUT_SUMMARY" \
  "lexical_first_half_sampled_no_state_update_bookkeeping" \
  "off" \
  "off" \
  "7.05" \
  "4.25" \
  "0.25" \
  "0.0" \
  "9" \
  "0"

python3 ./scripts/summarize_sim_initial_host_merge_state_update_bookkeeping_classification.py \
  --with-state-update-bookkeeping-summary "$WITH_SUMMARY" \
  --without-state-update-bookkeeping-summary "$WITHOUT_SUMMARY" \
  --output-dir "$OUT_DIR"

assert_ready_decision "$OUT_DIR"

DRIFT_OUT="$WORK/out-drift"
write_summary \
  "$WITHOUT_SUMMARY" \
  "lexical_first_half_sampled_no_state_update_bookkeeping" \
  "off" \
  "off" \
  "7.05" \
  "4.25" \
  "0.25" \
  "0.0" \
  "8" \
  "1"

python3 ./scripts/summarize_sim_initial_host_merge_state_update_bookkeeping_classification.py \
  --with-state-update-bookkeeping-summary "$WITH_SUMMARY" \
  --without-state-update-bookkeeping-summary "$WITHOUT_SUMMARY" \
  --output-dir "$DRIFT_OUT"

assert_semantic_drift_not_ready "$DRIFT_OUT"

echo "check_summarize_sim_initial_host_merge_state_update_bookkeeping_classification: PASS"
