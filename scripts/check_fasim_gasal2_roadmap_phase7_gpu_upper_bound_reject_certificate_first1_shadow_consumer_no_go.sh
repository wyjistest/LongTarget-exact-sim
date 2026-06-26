#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
EXECUTION_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"
DIRECT="$ROOT/docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$EXECUTION_PLAN" "$DIRECT" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
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
    direct,
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
    direct,
    current_state,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate First1 Shadow Consumer No-Go",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md",
    "previous_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "upper_bound_descriptors > 0",
    "upper_bound_certificates > 0",
    "reject_candidates_shadow = 0",
    "would_reject_scoreinfo_groups = 0",
    "would_reject_align_attempts = 0",
    "certificate_false_negatives = 0",
    "baseline_rows_in_rejected_groups = 0",
    "baseline_rows_in_rejected_attempts = 0",
    "unsupported_descriptors = 0",
    "fallback_to_full_cpu_replay = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 0",
    "accepted_gpu_upper_bound_reject_certificate_consumer = 0",
    "accepted_upper_bound_reject_certificate = 0",
    "accepted_pre_drop_reject_certificate = 0",
    "consumer_can_drop_scoreinfo_work = 0",
    "consumer_can_drop_align_work = 0",
    "consumer_can_reduce_cpu_replay_frontier = 0",
    "consumer_available_before_scoreinfo_prealign_skip = 0",
    "consumer_available_before_align_skip = 0",
    "rejected_work_units_available = 0",
    "reject_certificate_coverage = 0",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work",
    "do_not_implement_reducing_runtime_from_this_shadow = 1",
    "do_not_run_first64_from_this_shadow = 1",
    "do_not_promote_broad_replacement_row_from_this_shadow = 1",
    "path_b_gpu_upper_bound_reject_certificate_family_stopped = 1",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go",
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
        "missing upper-bound reject consumer no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "accepted_gpu_upper_bound_reject_certificate_consumer = 1",
    "accepted_upper_bound_reject_certificate = 1",
    "accepted_pre_drop_reject_certificate = 1",
    "consumer_can_drop_scoreinfo_work = 1",
    "consumer_can_drop_align_work = 1",
    "consumer_can_reduce_cpu_replay_frontier = 1",
    "consumer_available_before_scoreinfo_prealign_skip = 1",
    "consumer_available_before_align_skip = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gate_first1_pass = 1",
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
            f"upper-bound reject consumer no-go doc contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go" not in prev_text:
    raise SystemExit("previous upper-bound shadow scaffold does not point to consumer/no-go")

link = "docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md"
next_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
next_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
advanced_gate = "new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go"
advanced_pr = "fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go"
advanced_doc = "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md"
later_gate = "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold"
later_pr = "fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold"
later_doc = "docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md"
for label, path in [
    ("roadmap", roadmap),
    ("phase-to-completion", phase_plan),
    ("canonical phase plan", canonical),
    ("goal closure phase plan", closure),
    ("phase driver", driver),
    ("playbook", playbook),
    ("phase execution plan", execution_plan),
    ("direct phase roadmap", direct),
]:
    content = path.read_text(encoding="utf-8")
    if link not in content:
        raise SystemExit(f"{label} does not link upper-bound reject consumer no-go")
    if (
        f"current_gate_document = {advanced_doc}" not in content
        and f"current_gate_document = {link}" not in content
        and f"current_gate_document = {later_doc}" not in content
    ):
        raise SystemExit(f"{label} does not keep an upper-bound no-go checkpoint as current gate document")
    if (
        f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {next_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
        and f"current_execution_gate = {later_gate}" not in content
        and f"current_gate = {later_gate}" not in content
    ):
        raise SystemExit(f"{label} cursor was not advanced after upper-bound reject no-go")
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
        and f"current_next_pr = {later_pr}" not in content
    ):
        raise SystemExit(f"{label} next PR was not advanced after upper-bound reject no-go")

for phrase in [
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status",
    "no_go_no_rejected_work",
    "accepted_gpu_upper_bound_reject_certificate_consumer",
    "accepted_pre_drop_reject_certificate",
    "path_b_gpu_upper_bound_reject_certificate_family_stopped",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-consumer-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

target_name = "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-consumer-no-go"
if f"check-fasim-gasal2-roadmap-current-state: {target_name}" not in makefile_text:
    raise SystemExit("current-state aggregate does not include upper-bound reject consumer no-go target")

print("phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go=recorded")
print("phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status=no_go_no_rejected_work")
print("path_b_gpu_upper_bound_reject_certificate_family_stopped=1")
print("next_valid_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
