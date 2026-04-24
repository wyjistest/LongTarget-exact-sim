#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-candidate-index-structural-phase-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_branch_rollup_decision() {
  local path="$1"
  local recommended_next_action="$2"
  local current_phase="${3:-candidate_index_structural_profiling}"
  local current_phase_status="${4:-active}"
  local current_focus="${5:-operation_rollup}"
  local leaf_status="${6:-stopped}"
  local current_focus_json="null"
  if [[ -n "${current_focus}" ]]; then
    current_focus_json="\"${current_focus}\""
  fi
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "leaf_level_candidate_index_profiling_status": "${leaf_status}",
  "recommended_next_action": "${recommended_next_action}",
  "current_phase": "${current_phase}",
  "current_phase_status": "${current_phase_status}",
  "current_focus": ${current_focus_json},
  "runtime_prototype_allowed": false,
  "active_frontier": null,
  "stop_reason": "no_single_stable_leaf_found_under_current_profiler",
  "authoritative_sources": {
    "branch_rollup_decision": "branch_rollup_decision.json"
  }
}
EOF
}

write_operation_rollup_decision() {
  local path="$1"
  local recommended_next_action="$2"
  local optional_next_action="${3:-}"
  local optional_json="null"
  if [[ -n "${optional_next_action}" ]]; then
    optional_json="\"${optional_next_action}\""
  fi
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "recommended_next_action": "${recommended_next_action}",
  "optional_next_action": ${optional_json},
  "runtime_prototype_allowed": false
}
EOF
}

write_common_memory_decision() {
  local path="$1"
  local recommended_next_action="$2"
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "recommended_next_action": "${recommended_next_action}",
  "runtime_prototype_allowed": false
}
EOF
}

assert_operation_focus() {
  local out_dir="$1"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary = json.loads((out_dir / "candidate_index_structural_phase_summary.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))

assert summary["phase"] == "candidate_index_structural_profiling", summary
assert summary["phase_status"] == "active", summary
assert summary["current_focus"] == "operation_rollup", summary
assert summary["recommended_next_action"] == "profile_candidate_index_operation_rollup", summary
assert summary["runtime_prototype_allowed"] is False, summary
assert summary["authoritative_next_action_source"] == "branch_rollup_decision", summary
assert decision["phase"] == "candidate_index_structural_profiling", decision
assert decision["phase_status"] == "active", decision
assert decision["current_focus"] == "operation_rollup", decision
assert decision["recommended_next_action"] == "profile_candidate_index_operation_rollup", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY
}

assert_memory_focus() {
  local out_dir="$1"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))
assert decision["phase_status"] == "active", decision
assert decision["current_focus"] == "common_memory_behavior", decision
assert decision["recommended_next_action"] == "profile_candidate_index_common_memory_behavior", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY
}

assert_stopped() {
  local out_dir="$1"
  local expected_optional="${2:-}"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))
assert decision["phase_status"] == "stopped", decision
assert decision["current_focus"] is None, decision
assert decision["recommended_next_action"] == "stop_candidate_index_structural_profiling", decision
assert decision["stop_reason"] == "no_stable_structural_signal", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY
  python3 - "$out_dir" "$expected_optional" <<'PY'
import json
import sys
from pathlib import Path

decision = json.loads((Path(sys.argv[1]) / "candidate_index_structural_phase_decision.json").read_text(encoding="utf-8"))
expected_optional = sys.argv[2] if sys.argv[2] else None
assert decision.get("optional_next_action") == expected_optional, decision
PY
}

BRANCH_ROLLUP_DECISION="$WORK/branch_rollup_decision.json"
OPERATION_ROLLUP_DECISION="$WORK/candidate_index_operation_rollup_decision.json"
COMMON_MEMORY_DECISION="$WORK/candidate_index_common_memory_behavior_decision.json"
OUT_DIR="$WORK/out"

write_branch_rollup_decision "$BRANCH_ROLLUP_DECISION" "profile_candidate_index_operation_rollup"

python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py \
  --branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

assert_operation_focus "$OUT_DIR"

write_operation_rollup_decision \
  "$OPERATION_ROLLUP_DECISION" \
  "stop_candidate_index_structural_profiling" \
  "profile_candidate_index_common_control_flow_behavior"

python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py \
  --branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

assert_stopped "$OUT_DIR" "profile_candidate_index_common_control_flow_behavior"

write_operation_rollup_decision "$OPERATION_ROLLUP_DECISION" "profile_candidate_index_common_memory_behavior"

python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py \
  --branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

assert_memory_focus "$OUT_DIR"

write_common_memory_decision "$COMMON_MEMORY_DECISION" "stop_candidate_index_structural_profiling"

python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py \
  --branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --candidate-index-common-memory-behavior-decision "$COMMON_MEMORY_DECISION" \
  --output-dir "$OUT_DIR"

assert_stopped "$OUT_DIR"

echo "check_summarize_sim_initial_host_merge_candidate_index_structural_phase: PASS"
