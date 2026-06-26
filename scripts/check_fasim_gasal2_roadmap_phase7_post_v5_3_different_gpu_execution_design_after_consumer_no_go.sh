#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md"
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
    "# Fasim GASAL2 Phase 7 Post-v5.3 Different GPU Execution Design After Consumer No-Go",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md",
    "previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go",
    "runtime_default = off",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "current_descriptor_stream_can_prove_output_inert_skips = 0",
    "accepted_pre_drop_output_inert_proof = 0",
    "path_b_current_family_stopped = 1",
    "design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "not_current_descriptor_stream_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "runtime_pr_allowed = 0",
    "requires_fasim_byte_saturation_semantics = 1",
    "requires_scoreinfo_window_of_5_cluster_semantics = 1",
    "requires_scoreinfo_order_equivalence = 1",
    "requires_attempt_order_equivalence = 1",
    "requires_complete_row_set_contract = 1",
    "requires_cpu_authority_replay = 1",
    "selected_replay_attempts",
    "skipped_scoreinfo_group_certificate",
    "skipped_attempt_certificate",
    "fallback_reason_counters",
    "proof_telemetry",
    "endpoint authority",
    "CIGAR authority",
    "traceback authority",
    "final output authority",
    "digest authority",
    "scoreInfo_group_score_upper_bound",
    "scoreInfo_local_break_state",
    "attempt_score_upper_bound",
    "attempt_nt_upper_bound",
    "attempt_identity_upper_bound",
    "attempt_stability_upper_bound",
    "task_output_capacity",
    "task_current_acceptance_frontier",
    "first1_spec_gate_required = 1",
    "certificate field math",
    "first1 checker inputs and expected outputs",
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
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined",
    "path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "path_b_current_descriptor_family_stopped = 1",
    "path_a_user_acceptance_still_allowed = 1",
    "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
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
        "missing different GPU execution design after consumer no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first64_runtime_allowed = 1",
    "runtime_pr_allowed = 1",
    "not_current_descriptor_stream_continuation = 0",
    "not_final_cpu_output_membership_proof = 0",
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
            f"different GPU execution design after consumer no-go doc contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go" not in prev_text:
    raise SystemExit("consumer no-go checkpoint does not point to different design fork")

link = "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link different design after consumer no-go checkpoint")
    if "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance" not in content:
        raise SystemExit(f"{name} does not record the post-consumer spec gate")
    if "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold" not in content:
        raise SystemExit(f"{name} does not record the post-consumer first1 shadow gate")
    if "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go" not in content:
        raise SystemExit(f"{name} does not record the post-consumer first1 shadow consumer no-go gate")
    if "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the GPU-owned scoreInfo consumer spec gate")
    if "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the GPU-owned scoreInfo consumer spec")

for phrase in [
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status",
    "design_defined",
    "path_b_new_design_family",
    "fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-after-consumer-no-go:"
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
if "check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-after-consumer-no-go" not in current_state_line:
    raise SystemExit("current-state aggregate does not include different design after consumer no-go target")

print("phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go=defined")
print("phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status=design_defined")
print("path_b_new_design_family=fasim_compatible_gpu_scoreinfo_frontier_certificate_engine")
print("next_valid_gate=phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
