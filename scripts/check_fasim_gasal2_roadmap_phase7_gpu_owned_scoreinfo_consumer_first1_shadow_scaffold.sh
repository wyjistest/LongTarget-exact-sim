#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE_PLAN="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
PHASE_DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
CURRENT_STATE_CHECK="$ROOT/scripts/check_fasim_gasal2_roadmap_current_state.sh"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL_PLAN" "$CLOSURE_PLAN" "$PHASE_DRIVER" "$PLAYBOOK" "$CURRENT_STATE" "$CURRENT_STATE_CHECK" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical_plan,
    closure_plan,
    phase_driver,
    playbook,
    current_state,
    current_state_check,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical_plan,
    closure_plan,
    phase_driver,
    playbook,
    current_state,
    current_state_check,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_text = phase_plan.read_text(encoding="utf-8")
canonical_text = canonical_plan.read_text(encoding="utf-8")
closure_text = closure_plan.read_text(encoding="utf-8")
driver_text = phase_driver.read_text(encoding="utf-8")
playbook_text = playbook.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
current_state_check_text = current_state_check.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 GPU-Owned ScoreInfo Consumer First1 Shadow Scaffold",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "required_runtime_env = FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_",
    "requested = 1",
    "active = 1",
    "gpu_owned_scoreinfo_consumer_requested = 1",
    "gpu_owned_scoreinfo_consumer_active = 1",
    "gpu_owned_scoreinfo_states > 0",
    "gpu_owned_attempt_frontier_attempts > 0",
    "gpu_owned_replay_frontier_attempts > 0",
    "gpu_owned_skipped_scoreinfo_groups = 0",
    "gpu_owned_skipped_attempts = 0",
    "cpu_replay_attempts > 0",
    "baseline_cpu_attempts > 0",
    "cpu_replay_attempts = baseline_cpu_attempts",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "certificate_produced_before_work_drop = 0",
    "certificate_consumed_before_cpu_replay_selection = 0",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_to_full_cpu_replay = 1",
    "fallback_accounting_clean = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "full_rows_equal = 0",
    "digest_match = 0",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "gate_first1_shadow_pass = 0",
    "gate_first1_pass = 0",
    "path_b_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing gpu-owned first1 shadow scaffold phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "certificate_produced_before_work_drop = 1",
    "certificate_consumed_before_cpu_replay_selection = 1",
    "fallback_accounting_clean = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"gpu-owned first1 shadow scaffold doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold" not in prev_text:
    raise SystemExit("previous spec doc no longer points to gpu-owned first1 shadow scaffold")

link = "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md"
for label, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion plan", phase_text),
    ("canonical phase plan", canonical_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{label} does not link gpu-owned first1 shadow scaffold checkpoint")
    if "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go" not in content:
        raise SystemExit(f"{label} does not record the consumer/no-go checkpoint after gpu-owned first1 shadow")
    if "current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go" not in content:
        raise SystemExit(f"{label} cursor was not advanced to the gpu-owned consumer/no-go gate")
    if "runtime_reduction_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime reduction disabled")
    if "runtime_work_drop_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime work drop disabled")
    if "first64_runtime_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep first64 disabled")

for phrase in [
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

for phrase in [
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold=fail_closed_shadow",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled=0",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled=0",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass=0",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go=recorded",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_next_valid_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go=recorded",
    "current_execution_gate=phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "current_next_pr=fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
]:
    if phrase not in current_state_check_text:
        raise SystemExit(f"current-state checker missing phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-scaffold:",
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
if "check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-scaffold" not in current_state_line:
    raise SystemExit("current-state aggregate does not include gpu-owned first1 shadow scaffold target")

print("phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold=fail_closed_shadow")
print("phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction")
print("phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled=0")
print("phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled=0")
print("phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass=0")
print("next_valid_gate=phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
