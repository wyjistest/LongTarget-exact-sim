#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scope_or_broad_design_decision.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PATH_A="$ROOT/docs/fasim_gasal2_path_a_scoped_completion_acceptance.md"
PHASE8="$ROOT/scripts/check_fasim_gasal2_roadmap_phase8_completion_decision.sh"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ROADMAP" "$PATH_A" "$PHASE8" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
path_a = Path(sys.argv[3])
phase8 = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, roadmap, path_a, phase8, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
roadmap_flat = " ".join(roadmap.read_text(encoding="utf-8").split())
path_a_flat = " ".join(path_a.read_text(encoding="utf-8").split())
phase8_text = phase8.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "scope_or_broad_design_decision_packet = defined",
    "scope_or_broad_design_decision_required = 0",
    "path_a_user_acceptance_required = 0",
    "path_a_user_acceptance_recorded = 1",
    "path_b_new_broad_architecture_required = 0",
    "current_decision = path_a_scoped_completion_accepted",
    "active_goal_completion_status = complete_scoped_path_a",
    "completion_guard_cleared = 1",
    "path_a_choice = accept_scoped_completion",
    "path_b_choice = pursue_different_gpu_execution_design",
    "path_a_acceptance_document = docs/fasim_gasal2_path_a_scoped_completion_acceptance.md",
    "path_b_current_v4_source_replay_status = stopped_performance_no_go",
    "current_v4_source_replay_must_not_continue = 1",
    "broad_replacement_row_allowed = 0",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 0",
    "Path A is accepted:",
    "If Path B is selected in the future:",
    "different GPU execution design",
    "full row-set/digest equality",
    "candidate_wall_seconds < baseline_wall_seconds",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required decision packet phrase: {phrase}")

for phrase in [
    "scope_or_broad_design_decision_required = 0",
    "path_a_user_acceptance_required = 0",
    "path_b_new_broad_architecture_required = 0",
]:
    if phrase not in roadmap_flat:
        raise SystemExit(f"roadmap missing decision field: {phrase}")

for phrase in [
    "path_a_scoped_completion_acceptance_packet = defined",
    "user_scope_acceptance_recorded = 1",
    "scoped_completion_may_close_goal = 1",
    "active_goal_completion_status = complete_scoped_path_a",
]:
    if phrase not in path_a_flat:
        raise SystemExit(f"Path A acceptance packet missing: {phrase}")

for phrase in [
    "scope_or_broad_design_decision_required=0",
    "path_a_user_acceptance_required=0",
    "path_b_new_broad_architecture_required=0",
]:
    if phrase not in phase8_text:
        raise SystemExit(f"Phase 8 checker missing emitted field: {phrase}")

target = "check-fasim-gasal2-roadmap-scope-or-broad-design-decision:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
dependency = target[:-1]
if dependency not in aggregate_line:
    raise SystemExit("roadmap current-state target missing decision dependency")

print("scope_or_broad_design_decision_packet=defined")
print("scope_or_broad_design_decision_required=0")
print("path_a_user_acceptance_required=0")
print("path_a_user_acceptance_recorded=1")
print("path_b_new_broad_architecture_required=0")
print("current_decision=path_a_scoped_completion_accepted")
print("current_v4_source_replay_must_not_continue=1")
print("broad_replacement_row_allowed=0")
print("broad_objective_status=open")
print("active_goal_completion_status=complete_scoped_path_a")
print("completion_guard_cleared=1")
print("must_not_call_update_goal_complete=0")
print("ok")
PY
