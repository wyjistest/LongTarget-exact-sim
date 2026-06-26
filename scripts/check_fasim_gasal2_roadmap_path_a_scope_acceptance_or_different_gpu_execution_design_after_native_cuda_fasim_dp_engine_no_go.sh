#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md"
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
    "# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After Native CUDA Fasim DP Engine No-Go",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md",
    "previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_native_cuda_fasim_dp_engine_family_stopped = 1",
    "path_b_different_gpu_execution_design_required = 1",
    "path_b_different_gpu_execution_design_defined = 0",
    "runtime_default = off",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "native_scoreinfo_tiles > 0",
    "forward_endpoint_witnesses = 0",
    "reverse_start_witnesses = 0",
    "traceback_cigar_witnesses = 0",
    "certificates = 0",
    "missing_required_attempts = native_scoreinfo_tiles",
    "cpu_align_fallbacks = native_scoreinfo_tiles",
    "fallback_to_full_cpu_replay = 1",
    "accepted_native_cuda_fasim_dp_engine_consumer = 0",
    "accepted_native_dp_certificate = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "gate_first1_shadow_pass = 0",
    "stopped_family = native_cuda_fasim_dp_certificate_engine",
    "do_not_continue_native_dp_shadow_as_runtime = 1",
    "do_not_relabel_native_scoreinfo_tiles_as_certificates = 1",
    "do_not_run_first64_from_failed_first1_consumer = 1",
    "do_not_promote_broad_replacement_row_from_this_family = 1",
    "stopped_prior_families:",
    "post_v5_3_descriptor_stream",
    "scoreinfo_certificate_engine",
    "gpu_owned_scoreinfo_consumer",
    "gasal2_full_align_result_with_cpu_verifier_certificate",
    "native_cuda_fasim_dp_certificate_engine",
    "missing_valid_pre_drop_certificate = 1",
    "missing_complete_row_safe_work_drop = 1",
    "missing_scoreinfo_work_drop = 1",
    "missing_align_side_work_drop = 1",
    "missing_first1_runtime_reduction_gate = 1",
    "missing_first64_broad_gate = 1",
    "path_b_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go_status = required_not_defined",
    "path_b_new_design_family_after_native_cuda_fasim_dp_engine_no_go = undefined",
    "path_b_new_design_family_spec_required = 1",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "not_native_cuda_fasim_dp_engine_continuation = 1",
    "not_gasal2_full_align_verifier_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_gpu_owned_scoreinfo_consumer_continuation = 1",
    "not_scoreinfo_certificate_engine_continuation = 1",
    "not_post_v5_3_descriptor_stream_continuation = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "requires_pre_drop_complete_row_safe_certificate_source = 1",
    "requires_scoreinfo_prealign_reduction_plan = 1",
    "requires_align_side_reduction_plan = 1",
    "requires_fallback_accounting_schema = 1",
    "requires_first1_shadow_inputs = 1",
    "requires_first1_shadow_expected_telemetry = 1",
    "requires_first64_broad_gate_plan = 1",
    "no real opt-in",
    "no default behavior change",
    "no runtime work drop",
    "no first64 before first1 passes",
    "no promotion of the stopped native-DP family",
    "no promotion of stopped earlier Path B families",
    "no GPU score authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no GPU output authority",
    "no GPU digest authority",
    "no completion claim from this checkpoint",
    "next_valid_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "current_execution_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
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
        "missing post-native-DP fork phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_different_gpu_execution_design_defined = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "path_b_runtime_pr_allowed = 1",
    "not_native_cuda_fasim_dp_engine_continuation = 0",
    "not_gasal2_full_align_verifier_continuation = 0",
    "not_gasal2_align_replacement = 0",
    "not_gpu_owned_scoreinfo_consumer_continuation = 0",
    "not_scoreinfo_certificate_engine_continuation = 0",
    "not_post_v5_3_descriptor_stream_continuation = 0",
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
        raise SystemExit(f"post-native-DP fork doc contains forbidden phrase: {forbidden}")

old_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
old_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
next_gate = "new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go"
next_pr = "fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go"
advanced_gate = "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold"
advanced_pr = "fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold"
advanced_doc = (
    "docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md"
)

if f"next_valid_gate = {old_gate}" not in prev_text:
    raise SystemExit("native CUDA Fasim DP consumer no-go does not point to this fork")
if f"current_next_pr = {old_pr}" not in prev_text:
    raise SystemExit("native CUDA Fasim DP consumer no-go does not name this fork PR")

link = "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md"
gate_doc = f"current_gate_document = {link}"
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
        raise SystemExit(f"{name} does not link post-native-DP fork checkpoint")
    if gate_doc not in content and f"current_gate_document = {advanced_doc}" not in content:
        raise SystemExit(
            f"{name} does not set current gate document to the post-native-DP fork or a later accepted spec"
        )
    if (
        f"current_gate = {next_gate}" not in content
        and f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
    ):
        raise SystemExit(
            f"{name} cursor was not advanced to the post-native-DP next design/spec gate or a later accepted gate"
        )
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
    ):
        raise SystemExit(
            f"{name} next PR was not advanced to the post-native-DP next design/spec gate or a later accepted PR"
        )

for phrase in [
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "path_b_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go_status",
    "required_not_defined",
    "path_b_new_design_family_after_native_cuda_fasim_dp_engine_no_go",
    "undefined",
    next_gate,
    next_pr,
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-native-cuda-fasim-dp-engine-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

if "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-native-cuda-fasim-dp-engine-no-go" not in makefile_text:
    raise SystemExit("Makefile does not register post-native-DP fork checker")

print("path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go=recorded")
print("path_b_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go_status=required_not_defined")
print("path_b_new_design_family_after_native_cuda_fasim_dp_engine_no_go=undefined")
print(f"next_valid_gate={next_gate}")
print(f"current_next_pr={next_pr}")
print("runtime_reduction_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
