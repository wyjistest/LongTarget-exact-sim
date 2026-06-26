#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md"
DECISION="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md"
PHASE_EXEC="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$DECISION" "$PHASE_EXEC" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
decision = Path(sys.argv[2])
phase_exec = Path(sys.argv[3])
roadmap = Path(sys.argv[4])

for path in [doc, decision, phase_exec, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New Pre-D2H Proof Family First1 Feasibility No-Go",
    "phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md",
    "previous_gate = implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance",
    "current_descriptor_stream = PreAlignCudaAttemptDescriptor",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "taskIndex",
    "scoreInfoPosition",
    "scoreInfoScore",
    "scoreInfoOrder",
    "attemptOrder",
    "targetStart",
    "cutlength",
    "targetEndRequiredForFallback",
    "ntMinLength",
    "scoringConfigKey",
    "overflowFlag",
    "skipped_scoreinfo_score_upper_bound = missing",
    "skipped_attempt_score_upper_bound = missing",
    "skipped_attempt_nt_upper_bound = missing",
    "skipped_attempt_identity_upper_bound = missing",
    "skipped_attempt_stability_upper_bound = missing",
    "task_output_capacity = missing",
    "scoreInfo-local break-state = missing",
    "current_descriptor_stream_can_prove_output_inert_skips = 0",
    "accepted_pre_d2h_proof_families = 0",
    "candidate_proof_false_negatives = unproven",
    "candidate_proof_missing_required_attempts = unproven",
    "candidate_selected_attempts_lt_v5_candidate_align_attempts = unproven",
    "candidate_selected_attempts_lt_reference_align_attempts = unproven",
    "candidate_uses_final_cpu_output_as_runtime_proof = forbidden",
    "new_pre_d2h_proof_family_first1_smoke_allowed = 0",
    "reducing_runtime_allowed = 0",
    "do_not_implement_reducing_runtime_from_current_descriptor_stream = 1",
    "do_not_run_first64_from_current_descriptor_stream = 1",
    "different_gpu_execution_design_required = 1",
    "path_a_user_acceptance_required = 1",
    "current_execution_gate = different_gpu_execution_design_or_path_a_scope_acceptance",
    "current_next_pr = fasim_design_different_gpu_execution_design_or_scope_acceptance",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new pre-D2H proof-family feasibility no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first64_runtime_allowed = 1",
    "new_pre_d2h_proof_family_first1_smoke_allowed = 1",
    "do_not_implement_reducing_runtime_from_current_descriptor_stream = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"new proof-family feasibility checkpoint contains forbidden phrase: {forbidden}")

support = decision.read_text(encoding="utf-8")
if "path_b_new_pre_d2h_proof_family_required = 1" not in support:
    raise SystemExit("decision checkpoint no longer records the previous Path B requirement")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md"
for path in [phase_exec, roadmap]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link new feasibility no-go checkpoint")

print("phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go=recorded")
print("current_descriptor_stream_can_prove_output_inert_skips=0")
print("new_pre_d2h_proof_family_first1_smoke_allowed=0")
print("different_gpu_execution_design_required=1")
print("path_a_user_acceptance_required=1")
print("current_execution_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("current_next_pr=fasim_design_different_gpu_execution_design_or_scope_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
