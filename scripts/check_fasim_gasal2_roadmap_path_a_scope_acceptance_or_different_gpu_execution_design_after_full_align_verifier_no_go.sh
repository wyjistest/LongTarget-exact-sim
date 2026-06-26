#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md"
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
    "# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After Full-Align Verifier No-Go",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md",
    "previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_full_align_verifier_family_stopped = 1",
    "runtime_default = off",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_full_align_verifier_first1_shadow_active = 1",
    "descriptors > 0",
    "proposals = 0",
    "proposal_failures = descriptors",
    "accepted_full_align_verifier_consumer = 0",
    "accepted_full_align_verifier_certificate = 0",
    "accepted_gasal2_full_align_proposals = 0",
    "consumer_can_drop_align_work = 0",
    "consumer_can_drop_scoreinfo_work = 0",
    "cpu_align_fallbacks = descriptors",
    "fallback_to_full_cpu_replay = 1",
    "gate_first1_shadow_pass = 0",
    "stopped_family = gasal2_full_align_result_with_cpu_verifier_certificate",
    "do_not_continue_descriptor_only_shadow_as_runtime = 1",
    "do_not_relabel_missing_proposals_as_verified = 1",
    "do_not_run_first64_from_failed_first1_consumer = 1",
    "do_not_promote_broad_replacement_row_from_this_family = 1",
    "missing_gasal2_full_align_proposals = 1",
    "missing_verified_full_align_certificate = 1",
    "missing_output_inert_skip_proof = 1",
    "missing_scoreinfo_work_drop = 1",
    "missing_align_side_work_drop = 1",
    "path_b_different_gpu_execution_design_required = 1",
    "path_b_different_gpu_execution_design_defined = 1",
    "design_family = native_cuda_fasim_dp_certificate_engine",
    "not_gasal2_full_align_verifier_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_gpu_owned_scoreinfo_consumer_continuation = 1",
    "not_scoreinfo_certificate_engine_continuation = 1",
    "not_post_v5_3_descriptor_stream_continuation = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "runtime_pr_allowed = 0",
    "native_cuda_fasim_byte_scoreinfo = 1",
    "native_cuda_fasim_forward_reverse_trace_witness = 1",
    "native_cuda_fasim_cigar_witness = 1",
    "certificate_produced_before_work_drop = 1",
    "certificate_consumed_before_cpu_align_skip = 1",
    "fallback_to_full_cpu_replay_on_uncertainty = 1",
    "requires_fasim_byte_saturation_semantics = 1",
    "requires_scoreinfo_window_of_5_cluster_semantics = 1",
    "requires_scoreinfo_order_equivalence = 1",
    "requires_attempt_order_equivalence = 1",
    "requires_local_max_tie_policy_equivalence = 1",
    "requires_reverse_start_equivalence = 1",
    "requires_traceback_cigar_equivalence = 1",
    "requires_complete_row_set_contract = 1",
    "requires_cpu_authority_replay = 1",
    "score authority",
    "endpoint authority",
    "CIGAR authority",
    "traceback authority",
    "final output authority",
    "digest authority",
    "next_valid_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "native_scoreinfo_byte_dp_layout",
    "native_forward_score_endpoint_layout",
    "native_reverse_start_layout",
    "native_traceback_cigar_witness_layout",
    "pre_drop_certificate_field_math",
    "consumer_decision_point_before_cpu_align_skip",
    "fallback_accounting_schema",
    "first1_shadow_inputs",
    "first1_shadow_expected_telemetry",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status = design_defined",
    "path_b_new_design_family_after_full_align_verifier_no_go = native_cuda_fasim_dp_certificate_engine",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "current_execution_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
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
        "missing path-a-or-different-design-after-full-align-verifier-no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "runtime_pr_allowed = 1",
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
        raise SystemExit(
            "full-align-verifier fork doc contains forbidden phrase: "
            f"{forbidden}"
        )

if "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go" not in prev_text:
    raise SystemExit("full-align verifier consumer no-go does not point to this fork")

link = "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md"
next_gate = "phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance"
next_pr = "fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link full-align-verifier fork checkpoint")
    if f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the native CUDA Fasim DP spec gate")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the native CUDA Fasim DP spec")

for phrase in [
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go",
    "path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status",
    "design_defined",
    "native_cuda_fasim_dp_certificate_engine",
    "phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-full-align-verifier-no-go:"
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
if "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-full-align-verifier-no-go" not in current_state_line:
    raise SystemExit("current-state aggregate does not include full-align-verifier fork target")

print("path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go=recorded")
print("path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status=design_defined")
print("path_b_new_design_family_after_full_align_verifier_no_go=native_cuda_fasim_dp_certificate_engine")
print("next_valid_gate=phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance")
print("current_next_pr=fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance")
print("runtime_reduction_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
