#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-top-level-budget-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

BRANCH_ROLLUP_DECISION="$WORK/branch_rollup_decision.json"
EXPLICIT_BUDGET="$WORK/explicit_budget.json"
PROJECTED_REPORT="$WORK/projected_report.json"
OUT_DIR="$WORK/out"

cat >"$BRANCH_ROLLUP_DECISION" <<'EOF'
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "current_phase": "candidate_index_structural_profiling",
  "current_phase_status": "stopped",
  "recommended_next_action": "stop_candidate_index_structural_profiling",
  "stop_reason": "no_stable_structural_signal",
  "runtime_prototype_allowed": false
}
EOF

cat >"$EXPLICIT_BUDGET" <<'EOF'
{
  "decision_status": "ready",
  "total_seconds": 100.0,
  "components": {
    "candidate_index": {"seconds": 55.0},
    "sim_initial_scan_d2h": {"seconds": 20.0},
    "calc_score": {"seconds": 15.0},
    "safe_store": {"seconds": 10.0}
  }
}
EOF

python3 ./scripts/summarize_longtarget_top_level_perf_budget.py \
  --input-budget "$EXPLICIT_BUDGET" \
  --candidate-index-branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/top_level_perf_budget.json" "$OUT_DIR/top_level_perf_budget_decision.json"
import json
import math
import sys
from pathlib import Path

budget = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
decision = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
components = {row["component"]: row for row in budget["components"]}

assert budget["decision_status"] == "ready", budget
assert budget["phase"] == "top_level_optimization_budget_reset", budget
assert budget["total_seconds"] == 100.0, budget
assert budget["runtime_prototype_allowed"] is False, budget
assert budget["selected_component"] == "sim_initial_scan_d2h", budget
assert budget["recommended_next_action"] == "profile_d2h_handoff_path", budget
assert decision["recommended_next_action"] == "profile_d2h_handoff_path", decision
assert decision["selected_component"] == "sim_initial_scan_d2h", decision
assert budget["allowed_next_actions"] == [
    "profile_calc_score_path",
    "profile_device_resident_sim_pipeline",
    "profile_d2h_handoff_path",
    "profile_safe_store_or_locate_path",
    "stop_candidate_index_work",
], budget

candidate = components["candidate_index"]
assert candidate["material"] is True, candidate
assert candidate["status"] == "known_material_but_no_actionable_leaf", candidate
assert candidate["candidate_index_policy"] == "do_not_continue_leaf_split", candidate
assert candidate["recommended_action"] == "stop_candidate_index_work", candidate
assert candidate["eligible_for_selection"] is False, candidate

d2h = components["sim_initial_scan_d2h"]
assert math.isclose(d2h["share_of_total"], 0.2, rel_tol=0, abs_tol=1e-12), d2h
assert math.isclose(d2h["max_speedup_if_removed"], 1.25, rel_tol=0, abs_tol=1e-12), d2h
PY

cat >"$PROJECTED_REPORT" <<'EOF'
{
  "projected_total_seconds": 200.0,
  "projected_calc_score_seconds": 80.0,
  "projected_sim_seconds": 70.0,
  "projected_sim_initial_scan_seconds": 45.0,
  "projected_sim_initial_scan_cpu_merge_seconds": 30.0,
  "projected_postprocess_seconds": 20.0,
  "benchmark": {
    "calc_score_tasks_total": 10,
    "calc_score_cuda_tasks": 7,
    "calc_score_cpu_fallback_tasks": 3
  }
}
EOF

python3 ./scripts/summarize_longtarget_top_level_perf_budget.py \
  --input-budget "$PROJECTED_REPORT" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/top_level_perf_budget.json"
import json
import math
import sys
from pathlib import Path

budget = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
components = {row["component"]: row for row in budget["components"]}

assert budget["selected_component"] == "calc_score", budget
assert budget["recommended_next_action"] == "profile_calc_score_path", budget
assert components["calc_score"]["recommended_action"] == "profile_calc_score_path", components
assert components["sim_initial_scan"]["recommended_action"] == "profile_device_resident_sim_pipeline", components
assert components["postprocess"]["recommended_action"] == "profile_safe_store_or_locate_path", components
assert math.isclose(components["calc_score"]["share_of_total"], 0.4, rel_tol=0, abs_tol=1e-12), components
assert math.isclose(components["calc_score"]["max_speedup_if_removed"], 200.0 / 120.0, rel_tol=0, abs_tol=1e-12), components
assert "split_candidate_index" not in json.dumps(budget), budget
PY

test -s "$OUT_DIR/top_level_perf_budget.md"

echo "check_summarize_longtarget_top_level_perf_budget: PASS"
