#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase1_scoped_product"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-roadmap-phase1-scoped-contract \
  WORK="$WORK/phase1_contract_work" \
  >"$WORK/phase1_contract.log"
make -C "$ROOT" check-fasim-gasal2-top5-recommended-runtime \
  WORK="$WORK/recommended_runtime_work" \
  >"$WORK/recommended_runtime.log"
make -C "$ROOT" check-fasim-gasal2-top5-product-readiness \
  WORK="$WORK/product_readiness_work" \
  >"$WORK/product_readiness.log"
make -C "$ROOT" check-fasim-gasal2-top5-scoped-completion-candidate \
  WORK="$WORK/scoped_completion_candidate_work" \
  >"$WORK/scoped_completion_candidate.log"
make -C "$ROOT" check-fasim-gasal2-goal-completion-decision \
  WORK="$WORK/goal_completion_decision_work" \
  >"$WORK/goal_completion_decision_gate.log"
python3 "$ROOT/scripts/decide_fasim_gasal2_goal_completion.py" \
  --matrix "$ROOT/docs/fasim_gasal2_workload_matrix.tsv" \
  >"$WORK/goal_completion_decision.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/phase1_contract.log" "phase1_scoped_contract_gate=ready"
require_line "$WORK/phase1_contract.log" "scoped_contract_named=1"
require_line "$WORK/phase1_contract.log" "default_off_runtime_documented=1"
require_line "$WORK/phase1_contract.log" "contract_artifacts_documented=1"
require_line "$WORK/phase1_contract.log" "non_claims_documented=1"
require_line "$WORK/phase1_contract.log" "full_objective_still_open=1"

require_line "$WORK/goal_completion_decision.log" "scoped_product_status=ready_if_user_accepts_scope"
require_line "$WORK/goal_completion_decision.log" "broad_objective_status=open"
require_line "$WORK/goal_completion_decision.log" "must_not_call_update_goal_complete=1"

echo "phase1_scoped_product_gate=ready_if_user_accepts_scope"
echo "phase1_scoped_contract=pass"
echo "top5_recommended_runtime=pass"
echo "top5_product_readiness=pass"
echo "top5_scoped_completion_candidate=pass"
echo "broad_objective_status=open"
echo "must_not_call_update_goal_complete=1"
echo "ok"
