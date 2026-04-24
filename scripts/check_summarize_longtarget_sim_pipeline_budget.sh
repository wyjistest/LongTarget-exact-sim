#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-sim-pipeline-budget-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

TOP_LEVEL_DECISION="$WORK/top_level_perf_budget_decision.json"
SIM_BUDGET="$WORK/sim_budget.json"
OUT_DIR="$WORK/out"

write_top_level_decision() {
  local selected_component="$1"
  local recommended_next_action="$2"
  cat >"$TOP_LEVEL_DECISION" <<EOF
{
  "decision_status": "ready",
  "phase": "top_level_optimization_budget_reset",
  "selected_component": "${selected_component}",
  "recommended_next_action": "${recommended_next_action}",
  "runtime_prototype_allowed": false
}
EOF
}

assert_decision() {
  local expected_action="$1"
  local expected_component="$2"
  python3 - "$OUT_DIR" "$expected_action" "$expected_component" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
expected_action = sys.argv[2]
expected_component = sys.argv[3]
budget = json.loads((out_dir / "sim_pipeline_budget.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "sim_pipeline_budget_decision.json").read_text(encoding="utf-8"))
cases = (out_dir / "sim_pipeline_budget_cases.tsv").read_text(encoding="utf-8").splitlines()

assert budget["decision_status"] == "ready", budget
assert budget["phase"] == "device_resident_sim_pipeline_budget", budget
assert budget["runtime_prototype_allowed"] is False, budget
assert budget["recommended_next_action"] == expected_action, budget
assert budget["selected_subcomponent"] == expected_component, budget
assert decision["recommended_next_action"] == expected_action, decision
assert decision["selected_subcomponent"] == expected_component, decision
assert cases[0].split("\t")[:4] == ["case_id", "subcomponent", "seconds", "share_of_sim_seconds"], cases
assert budget["allowed_next_actions"] == [
    "collect_sim_substage_telemetry",
    "profile_device_resident_state_handoff",
    "profile_device_side_ordered_candidate_maintenance",
    "profile_sim_initial_scan_kernel",
    "profile_locate_traceback_pipeline",
    "stop_sim_pipeline_work",
], budget
PY
}

assert_insufficient_telemetry() {
  python3 - "$OUT_DIR" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
budget = json.loads((out_dir / "sim_pipeline_budget.json").read_text(encoding="utf-8"))
decision = json.loads((out_dir / "sim_pipeline_budget_decision.json").read_text(encoding="utf-8"))

assert budget["decision_status"] == "ready", budget
assert budget["selection_status"] == "insufficient_sim_substage_telemetry", budget
assert budget["recommended_next_action"] == "collect_sim_substage_telemetry", budget
assert budget["selected_subcomponent"] is None, budget
assert budget["provided_subcomponent_count"] == 0, budget
assert decision["selection_status"] == "insufficient_sim_substage_telemetry", decision
assert decision["recommended_next_action"] == "collect_sim_substage_telemetry", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY
}

write_top_level_decision "sim" "profile_device_resident_sim_pipeline"

cat >"$SIM_BUDGET" <<'EOF'
{
  "projected_total_seconds": 200.0,
  "projected_sim_seconds": 100.0
}
EOF

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

assert_insufficient_telemetry

cat >"$SIM_BUDGET" <<'EOF'
{
  "decision_status": "ready",
  "total_seconds": 200.0,
  "sim_seconds": 100.0,
  "cases": [
    {
      "case_id": "case-a",
      "sim_seconds": 100.0,
      "sim_initial_scan_d2h_seconds": 30.0,
      "candidate_state_handoff_seconds": 15.0,
      "host_rebuild_seconds": 10.0,
      "sim_initial_scan_cpu_merge_seconds": 20.0,
      "sim_initial_scan_gpu_seconds": 15.0,
      "sim_locate_seconds": 5.0,
      "sim_traceback_seconds": 5.0
    }
  ]
}
EOF

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

assert_decision "profile_device_resident_state_handoff" "state_handoff"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget.json"
import json
import math
import sys
from pathlib import Path

budget = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = {row["subcomponent"]: row for row in budget["subcomponents"]}
assert math.isclose(rows["state_handoff"]["seconds"], 55.0, rel_tol=0, abs_tol=1e-12), rows
assert math.isclose(rows["state_handoff"]["share_of_sim_seconds"], 0.55, rel_tol=0, abs_tol=1e-12), rows
assert math.isclose(rows["state_handoff"]["share_of_total_seconds"], 0.275, rel_tol=0, abs_tol=1e-12), rows
assert rows["state_handoff"]["recommended_action"] == "profile_device_resident_state_handoff", rows
PY

cat >"$SIM_BUDGET" <<'EOF'
{
  "projected_total_seconds": 200.0,
  "projected_sim_seconds": 100.0,
  "projected_sim_initial_scan_gpu_seconds": 45.0,
  "projected_sim_initial_scan_cpu_merge_seconds": 30.0,
  "projected_sim_locate_seconds": 15.0,
  "projected_sim_traceback_seconds": 10.0
}
EOF

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

assert_decision "profile_sim_initial_scan_kernel" "gpu_compute"

cat >"$SIM_BUDGET" <<'EOF'
{
  "projected_total_seconds": 200.0,
  "projected_sim_seconds": 100.0,
  "projected_sim_initial_scan_cpu_merge_seconds": 50.0,
  "projected_sim_initial_scan_gpu_seconds": 25.0,
  "projected_sim_locate_seconds": 15.0,
  "projected_sim_traceback_seconds": 10.0
}
EOF

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

assert_decision "profile_device_side_ordered_candidate_maintenance" "host_cpu_merge"

cat >"$SIM_BUDGET" <<'EOF'
{
  "projected_total_seconds": 200.0,
  "projected_sim_seconds": 100.0,
  "projected_sim_initial_scan_gpu_seconds": 20.0,
  "projected_sim_initial_scan_cpu_merge_seconds": 20.0,
  "projected_sim_locate_seconds": 35.0,
  "projected_sim_traceback_seconds": 15.0,
  "projected_sim_output_materialization_seconds": 10.0
}
EOF

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

assert_decision "profile_locate_traceback_pipeline" "locate_traceback"

write_top_level_decision "calc_score" "profile_calc_score_path"

python3 ./scripts/summarize_longtarget_sim_pipeline_budget.py \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --input-budget "$SIM_BUDGET" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/sim_pipeline_budget_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["decision_status"] == "inactive", decision
assert decision["recommended_next_action"] == "return_to_top_level_budget", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

test -s "$OUT_DIR/sim_pipeline_budget.md"

echo "check_summarize_longtarget_sim_pipeline_budget: PASS"
