#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md"
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
    "# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate Design Spec Or Path A Acceptance",
    "phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md",
    "previous_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_gpu_upper_bound_reject_certificate_spec_defined = 1",
    "design_family = gpu_upper_bound_reject_certificate_engine",
    "not_native_cuda_fasim_dp_engine_continuation = 1",
    "not_gasal2_full_align_verifier_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_gpu_owned_scoreinfo_consumer_continuation = 1",
    "not_scoreinfo_certificate_engine_continuation = 1",
    "not_post_v5_3_descriptor_stream_continuation = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "proof_shape = negative_upper_bound_reject_certificate",
    "gpu_accepts_rows = 0",
    "gpu_emits_final_rows = 0",
    "gpu_endpoint_cigar_traceback_required = 0",
    "cpu_authority_replay_required = 1",
    "fallback_to_full_cpu_replay_on_uncertainty = 1",
    "max_possible_nt = sum_base min(query_base_count[base], target_base_count[base])",
    "max_possible_score = max_possible_nt * max_positive_match_score",
    "safe_reject_by_nt = max_possible_nt < required_nt_min",
    "safe_reject_by_score = max_possible_score < required_score_threshold",
    "reject_safe = safe_reject_by_nt or safe_reject_by_score",
    "fallback_on_unsupported_alphabet = 1",
    "fallback_on_ambiguous_bound_uncertainty = 1",
    "fallback_on_unknown_threshold = 1",
    "fallback_on_scoring_config_mismatch = 1",
    "fallback_on_sequence_digest_mismatch = 1",
    "qgram_bound_diagnostic_only = 1",
    "qgram_bound_may_reject_runtime = 0",
    "UpperBoundRejectDescriptor",
    "request_id",
    "group_id",
    "scoreinfo_id",
    "candidate_id",
    "legacy_request_order",
    "translated_query_digest",
    "translated_target_window_digest",
    "target_window_offset",
    "target_window_length",
    "scoring_config_key",
    "required_nt_min",
    "required_score_threshold",
    "output_slot_id",
    "scoreinfo_prealign_group_descriptor",
    "align_candidate_descriptor",
    "requires_scoreinfo_prealign_reduction_plan = 1",
    "requires_align_side_reduction_plan = 1",
    "UpperBoundRejectCertificate",
    "query_base_counts",
    "target_base_counts",
    "certificate_valid_before_scoreinfo_or_align_skip",
    "certificate_consumed_before_scoreinfo_skip = 0",
    "certificate_consumed_before_align_skip = 0",
    "cpu_checker_recomputes_counts = 1",
    "cpu_checker_recomputes_bounds = 1",
    "cpu_checker_does_not_use_final_output_membership = 1",
    "cpu_checker_does_not_use_final_digest_membership = 1",
    "required_env = FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_upper_bound_reject_",
    "upper_bound_descriptors",
    "upper_bound_certificates",
    "reject_candidates_shadow",
    "would_reject_scoreinfo_groups",
    "would_reject_align_attempts",
    "certificate_false_negatives",
    "baseline_rows_in_rejected_groups",
    "baseline_rows_in_rejected_attempts",
    "unsupported_descriptors",
    "fallback_to_full_cpu_replay = 1",
    "full_rows_equal = 1",
    "digest_match = 1",
    "upper_bound_descriptors > 0",
    "upper_bound_certificates > 0",
    "certificate_false_negatives = 0",
    "baseline_rows_in_rejected_groups = 0",
    "baseline_rows_in_rejected_attempts = 0",
    "gate_first1_shadow_pass = 1",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "fallback_accounting_clean = 1",
    "phase7_gpu_upper_bound_reject_certificate_design_spec_status = spec_defined",
    "path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "current_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "no real opt-in",
    "no runtime reduction in this design/spec checkpoint",
    "no runtime work drop in this design/spec checkpoint",
    "no first64 before first1 fail-closed shadow passes",
    "no GPU accept decision",
    "no GPU score authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no GPU output authority",
    "no GPU digest authority",
    "no qgram runtime rejection without a conservative proof",
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
        "missing GPU upper-bound reject certificate spec phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gpu_accepts_rows = 1",
    "gpu_emits_final_rows = 1",
    "qgram_bound_may_reject_runtime = 1",
    "certificate_consumed_before_scoreinfo_skip = 1",
    "certificate_consumed_before_align_skip = 1",
    "path_b_runtime_reduction_pr_allowed = 1",
    "path_b_runtime_work_drop_allowed = 1",
    "path_b_first64_runtime_allowed = 1",
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
        raise SystemExit(
            f"GPU upper-bound reject certificate spec contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go" not in prev_text:
    raise SystemExit("previous post-native-DP fork does not point to the new design/spec gate")

link = "docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md"
next_gate = "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold"
next_pr = "fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold"
advanced_gate = "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go"
advanced_pr = "fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go"
later_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
later_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go"
later_doc = "docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md"
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
        raise SystemExit(f"{name} does not link GPU upper-bound reject certificate spec")
    if f"current_gate_document = {link}" not in content and f"current_gate_document = {later_doc}" not in content:
        raise SystemExit(f"{name} does not link a current or historical GPU upper-bound checkpoint document")
    if (
        f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {next_gate}" not in content
        and f"current_execution_gate = {advanced_gate}" not in content
        and f"current_gate = {advanced_gate}" not in content
        and f"historical_execution_gate = {advanced_gate}" not in content
        and f"current_execution_gate = {later_gate}" not in content
        and f"current_gate = {later_gate}" not in content
    ):
        raise SystemExit(f"{name} cursor was not advanced to the GPU upper-bound first1 shadow gate")
    if (
        f"current_next_pr = {next_pr}" not in content
        and f"current_next_pr = {advanced_pr}" not in content
        and f"historical_next_pr = {advanced_pr}" not in content
        and f"current_next_pr = {later_pr}" not in content
    ):
        raise SystemExit(f"{name} next PR was not advanced to the GPU upper-bound first1 shadow")

for phrase in [
    "phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance",
    "phase7_gpu_upper_bound_reject_certificate_design_spec_status",
    "gpu_upper_bound_reject_certificate_engine",
    "path_b_gpu_upper_bound_reject_certificate_spec_defined",
    "path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
    "fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-design-spec-or-path-a-acceptance:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

if "check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-design-spec-or-path-a-acceptance" not in makefile_text:
    raise SystemExit("Makefile does not register GPU upper-bound reject certificate spec checker")

print("phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance=defined")
print("phase7_gpu_upper_bound_reject_certificate_design_spec_status=spec_defined")
print("path_b_gpu_upper_bound_reject_certificate_spec_defined=1")
print("design_family=gpu_upper_bound_reject_certificate_engine")
print("next_valid_gate=phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold")
print("current_next_pr=fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold")
print("runtime_reduction_enabled=0")
print("runtime_work_drop_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
