#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_goal_completion_decision"}"
CHECKER="$ROOT/scripts/decide_fasim_gasal2_goal_completion.py"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
ACCEPTANCE="$ROOT/docs/fasim_gasal2_path_a_scoped_completion_acceptance.md"

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$CHECKER" --matrix "$MATRIX" --acceptance "$ACCEPTANCE" \
  >"$WORK/decision.txt"

cat >"$WORK/broad_weak.tsv" <<'EOF'
workload	contract	scope	status	row_equal	top5_equal	speedup	fallbacks	notes
neat1_first64	broad_replacement	claimed	pass	true	true	1.250	0	full row-set equal but align-side reduction evidence missing
EOF

python3 "$CHECKER" --matrix "$WORK/broad_weak.tsv" >"$WORK/broad_weak_decision.txt"

cat >"$WORK/broad_complete.tsv" <<'EOF'
workload	contract	scope	status	row_equal	top5_equal	speedup	fallbacks	scoreinfo_reduced	align_side_reduced	notes
neat1_first64	broad_replacement	claimed	pass	true	true	1.250	0	true	true	full row-set equal; scoreInfo and Align-side work reduced
EOF

python3 "$CHECKER" --matrix "$WORK/broad_complete.tsv" >"$WORK/broad_complete_decision.txt"

require_line() {
  local expected="$1"
  local file="${2:-"$WORK/decision.txt"}"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "scoped_product_status=accepted"
require_line "broad_objective_status=open"
require_line "broad_restart_required=0"
require_line "claimed_workloads_clean=1"
require_line "broad_gate_rows_clean=0"
require_line "blocked_or_unclaimed_workloads=3"
require_line "user_scope_acceptance_recorded=1"
require_line "scoped_completion_may_close_goal=1"
require_line "path_a_user_acceptance_recorded=1"
require_line "path_a_scoped_completion_may_close_goal=1"
require_line "active_goal_completion_status=complete_scoped_path_a"
require_line "final_goal_decision=complete_scoped_path_a"
require_line "scope_or_broad_design_decision_required=0"
require_line "path_a_user_acceptance_required=0"
require_line "path_b_new_broad_architecture_required=0"
require_line "completion_guard_cleared=1"
require_line "goal_completion_status=complete"
require_line "must_not_call_update_goal_complete=0"

require_line "broad_objective_status=open" "$WORK/broad_weak_decision.txt"
require_line "broad_restart_required=1" "$WORK/broad_weak_decision.txt"
require_line "broad_gate_rows_clean=0" "$WORK/broad_weak_decision.txt"
require_line "final_goal_decision=not_complete_without_user_scope_acceptance" "$WORK/broad_weak_decision.txt"
require_line "scope_or_broad_design_decision_required=1" "$WORK/broad_weak_decision.txt"
require_line "path_a_user_acceptance_required=1" "$WORK/broad_weak_decision.txt"
require_line "path_b_new_broad_architecture_required=1" "$WORK/broad_weak_decision.txt"
require_line "must_not_call_update_goal_complete=1" "$WORK/broad_weak_decision.txt"

require_line "broad_objective_status=complete" "$WORK/broad_complete_decision.txt"
require_line "broad_restart_required=0" "$WORK/broad_complete_decision.txt"
require_line "broad_gate_rows_clean=1" "$WORK/broad_complete_decision.txt"
require_line "final_goal_decision=complete" "$WORK/broad_complete_decision.txt"
require_line "scope_or_broad_design_decision_required=0" "$WORK/broad_complete_decision.txt"
require_line "path_a_user_acceptance_required=0" "$WORK/broad_complete_decision.txt"
require_line "path_b_new_broad_architecture_required=0" "$WORK/broad_complete_decision.txt"
require_line "must_not_call_update_goal_complete=0" "$WORK/broad_complete_decision.txt"

echo "ok"
