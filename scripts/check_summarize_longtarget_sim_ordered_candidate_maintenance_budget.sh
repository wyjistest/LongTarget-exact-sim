#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-ordered-maintenance-budget-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

OUT_DIR="$WORK/out"
ROLLUP_DECISION="$WORK/sim_pipeline_budget_rollup_decision.json"

write_pipeline_budget() {
  local dir="$1"
  local workload_id="$2"
  local source_input_budget="$3"
  local total_seconds="$4"
  local sim_seconds="$5"
  local host_seconds="$6"
  local host_share="$7"
  mkdir -p "$dir"
  cat >"$dir/sim_pipeline_budget.json" <<EOF
{
  "decision_status": "ready",
  "phase": "device_resident_sim_pipeline_budget",
  "source_input_budget": "${source_input_budget}",
  "total_seconds": ${total_seconds},
  "sim_seconds": ${sim_seconds},
  "subcomponents": [
    {
      "subcomponent": "host_cpu_merge",
      "seconds": ${host_seconds},
      "share_of_sim_seconds": ${host_share},
      "share_of_total_seconds": 0.420000,
      "evidence_status": "provided"
    }
  ]
}
EOF
  cat >"$dir/sim_pipeline_budget_decision.json" <<EOF
{
  "decision_status": "ready",
  "phase": "device_resident_sim_pipeline_budget",
  "workload_id": "${workload_id}",
  "selection_status": "selected",
  "selected_subcomponent": "host_cpu_merge",
  "recommended_next_action": "profile_device_side_ordered_candidate_maintenance",
  "runtime_prototype_allowed": false
}
EOF
}

write_rollup() {
  local budget_a="$1"
  local budget_b="$2"
  cat >"$ROLLUP_DECISION" <<EOF
{
  "decision_status": "ready",
  "phase": "device_resident_sim_pipeline_budget_rollup",
  "selection_status": "stable_selected",
  "selected_subcomponent": "host_cpu_merge",
  "recommended_next_action": "profile_device_side_ordered_candidate_maintenance",
  "runtime_prototype_allowed": false,
  "workload_count": 2,
  "workload_decisions": {
    "sample": {
      "workload_id": "sample",
      "workload_class": "sample",
      "selection_status": "selected",
      "selected_subcomponent": "host_cpu_merge",
      "recommended_next_action": "profile_device_side_ordered_candidate_maintenance",
      "runtime_prototype_allowed": false,
      "source_sim_pipeline_budget": "${budget_a}",
      "source_sim_pipeline_budget_decision": "${budget_a%/*}/sim_pipeline_budget_decision.json"
    },
    "heavy": {
      "workload_id": "heavy",
      "workload_class": "5case_heavy",
      "selection_status": "selected",
      "selected_subcomponent": "host_cpu_merge",
      "recommended_next_action": "profile_device_side_ordered_candidate_maintenance",
      "runtime_prototype_allowed": false,
      "source_sim_pipeline_budget": "${budget_b}",
      "source_sim_pipeline_budget_decision": "${budget_b%/*}/sim_pipeline_budget_decision.json"
    }
  }
}
EOF
}

write_projection_missing() {
  local path="$1"
  cat >"$path" <<'EOF'
{
  "projected_total_seconds": 100.0,
  "projected_sim_seconds": 80.0,
  "projected_sim_initial_summary_count": 1000
}
EOF
}

write_projection_complete() {
  local path="$1"
  local event_count="$2"
  local segment_count="$3"
  local serial_share="$4"
  local parallel_share="$5"
  local avoidable_seconds="$6"
  cat >"$path" <<EOF
{
  "projected_total_seconds": 100.0,
  "projected_sim_seconds": 80.0,
  "projected_sim_initial_summary_count": ${event_count},
  "projected_sim_ordered_maintenance_candidate_event_count": ${event_count},
  "projected_sim_ordered_maintenance_ordered_segment_count": ${segment_count},
  "projected_sim_ordered_maintenance_parallel_segment_count": ${segment_count},
  "projected_sim_ordered_maintenance_mean_segment_length": 16.0,
  "projected_sim_ordered_maintenance_p90_segment_length": 32.0,
  "projected_sim_ordered_maintenance_serial_dependency_share": ${serial_share},
  "projected_sim_ordered_maintenance_parallelizable_event_share": ${parallel_share},
  "projected_sim_ordered_maintenance_estimated_d2h_bytes_avoided": 1048576,
  "projected_sim_ordered_maintenance_estimated_host_rebuild_seconds_avoided": 8.0,
  "projected_sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable": ${avoidable_seconds}
}
EOF
}

MISSING_A="$WORK/missing_a/projected_report.json"
MISSING_B="$WORK/missing_b/projected_report.json"
mkdir -p "$(dirname "$MISSING_A")" "$(dirname "$MISSING_B")"
write_projection_missing "$MISSING_A"
write_projection_missing "$MISSING_B"
write_pipeline_budget "$WORK/missing_a/sim_pipeline_budget" "sample" "$MISSING_A" 100.0 80.0 50.0 0.625
write_pipeline_budget "$WORK/missing_b/sim_pipeline_budget" "heavy" "$MISSING_B" 110.0 90.0 60.0 0.667
write_rollup \
  "$WORK/missing_a/sim_pipeline_budget/sim_pipeline_budget.json" \
  "$WORK/missing_b/sim_pipeline_budget/sim_pipeline_budget.json"

python3 scripts/summarize_longtarget_sim_ordered_candidate_maintenance_budget.py \
  --sim-pipeline-budget-rollup-decision "$ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/ordered_candidate_maintenance_budget_decision.json" "$OUT_DIR/ordered_candidate_maintenance_budget_cases.tsv"
import csv
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["phase"] == "device_side_ordered_candidate_maintenance_budget", decision
assert decision["telemetry_status"] == "insufficient_telemetry", decision
assert decision["device_side_ordered_candidate_maintenance_feasibility"] == "insufficient_telemetry", decision
assert decision["recommended_next_action"] == "collect_ordered_candidate_maintenance_telemetry", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["missing_required_field_count"] > 0, decision

rows = list(csv.DictReader(Path(sys.argv[2]).open(encoding="utf-8"), delimiter="\t"))
assert len(rows) == 2, rows
assert rows[0]["workload_id"] == "sample", rows
assert int(rows[0]["missing_required_field_count"]) > 0, rows
PY

COMPLETE_A="$WORK/complete_a/projected_report.json"
COMPLETE_B="$WORK/complete_b/projected_report.json"
mkdir -p "$(dirname "$COMPLETE_A")" "$(dirname "$COMPLETE_B")"
write_projection_complete "$COMPLETE_A" 12000 800 0.20 0.76 38.0
write_projection_complete "$COMPLETE_B" 18000 1200 0.18 0.78 42.0
write_pipeline_budget "$WORK/complete_a/sim_pipeline_budget" "sample" "$COMPLETE_A" 100.0 80.0 50.0 0.625
write_pipeline_budget "$WORK/complete_b/sim_pipeline_budget" "heavy" "$COMPLETE_B" 120.0 90.0 60.0 0.667
write_rollup \
  "$WORK/complete_a/sim_pipeline_budget/sim_pipeline_budget.json" \
  "$WORK/complete_b/sim_pipeline_budget/sim_pipeline_budget.json"

python3 scripts/summarize_longtarget_sim_ordered_candidate_maintenance_budget.py \
  --sim-pipeline-budget-rollup-decision "$ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/ordered_candidate_maintenance_budget_decision.json" "$OUT_DIR/ordered_candidate_maintenance_budget_summary.json"
import json
import math
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert decision["telemetry_status"] == "closed", decision
assert decision["device_side_ordered_candidate_maintenance_feasibility"] == "strong", decision
assert decision["recommended_next_action"] == "design_device_side_ordered_candidate_maintenance_shadow", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert math.isclose(summary["aggregate"]["parallelizable_event_share"], 0.772, rel_tol=0, abs_tol=1e-12), summary
assert summary["aggregate"]["parallel_segment_count"] == 2000.0, summary
assert summary["aggregate"]["estimated_cpu_merge_seconds_avoidable"] == 80.0, summary
PY

test -s "$OUT_DIR/ordered_candidate_maintenance_budget.md"

echo "check_summarize_longtarget_sim_ordered_candidate_maintenance_budget: PASS"
