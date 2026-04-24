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

echo "check_summarize_longtarget_sim_pipeline_budget_rollup: PASS"
