#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md"
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
    "# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine First1 Shadow Consumer No-Go",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md",
    "previous_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "native_scoreinfo_tiles > 0",
    "forward_endpoint_witnesses = 0",
    "reverse_start_witnesses = 0",
    "traceback_cigar_witnesses = 0",
    "certificates = 0",
    "missing_required_attempts = native_scoreinfo_tiles",
    "cpu_align_fallbacks = native_scoreinfo_tiles",
    "fallback_to_full_cpu_replay = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "fallback_accounting_clean = 0",
    "gate_first1_shadow_pass = 0",
    "gate_first1_pass = 0",
    "accepted_native_cuda_fasim_dp_engine_consumer = 0",
    "accepted_native_dp_certificate = 0",
    "accepted_pre_drop_certificate = 0",
    "consumer_can_drop_scoreinfo_work = 0",
    "consumer_can_drop_align_work = 0",
    "consumer_can_reduce_cpu_replay_frontier = 0",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_status = no_go_no_native_dp_certificates",
    "do_not_implement_reducing_runtime_from_this_shadow = 1",
    "do_not_run_first64_from_this_shadow = 1",
    "do_not_promote_broad_replacement_row_from_this_shadow = 1",
    "path_b_native_cuda_fasim_dp_engine_family_stopped = 1",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
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
        "missing native CUDA Fasim DP consumer no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "accepted_native_cuda_fasim_dp_engine_consumer = 1",
    "accepted_native_dp_certificate = 1",
    "accepted_pre_drop_certificate = 1",
    "consumer_can_drop_scoreinfo_work = 1",
    "consumer_can_drop_align_work = 1",
    "consumer_can_reduce_cpu_replay_frontier = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gate_first1_shadow_pass = 1",
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
            f"native CUDA Fasim DP consumer no-go doc contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go" not in prev_text:
    raise SystemExit("previous native CUDA Fasim DP scaffold does not point to consumer/no-go")

link = "docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md"
next_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
next_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
advanced_gate = "new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go"
advanced_pr = "fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link native CUDA Fasim DP consumer no-go checkpoint")
    if (
        f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {next_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
    ):
        raise SystemExit(
            f"{name} cursor was not advanced to the post-native-DP fork or a later accepted gate"
        )
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
    ):
        raise SystemExit(
            f"{name} next PR was not advanced to the post-native-DP fork or a later accepted PR"
        )

for phrase in [
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_status",
    "no_go_no_native_dp_certificates",
    "accepted_native_cuda_fasim_dp_engine_consumer",
    "accepted_native_dp_certificate",
    "path_b_native_cuda_fasim_dp_engine_family_stopped",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-consumer-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

target_name = "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-consumer-no-go"
if f"check-fasim-gasal2-roadmap-current-state: {target_name}" not in makefile_text:
    raise SystemExit("current-state aggregate does not include native CUDA Fasim DP consumer no-go target")

print("phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go=recorded")
print("phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_status=no_go_no_native_dp_certificates")
print("path_b_native_cuda_fasim_dp_engine_family_stopped=1")
print("next_valid_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
