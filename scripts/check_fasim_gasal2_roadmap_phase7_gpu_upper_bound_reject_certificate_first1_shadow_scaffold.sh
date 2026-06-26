#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
EXECUTION_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"
DIRECT="$ROOT/docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
CURRENT_STATE_CHECK="$ROOT/scripts/check_fasim_gasal2_roadmap_current_state.sh"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$EXECUTION_PLAN" "$DIRECT" "$CURRENT_STATE" "$CURRENT_STATE_CHECK" "$MAKEFILE" <<'PY'
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
    current_state_check,
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
    current_state_check,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
current_state_check_text = current_state_check.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate First1 Shadow Scaffold",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = fail_closed_shadow",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "required_runtime_env = FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_upper_bound_reject_",
    "requested = 1",
    "active = 1",
    "upper_bound_descriptors > 0",
    "upper_bound_certificates > 0",
    "reject_candidates_shadow",
    "would_reject_scoreinfo_groups",
    "would_reject_align_attempts",
    "certificate_false_negatives = 0",
    "baseline_rows_in_rejected_groups = 0",
    "baseline_rows_in_rejected_attempts = 0",
    "unsupported_descriptors = 0",
    "fallback_to_full_cpu_replay = 1",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "gpu_score_authority = 0",
    "gpu_endpoint_authority = 0",
    "gpu_cigar_traceback_output_authority = 0",
    "gpu_output_digest_authority = 0",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 0",
    "path_b_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "current_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing GPU upper-bound reject certificate first1 shadow phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_to_full_cpu_replay = 0",
    "gate_first1_pass = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
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
        raise SystemExit(f"upper-bound shadow doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold" not in prev_text:
    raise SystemExit("previous upper-bound spec no longer points to first1 shadow scaffold")

link = "docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md"
next_gate = "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go"
next_pr = "fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go"
advanced_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
advanced_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
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
        raise SystemExit(f"{label} does not link upper-bound first1 shadow scaffold")
    if (
        f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {next_gate}" not in content
        and f"historical_execution_gate = {next_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
    ):
        raise SystemExit(f"{label} cursor was not advanced to upper-bound consumer/no-go")
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"historical_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
    ):
        raise SystemExit(f"{label} next PR was not advanced to upper-bound consumer/no-go")
    if "runtime_reduction_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime reduction disabled")
    if "runtime_work_drop_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime work drop disabled")
    if "first64_runtime_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep first64 disabled")

for phrase in [
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status",
    "phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

for phrase in [
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold=fail_closed_shadow",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction",
    "phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass=1",
    "next_valid_gate=phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "current_execution_gate=phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "current_next_pr=fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_check_text:
        raise SystemExit(f"current-state checker missing phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-gpu-upper-bound-reject-certificate-first1-shadow-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-scaffold:",
]:
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
if "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-scaffold" not in current_state_line:
    raise SystemExit("current-state aggregate does not include upper-bound scaffold target")

print("phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold=fail_closed_shadow")
print("phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction")
print("phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass=1")
print("next_valid_gate=phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
