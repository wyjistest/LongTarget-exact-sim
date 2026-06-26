#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase8_completion_decision"}"

rm -rf "$WORK"
mkdir -p "$WORK"

WORK="$WORK/goal_completion_decision_work" \
make -C "$ROOT" check-fasim-gasal2-goal-completion-decision \
  >"$WORK/goal_completion_decision_gate.log"

python3 "$ROOT/scripts/decide_fasim_gasal2_goal_completion.py" \
  --matrix "$ROOT/docs/fasim_gasal2_workload_matrix.tsv" \
  --acceptance "$ROOT/docs/fasim_gasal2_path_a_scoped_completion_acceptance.md" \
  >"$WORK/goal_completion_decision.txt"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/goal_completion_decision_gate.log" "ok"
require_line "$WORK/goal_completion_decision.txt" "scoped_product_status=accepted"
require_line "$WORK/goal_completion_decision.txt" "broad_objective_status=open"
require_line "$WORK/goal_completion_decision.txt" "broad_restart_required=0"
require_line "$WORK/goal_completion_decision.txt" "broad_gate_rows_clean=0"
require_line "$WORK/goal_completion_decision.txt" "user_scope_acceptance_recorded=1"
require_line "$WORK/goal_completion_decision.txt" "scoped_completion_may_close_goal=1"
require_line "$WORK/goal_completion_decision.txt" "path_a_user_acceptance_recorded=1"
require_line "$WORK/goal_completion_decision.txt" "path_a_scoped_completion_may_close_goal=1"
require_line "$WORK/goal_completion_decision.txt" "active_goal_completion_status=complete_scoped_path_a"
require_line "$WORK/goal_completion_decision.txt" "final_goal_decision=complete_scoped_path_a"
require_line "$WORK/goal_completion_decision.txt" "scope_or_broad_design_decision_required=0"
require_line "$WORK/goal_completion_decision.txt" "path_a_user_acceptance_required=0"
require_line "$WORK/goal_completion_decision.txt" "path_b_new_broad_architecture_required=0"
require_line "$WORK/goal_completion_decision.txt" "completion_guard_cleared=1"
require_line "$WORK/goal_completion_decision.txt" "goal_completion_status=complete"
require_line "$WORK/goal_completion_decision.txt" "must_not_call_update_goal_complete=0"

echo "phase8_completion_decision_gate=complete_scoped_path_a"
echo "goal_completion_decision=pass"
echo "scoped_product_status=accepted"
echo "broad_objective_status=open"
echo "broad_restart_required=0"
echo "broad_gate_rows_clean=0"
echo "user_scope_acceptance_recorded=1"
echo "scoped_completion_may_close_goal=1"
echo "path_a_user_acceptance_recorded=1"
echo "path_a_scoped_completion_may_close_goal=1"
echo "active_goal_completion_status=complete_scoped_path_a"
echo "final_goal_decision=complete_scoped_path_a"
echo "scope_or_broad_design_decision_required=0"
echo "path_a_user_acceptance_required=0"
echo "path_b_new_broad_architecture_required=0"
echo "completion_guard_cleared=1"
echo "goal_completion_status=complete"
echo "must_not_call_update_goal_complete=0"
echo "ok"
