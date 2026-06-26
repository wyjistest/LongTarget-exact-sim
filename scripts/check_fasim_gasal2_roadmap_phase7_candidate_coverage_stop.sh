#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase7_candidate_coverage_stop"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-roadmap-phase7-candidate-coverage \
  WORK="$WORK/candidate_coverage" \
  >"$WORK/candidate_coverage.log"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/candidate_coverage.log"; then
    echo "missing expected candidate-coverage line: $expected" >&2
    cat "$WORK/candidate_coverage.log" >&2
    exit 1
  fi
}

require_line "candidate_coverage_smoke_false_negative_scoreinfos=0"
require_line "candidate_coverage_smoke_candidate_align_attempts=51"
require_line "candidate_coverage_smoke_reference_align_attempts=51"
require_line "candidate_coverage_selected_only_false_negative_scoreinfos=0"
require_line "candidate_coverage_selected_only_candidate_align_attempts=51"
require_line "candidate_coverage_selected_only_reference_align_attempts=51"
require_line "candidate_coverage_current_decision=coverage_clean_no_align_reduction"
require_line "requires_cpu_align_attempt_reduction=1"
require_line "broad_objective_status=open"
require_line "must_not_call_update_goal_complete=1"

echo "phase7_candidate_coverage_stop_gate=current_reducer_no_go"
echo "candidate_coverage_prefix_false_negative_scoreinfos=0"
echo "candidate_coverage_prefix_align_reduction=0"
echo "candidate_coverage_selected_only_false_negative_scoreinfos=0"
echo "candidate_coverage_selected_only_align_reduction=0"
echo "candidate_coverage_stop_reason=no_cpu_align_attempt_reduction"
echo "next_phase7_required=new_reducer_or_architecture"
echo "broad_objective_status=open"
echo "must_not_call_update_goal_complete=1"
echo "ok"
