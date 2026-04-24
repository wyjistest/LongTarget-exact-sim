#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-candidate-index-common-memory-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_operation_rollup_decision() {
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

write_partial_coverage_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.08,
    "terminal_path_start_index_write_share_of_candidate_index": 0.18,
    "terminal_path_candidate_bytes_written": 3200,
    "terminal_path_start_index_bytes_written": 6400,
    "terminal_path_start_index_store_insert_bytes": 3520,
    "terminal_path_start_index_store_clear_bytes": 1600,
    "terminal_path_start_index_store_overwrite_bytes": 1280,
    "terminal_path_start_index_store_unique_entry_count": 120,
    "terminal_path_start_index_store_unique_slot_count": 120,
    "terminal_path_start_index_store_same_entry_rewrite_count": 18,
    "terminal_path_start_index_store_same_cacheline_rewrite_count": 12,
    "terminal_path_start_index_write_count": 300,
    "terminal_path_state_update_share_of_candidate_index": 0.34,
    "production_state_update_share_of_candidate_index": 0.26
  }
}
EOF
}

write_sufficient_coverage_lifecycle_summary() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index": {
    "seconds": 10.0,
    "share_of_total_seconds": 0.50,
    "terminal_path_candidate_slot_write_share_of_candidate_index": 0.28,
    "terminal_path_start_index_write_share_of_candidate_index": 0.38,
    "terminal_path_candidate_bytes_written": 11200,
    "terminal_path_start_index_bytes_written": 15200,
    "terminal_path_start_index_store_insert_bytes": 3200,
    "terminal_path_start_index_store_clear_bytes": 4800,
    "terminal_path_start_index_store_overwrite_bytes": 7200,
    "terminal_path_start_index_store_unique_entry_count": 90,
    "terminal_path_start_index_store_unique_slot_count": 72,
    "terminal_path_start_index_store_same_entry_rewrite_count": 64,
    "terminal_path_start_index_store_same_cacheline_rewrite_count": 58,
    "terminal_path_start_index_write_count": 120,
    "terminal_path_state_update_share_of_candidate_index": 0.04,
    "production_state_update_share_of_candidate_index": 0.01
  }
}
EOF
}

assert_action() {
  local out_dir="$1"
  local expected="$2"
  local expected_selection_status="${3:-}"
  python3 - "$out_dir" "$expected" "$expected_selection_status" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "candidate_index_common_memory_behavior_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "candidate_index_common_memory_behavior_summary.json").read_text(encoding="utf-8"))
assert decision["recommended_next_action"] == sys.argv[2], decision
assert decision["runtime_prototype_allowed"] is False, decision
assert summary["recommended_next_action"] == sys.argv[2], summary
expected_selection_status = sys.argv[3]
if expected_selection_status:
    assert decision["selection_status"] == expected_selection_status, decision
    assert summary["selection_status"] == expected_selection_status, summary
PY
}

assert_inactive_selection() {
  local out_dir="$1"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "candidate_index_common_memory_behavior_summary.json").read_text(encoding="utf-8"))
assert summary["selection_status"] == "inactive", summary
assert summary["coverage_status"] == "partial", summary
assert summary["memory_coverage_scope"] == "terminal_write_paths_only", summary
PY
}

assert_partial_coverage() {
  local out_dir="$1"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "candidate_index_common_memory_behavior_summary.json").read_text(encoding="utf-8"))
assert summary["coverage_status"] == "partial", summary
assert summary["memory_coverage_scope"] == "terminal_write_paths_only", summary
assert summary["covered_share_of_candidate_index"] < 0.60, summary
assert "state_update_bytes" in summary["missing_major_components"], summary
PY
}

assert_layout_signal() {
  local out_dir="$1"
  python3 - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads((Path(sys.argv[1]) / "candidate_index_common_memory_behavior_summary.json").read_text(encoding="utf-8"))
assert summary["coverage_status"] == "sufficient", summary
assert summary["same_cacheline_rewrite_share"] >= 0.70, summary
assert summary["covered_share_of_candidate_index"] >= 0.60, summary
PY
}

LIFECYCLE_SUMMARY="$WORK/candidate_index_lifecycle_summary.json"
OPERATION_ROLLUP_DECISION="$WORK/candidate_index_operation_rollup_decision.json"
OUT_DIR="$WORK/out"

write_operation_rollup_decision "$OPERATION_ROLLUP_DECISION" "stop_candidate_index_structural_profiling"
write_partial_coverage_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"
assert_action "$OUT_DIR" "stop_candidate_index_structural_profiling" "inactive"
assert_inactive_selection "$OUT_DIR"

write_operation_rollup_decision "$OPERATION_ROLLUP_DECISION" "profile_candidate_index_common_memory_behavior"

write_partial_coverage_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"
assert_action "$OUT_DIR" "instrument_candidate_index_state_update_memory_counters" "active"
assert_partial_coverage "$OUT_DIR"

write_sufficient_coverage_lifecycle_summary "$LIFECYCLE_SUMMARY"
python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py \
  --candidate-index-lifecycle-summary "$LIFECYCLE_SUMMARY" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"
assert_action "$OUT_DIR" "profile_candidate_index_common_store_layout" "active"
assert_layout_signal "$OUT_DIR"

echo "check_summarize_sim_initial_host_merge_candidate_index_common_memory_behavior: PASS"
