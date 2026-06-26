#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md"
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
    "# Fasim GASAL2 Phase 7 Post-Consumer GPU ScoreInfo Certificate Engine Spec Or Path A Acceptance",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md",
    "previous_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_scoreinfo_certificate_engine_spec_defined = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "runtime_reduction_pr_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "not_current_descriptor_stream_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "cpu_align_authority_required = 1",
    "requires_fasim_byte_saturation_semantics = 1",
    "requires_scoreinfo_window_of_5_cluster_semantics = 1",
    "requires_scoreinfo_order_equivalence = 1",
    "requires_attempt_order_equivalence = 1",
    "requires_complete_row_set_contract = 1",
    "requires_cpu_authority_replay = 1",
    "ScoreInfoCertificateQuery",
    "ScoreInfoCertificateTargetWindow",
    "ScoreInfoCertificateTask",
    "GpuScoreInfoGroup",
    "GpuAttemptFrontier",
    "scoreInfo_group_score_upper_bound",
    "scoreInfo_local_break_state",
    "attempt_score_upper_bound",
    "attempt_nt_upper_bound",
    "attempt_identity_upper_bound",
    "attempt_stability_upper_bound",
    "certificate_valid_before_work_drop = 1",
    "certificate_valid_before_d2h = 1",
    "certificate_uses_final_cpu_output_membership = 0",
    "certificate_uses_final_digest = 0",
    "certificate_uses_top5_only_membership = 0",
    "certificate_covers_complete_row_set = 1",
    "SkippedScoreInfoGroupCertificate",
    "SkippedAttemptCertificate",
    "task_current_acceptance_frontier",
    "task_output_capacity",
    "output_inert_if_skipped",
    "first1_fail_closed_shadow_scaffold_allowed = 1",
    "fallback_to_full_cpu_replay = 1",
    "FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW=1",
    "scoreinfo_cert_engine_requested",
    "scoreinfo_cert_engine_active",
    "scoreinfo_cert_engine_first1_shadow",
    "gpu_scoreinfo_groups",
    "gpu_attempt_frontier_attempts",
    "gpu_selected_replay_attempts",
    "gpu_skipped_scoreinfo_groups",
    "gpu_skipped_attempts",
    "cpu_replay_attempts",
    "baseline_cpu_attempts",
    "scoreInfo_prealign_reduced",
    "align_side_reduced",
    "certificate_false_negatives",
    "missing_required_attempts",
    "fallback_reason_counts",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "full_rows_equal",
    "digest_match",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "scoreinfo_cert_engine_active = 1",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status = spec_defined",
    "path_b_first1_fail_closed_shadow_scaffold_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing post-consumer scoreInfo certificate engine spec phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "runtime_reduction_pr_allowed = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "not_current_descriptor_stream_continuation = 0",
    "not_gasal2_align_replacement = 0",
    "not_final_cpu_output_membership_proof = 0",
    "not_top5_only_contract = 0",
    "certificate_uses_final_cpu_output_membership = 1",
    "certificate_uses_final_digest = 1",
    "certificate_uses_top5_only_membership = 1",
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
            f"post-consumer scoreInfo certificate engine spec contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous different-GPU-design checkpoint does not point to this spec gate")

link = "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link post-consumer scoreInfo certificate engine spec")
    if "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold" not in content:
        raise SystemExit(f"{name} does not record the first1 shadow scaffold gate")
    if "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go" not in content:
        raise SystemExit(f"{name} does not record the first1 shadow consumer no-go gate")
    if "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the GPU-owned scoreInfo consumer spec gate")
    if "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the GPU-owned scoreInfo consumer spec")

for phrase in [
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status",
    "spec_defined",
    "path_b_scoreinfo_certificate_engine_spec_defined",
    "path_b_first1_fail_closed_shadow_scaffold_allowed",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-spec-or-path-a-acceptance:"
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
target_name = "check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-spec-or-path-a-acceptance"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include scoreInfo certificate engine spec target")

print("phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance=defined")
print("phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status=spec_defined")
print("path_b_scoreinfo_certificate_engine_spec_defined=1")
print("path_b_first1_fail_closed_shadow_scaffold_allowed=1")
print("next_valid_gate=phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
