#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-sim-pipeline-rollup-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

OUT_DIR="$WORK/out"
CASE_A="$WORK/case_a_decision.json"
CASE_B="$WORK/case_b_decision.json"

write_decision() {
  local path="$1"
  local workload_id="$2"
  local selection_status="$3"
  local selected_subcomponent="$4"
  local recommended_next_action="$5"
  local selected_json="null"
  if [[ -n "$selected_subcomponent" ]]; then
    selected_json="\"${selected_subcomponent}\""
  fi
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "phase": "device_resident_sim_pipeline_budget",
  "workload_id": "${workload_id}",
  "selection_status": "${selection_status}",
  "selected_subcomponent": ${selected_json},
  "recommended_next_action": "${recommended_next_action}",
  "runtime_prototype_allowed": false
}
EOF
}

write_summary() {
  local path="$1"
  local workload_class="$2"
  local total_seconds="$3"
  local sim_seconds="$4"
  local state_handoff_share="$5"
  local host_cpu_merge_share="$6"
  local gpu_compute_share="$7"
  local locate_traceback_share="$8"
  cat >"$path" <<EOF
{
  "phase": "device_resident_sim_pipeline_budget",
  "workload_class": "${workload_class}",
  "total_seconds": ${total_seconds},
  "sim_seconds": ${sim_seconds},
  "subcomponents": [
    {
      "subcomponent": "state_handoff",
      "share_of_sim_seconds": ${state_handoff_share},
      "share_of_total_seconds": 0.300000,
      "evidence_status": "provided"
    },
    {
      "subcomponent": "host_cpu_merge",
      "share_of_sim_seconds": ${host_cpu_merge_share},
      "share_of_total_seconds": 0.120000,
      "evidence_status": "provided"
    },
    {
      "subcomponent": "gpu_compute",
      "share_of_sim_seconds": ${gpu_compute_share},
      "share_of_total_seconds": 0.080000,
      "evidence_status": "provided"
    },
    {
      "subcomponent": "locate_traceback",
      "share_of_sim_seconds": ${locate_traceback_share},
      "share_of_total_seconds": 0.160000,
      "evidence_status": "provided"
    }
  ]
}
EOF
}

write_decision "$CASE_A" "sample" "selected" "state_handoff" "profile_device_resident_state_handoff"
write_decision "$CASE_B" "heavy" "selected" "state_handoff" "profile_device_resident_state_handoff"

python3 scripts/summarize_longtarget_sim_pipeline_budget_rollup.py \
  --sim-pipeline-budget-decision "$CASE_A" \
  --sim-pipeline-budget-decision "$CASE_B" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget_rollup_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["decision_status"] == "ready", decision
assert decision["workload_count"] == 2, decision
assert decision["selection_status"] == "stable_selected", decision
assert decision["selected_subcomponent"] == "state_handoff", decision
assert decision["recommended_next_action"] == "profile_device_resident_state_handoff", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

write_decision "$CASE_A" "sample" "no_stable_subcomponent" "" "stop_sim_pipeline_work"
write_decision "$CASE_B" "heavy" "selected" "locate_traceback" "profile_locate_traceback_pipeline"

python3 scripts/summarize_longtarget_sim_pipeline_budget_rollup.py \
  --sim-pipeline-budget-decision "$CASE_A" \
  --sim-pipeline-budget-decision "$CASE_B" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget_rollup_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["selection_status"] == "workload_dependent_subcomponent", decision
assert decision["selected_subcomponent"] is None, decision
assert decision["recommended_next_action"] == "expand_or_stratify_sim_pipeline_budget", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["workload_decisions"]["sample"]["selection_status"] == "no_stable_subcomponent", decision
assert decision["workload_decisions"]["heavy"]["selected_subcomponent"] == "locate_traceback", decision
PY

write_decision "$CASE_A" "sample" "insufficient_sim_substage_telemetry" "" "collect_sim_substage_telemetry"
write_decision "$CASE_B" "heavy" "selected" "state_handoff" "profile_device_resident_state_handoff"

python3 scripts/summarize_longtarget_sim_pipeline_budget_rollup.py \
  --sim-pipeline-budget-decision "$CASE_A" \
  --sim-pipeline-budget-decision "$CASE_B" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget_rollup_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["selection_status"] == "insufficient_sim_substage_telemetry", decision
assert decision["recommended_next_action"] == "collect_sim_substage_telemetry", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

test -s "$OUT_DIR/sim_pipeline_budget_rollup.md"

SAMPLE_DIR="$WORK/sample/sim_pipeline_budget"
HEAVY_DIR="$WORK/heavy/sim_pipeline_budget"
mkdir -p "$SAMPLE_DIR" "$HEAVY_DIR"
CASE_A="$SAMPLE_DIR/sim_pipeline_budget_decision.json"
CASE_B="$HEAVY_DIR/sim_pipeline_budget_decision.json"

write_decision "$CASE_A" "sample" "no_stable_subcomponent" "" "stop_sim_pipeline_work"
write_decision "$CASE_B" "heavy" "selected" "locate_traceback" "profile_locate_traceback_pipeline"
write_summary "$SAMPLE_DIR/sim_pipeline_budget.json" "sample" 18.0 10.0 0.34 0.32 0.06 0.38
write_summary "$HEAVY_DIR/sim_pipeline_budget.json" "5case_heavy" 20.0 12.0 0.12 0.14 0.16 0.52

python3 scripts/summarize_longtarget_sim_pipeline_budget_rollup.py \
  --sim-pipeline-budget-decision "$CASE_A" \
  --sim-pipeline-budget-decision "$CASE_B" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget_rollup_decision.json" "$OUT_DIR/sim_pipeline_budget_rollup_cases.tsv"
import csv
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["selection_status"] == "workload_dependent_subcomponent", decision
assert decision["stratification_status"] == "needed", decision
assert decision["minimum_next_workloads"] == [
    "one_more_locate_traceback_like_workload",
    "one_more_no_stable_like_workload",
], decision
assert decision["sim_seconds_weighted_selected_subcomponent"] == "locate_traceback", decision
assert abs(decision["selected_subcomponent_share_of_sim_seconds"] - (12.0 / 22.0)) < 1e-9, decision
assert decision["stable_subcomponents_by_workload_class"] == {}, decision

rows = list(csv.DictReader(Path(sys.argv[2]).open(encoding="utf-8"), delimiter="\t"))
assert [row["workload_id"] for row in rows] == ["sample", "heavy"], rows
assert rows[0]["workload_class"] == "sample", rows
assert rows[1]["workload_class"] == "5case_heavy", rows
assert rows[1]["locate_traceback_safe_store_share_of_sim"] == "0.520000", rows
assert rows[1]["missing_required_field_count"] == "0", rows
PY

echo "check_summarize_longtarget_sim_pipeline_budget_rollup: PASS"
