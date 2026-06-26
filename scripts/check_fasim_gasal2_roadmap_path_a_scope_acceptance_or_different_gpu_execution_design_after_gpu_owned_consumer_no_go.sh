#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
EXECUTION_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$EXECUTION_PLAN" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
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
    execution_plan,
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
    execution_plan,
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
execution_text = execution_plan.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After GPU-Owned Consumer No-Go",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md",
    "previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go",
    "user_scope_acceptance_recorded = 0",
    "scoped_completion_may_close_goal = 0",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate",
    "accepted_gpu_owned_scoreinfo_consumer = 0",
    "accepted_pre_drop_frontier_certificate = 0",
    "certificate_produced_before_work_drop = 0",
    "certificate_consumed_before_cpu_replay_selection = 0",
    "cpu_replay_attempts = baseline_cpu_attempts",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "path_b_gpu_owned_scoreinfo_consumer_family_stopped = 1",
    "path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status = design_defined",
    "path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate",
    "path_b_differs_from_gpu_owned_scoreinfo_consumer = 1",
    "path_b_differs_from_scoreinfo_certificate_engine = 1",
    "path_b_differs_from_post_v5_3_descriptor_stream = 1",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "GPU proposal:",
    "CPU verifier certificate:",
    "local maximum witness",
    "reverse-start witness",
    "traceback/CIGAR path score witness",
    "The CPU verifier is not allowed to trust GASAL2 output by assertion.",
    "next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "input descriptor:",
    "GPU proposal fields:",
    "CPU verifier fields:",
    "fail-closed telemetry:",
    "proposals > 0",
    "verifier_pass > 0 or verifier failure taxonomy complete",
    "score_mismatches = 0",
    "endpoint_mismatches = 0",
    "cigar_mismatches = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "verifier is consumed before CPU Align work is skipped",
    "candidate_align_attempts < reference_align_attempts",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "no real opt-in",
    "no first64 before first1 passes",
    "no runtime work drop in the design/spec checkpoint",
    "no promotion of the stopped GPU-owned scoreInfo consumer family",
    "no promotion of the stopped scoreInfo certificate-engine family",
    "no promotion of the stopped post-v5.3 descriptor-stream family",
    "no GASAL2 endpoint authority",
    "no GASAL2 CIGAR authority",
    "no GASAL2 traceback authority",
    "no GASAL2 output authority",
    "no GASAL2 digest authority",
    "CPU aligner.Align() authority = 1",
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
        "missing path-a-or-different-design-after-gpu-owned-consumer-no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "user_scope_acceptance_recorded = 1",
    "scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "path_b_runtime_pr_allowed = 1",
    "path_b_differs_from_gpu_owned_scoreinfo_consumer = 0",
    "path_b_differs_from_scoreinfo_certificate_engine = 0",
    "path_b_differs_from_post_v5_3_descriptor_stream = 0",
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
            "GPU-owned-consumer fork doc contains forbidden phrase: "
            f"{forbidden}"
        )

if "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go" not in prev_text:
    raise SystemExit("GPU-owned consumer no-go does not point to this fork")

link = "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md"
next_gate = "phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance"
next_pr = "fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance"
advanced_gate = "phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold"
advanced_pr = "fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
    ("phase execution plan", execution_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link GPU-owned-consumer fork checkpoint")
    if (
        f"current_gate = {next_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
    ):
        raise SystemExit(
            f"{name} cursor was not advanced to the full-align verifier spec gate or a later accepted gate"
        )
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
    ):
        raise SystemExit(
            f"{name} next PR was not advanced to the full-align verifier spec or a later accepted PR"
        )

for phrase in [
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go",
    "path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status",
    "gasal2_full_align_result_with_cpu_verifier_certificate",
    "phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-owned-consumer-no-go:"
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
if "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-owned-consumer-no-go" not in current_state_line:
    raise SystemExit("current-state target does not depend on GPU-owned-consumer fork checker")

print("path_a_or_different_design_after_gpu_owned_consumer_no_go_document=present")
print("path_b_new_design_family=gasal2_full_align_result_with_cpu_verifier_certificate")
print("next_valid_gate=phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance")
print("current_next_pr=fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance")
print("runtime_reduction_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
