#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_scaffold.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    playbook,
    current_state,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    playbook,
    current_state,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_text = phase_plan.read_text(encoding="utf-8")
canonical_text = canonical.read_text(encoding="utf-8")
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
playbook_text = playbook.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Full-Align Verifier First1 Shadow Consumer No-Go",
    "phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_scaffold.md",
    "previous_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go",
    "phase7_full_align_verifier_first1_shadow_active = 1",
    "descriptors > 0",
    "proposals = 0",
    "proposal_failures = descriptors",
    "verifier_pass = 0",
    "verifier_fail = 0",
    "cpu_align_fallbacks = descriptors",
    "fallback_to_full_cpu_replay = 1",
    "accepted_full_align_verifier_consumer = 0",
    "accepted_full_align_verifier_certificate = 0",
    "accepted_gasal2_full_align_proposals = 0",
    "consumer_can_drop_align_work = 0",
    "consumer_can_drop_scoreinfo_work = 0",
    "consumer_can_reduce_cpu_replay_frontier = 0",
    "phase7_full_align_verifier_first1_shadow_consumer_status = no_go_no_gpu_full_align_proposals",
    "do_not_implement_reducing_runtime_from_this_shadow = 1",
    "do_not_run_first64_from_this_shadow = 1",
    "do_not_promote_broad_replacement_row_from_this_shadow = 1",
    "path_b_full_align_verifier_family_stopped = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "default behavior unchanged = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing full-align verifier consumer no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "accepted_full_align_verifier_consumer = 1",
    "accepted_full_align_verifier_certificate = 1",
    "accepted_gasal2_full_align_proposals = 1",
    "consumer_can_drop_align_work = 1",
    "consumer_can_drop_scoreinfo_work = 1",
    "consumer_can_reduce_cpu_replay_frontier = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gate_first1_shadow_pass = 1",
    "GPU score authority = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(
            f"full-align verifier consumer no-go doc contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go" not in prev_text:
    raise SystemExit("previous full-align verifier scaffold does not point to consumer/no-go")

link = "docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md"
next_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go"
next_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link full-align verifier consumer no-go checkpoint")
    if f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the post-full-align-verifier fork gate")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the post-full-align-verifier fork")

for phrase in [
    "phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go",
    "phase7_full_align_verifier_first1_shadow_consumer_status",
    "no_go_no_gpu_full_align_proposals",
    "accepted_full_align_verifier_consumer",
    "accepted_full_align_verifier_certificate",
    "path_b_full_align_verifier_family_stopped",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-consumer-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

current_state_line = next(
    (
        line
        for line in makefile_text.splitlines()
        if line.startswith("check-fasim-gasal2-roadmap-current-state:")
    ),
    "",
)
target_name = "check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-consumer-no-go"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include full-align verifier consumer no-go target")

print("phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go=recorded")
print("phase7_full_align_verifier_first1_shadow_consumer_status=no_go_no_gpu_full_align_proposals")
print("path_b_full_align_verifier_family_stopped=1")
print("next_valid_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
