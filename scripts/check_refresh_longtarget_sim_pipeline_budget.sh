#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-refresh-sim-pipeline-budget-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

TOP_LEVEL_DECISION="$WORK/top_level_perf_budget_decision.json"
SIM_TELEMETRY_BUDGET="$WORK/sim_telemetry_budget.json"
OUTPUT_ROOT="$WORK/out"

cat >"$TOP_LEVEL_DECISION" <<'EOF'
{
  "decision_status": "ready",
  "phase": "top_level_optimization_budget_reset",
  "selected_component": "sim",
  "recommended_next_action": "profile_device_resident_sim_pipeline",
  "runtime_prototype_allowed": false
}
EOF

cat >"$SIM_TELEMETRY_BUDGET" <<'EOF'
{
  "decision_status": "ready",
  "projected_total_seconds": 250.0,
  "projected_sim_seconds": 100.0,
  "projected_sim_initial_scan_d2h_seconds": 20.0,
  "projected_sim_initial_state_handoff_seconds": 15.0,
  "projected_sim_initial_host_rebuild_seconds": 10.0,
  "projected_sim_initial_scan_cpu_merge_seconds": 25.0,
  "projected_sim_initial_scan_gpu_seconds": 15.0,
  "projected_sim_locate_seconds": 8.0,
  "projected_sim_traceback_seconds": 4.0,
  "projected_sim_safe_store_seconds": 2.0,
  "projected_sim_output_materialization_seconds": 1.0
}
EOF

scripts/refresh_longtarget_sim_pipeline_budget.sh \
  --top-level-budget-decision "$TOP_LEVEL_DECISION" \
  --sim-telemetry-budget "$SIM_TELEMETRY_BUDGET" \
  --output-root "$OUTPUT_ROOT"

python3 - <<'PY' "$OUTPUT_ROOT" "$TOP_LEVEL_DECISION" "$SIM_TELEMETRY_BUDGET"
import json
import math
import sys
from pathlib import Path

root = Path(sys.argv[1])
decision = json.loads((root / "sim_pipeline_budget" / "sim_pipeline_budget_decision.json").read_text(encoding="utf-8"))
budget = json.loads((root / "sim_pipeline_budget" / "sim_pipeline_budget.json").read_text(encoding="utf-8"))
cases = (root / "sim_pipeline_budget" / "sim_pipeline_budget_cases.tsv").read_text(encoding="utf-8").splitlines()

rows = {row["subcomponent"]: row for row in budget["subcomponents"]}
assert decision["decision_status"] == "ready", decision
assert decision["selection_status"] == "selected", decision
assert decision["selected_subcomponent"] == "state_handoff", decision
assert decision["recommended_next_action"] == "profile_device_resident_state_handoff", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert budget["source_top_level_budget_decision"] == sys.argv[2], budget
assert budget["source_input_budget"] == sys.argv[3], budget
assert math.isclose(rows["state_handoff"]["seconds"], 45.0, rel_tol=0, abs_tol=1e-12), rows
assert math.isclose(rows["locate_traceback"]["seconds"], 15.0, rel_tol=0, abs_tol=1e-12), rows
assert cases[0].split("\t")[:4] == ["case_id", "subcomponent", "seconds", "share_of_sim_seconds"], cases
assert (root / "sim_pipeline_budget" / "sim_pipeline_budget.md").is_file()
PY

echo "check_refresh_longtarget_sim_pipeline_budget: PASS"
