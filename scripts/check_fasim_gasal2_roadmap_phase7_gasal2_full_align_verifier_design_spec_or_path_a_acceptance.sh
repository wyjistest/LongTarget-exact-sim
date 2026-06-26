#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md"
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
    "# Fasim GASAL2 Phase 7 Full-Align Verifier Design Spec Or Path A Acceptance",
    "phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md",
    "previous_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_full_align_verifier_spec_defined = 1",
    "path_b_design_family = gasal2_full_align_result_with_cpu_verifier_certificate",
    "path_b_differs_from_gpu_owned_scoreinfo_consumer = 1",
    "path_b_differs_from_scoreinfo_certificate_engine = 1",
    "path_b_differs_from_post_v5_3_descriptor_stream = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "GASAL2 produces untrusted full-align proposal data.",
    "CPU verifier checks the proposal before CPU Align work can be skipped.",
    "CPU aligner.Align() remains the shadow and fallback authority.",
    "FullAlignVerifierRequest",
    "request_id",
    "translated_query_digest",
    "translated_target_window_digest",
    "scoreinfo_group_id",
    "candidate_id",
    "legacy_request_order",
    "descriptor_uses_final_cpu_output_membership = 0",
    "descriptor_uses_final_digest = 0",
    "Gasal2FullAlignProposal",
    "proposal_status",
    "proposal_fallback_reason",
    "score",
    "ref_end",
    "query_end",
    "ref_start",
    "query_start",
    "cigar_op_count",
    "cigar_bytes",
    "traceback_status",
    "local_max_witness",
    "reverse_start_witness",
    "proposal_score_authority = 0",
    "proposal_endpoint_authority = 0",
    "proposal_cigar_authority = 0",
    "proposal_traceback_authority = 0",
    "proposal_output_authority = 0",
    "proposal_digest_authority = 0",
    "FullAlignVerifierCertificate",
    "proposal_verified",
    "verifier_failure_reason",
    "local_max_witness_verified",
    "reverse_start_witness_verified",
    "traceback_cigar_witness_verified",
    "coordinate_convention_verified",
    "row_identity_linkage_verified",
    "score_match_vs_cpu_align",
    "endpoint_match_vs_cpu_align",
    "cigar_match_vs_cpu_align",
    "full_row_match_vs_cpu_align",
    "digest_match_vs_cpu_align",
    "verifier_failure_means_cpu_align_fallback = 1",
    "certificate_consumed_before_cpu_align_skip = 0",
    "certificate_consumed_before_cpu_replay_selection = 0",
    "verifier_failure_reason:",
    "score_mismatch",
    "endpoint_mismatch",
    "reverse_start_mismatch",
    "cigar_mismatch",
    "traceback_witness_mismatch",
    "row_identity_mismatch",
    "required_env = FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_full_align_verifier_",
    "descriptors",
    "proposals",
    "proposal_failures",
    "verifier_pass",
    "verifier_fail",
    "cpu_align_fallbacks",
    "score_mismatches",
    "endpoint_mismatches",
    "cigar_mismatches",
    "full_row_mismatches",
    "digest_mismatches",
    "gpu_endpoint_cigar_traceback_output_authority",
    "gpu_output_digest_authority",
    "requested = 1",
    "active = 1",
    "proposals > 0",
    "verifier_pass > 0 or verifier failure taxonomy complete",
    "score_mismatches = 0",
    "endpoint_mismatches = 0",
    "cigar_mismatches = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "gate_first1_shadow_pass = 1",
    "uses_cpu_verifier_certificate = 1",
    "verifier_consumed_before_cpu_align_skip = 1",
    "candidate_align_attempts < reference_align_attempts",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "fallback_accounting_clean = 1",
    "score, endpoint, CIGAR, full row, or digest drift appears",
    "the CPU verifier cannot prove the proposal without rerunning full CPU Align",
    "phase7_full_align_verifier_design_spec_status = spec_defined",
    "path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "current_execution_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "no real opt-in",
    "no runtime reduction in this design/spec checkpoint",
    "no runtime work drop in this design/spec checkpoint",
    "no first64 before first1 fail-closed shadow passes",
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
        "missing full-align verifier design/spec phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 1",
    "path_b_runtime_work_drop_allowed = 1",
    "path_b_first64_runtime_allowed = 1",
    "path_b_differs_from_gpu_owned_scoreinfo_consumer = 0",
    "path_b_differs_from_scoreinfo_certificate_engine = 0",
    "path_b_differs_from_post_v5_3_descriptor_stream = 0",
    "proposal_score_authority = 1",
    "proposal_endpoint_authority = 1",
    "proposal_cigar_authority = 1",
    "proposal_traceback_authority = 1",
    "proposal_output_authority = 1",
    "proposal_digest_authority = 1",
    "certificate_consumed_before_cpu_align_skip = 1",
    "certificate_consumed_before_cpu_replay_selection = 1",
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
            f"full-align verifier design/spec contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous fork checkpoint does not point to full-align verifier spec")

link = "docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md"
next_gate = "phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold"
next_pr = "fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold"
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
        raise SystemExit(f"{name} does not link full-align verifier design/spec")
    if f"current_gate = {next_gate}" not in content and f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the full-align verifier first1 shadow gate")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the full-align verifier first1 shadow")

for phrase in [
    "phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "phase7_full_align_verifier_design_spec_status",
    "path_b_full_align_verifier_spec_defined",
    "path_b_full_align_verifier_first1_fail_closed_shadow_allowed",
    "phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance:"
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
target_name = "check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include full-align verifier design/spec target")

print("phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance=defined")
print("phase7_full_align_verifier_design_spec_status=spec_defined")
print("path_b_full_align_verifier_spec_defined=1")
print("path_b_full_align_verifier_first1_fail_closed_shadow_allowed=1")
print("next_valid_gate=phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold")
print("current_next_pr=fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
