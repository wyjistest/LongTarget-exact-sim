#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md"

python3 - "$DOC" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
if not doc.exists():
    raise SystemExit(f"missing required file: {doc}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Pre-D2H Output-Inert Proof Acceptance First1",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = no_go",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_status = first1_no_accepted_proof",
    "proof_search_rows = 2872",
    "task_count = 48",
    "scoreinfo_count = 718",
    "attempt_count = 2872",
    "accepted_pre_d2h_proof_families = 0",
    "candidate_proof_false_negatives = not_zero_or_unproven",
    "candidate_proof_missing_required_attempts = not_zero_or_unproven",
    "candidate_selected_attempts_lt_v5_candidate_align_attempts = unproven",
    "candidate_selected_attempts_lt_reference_align_attempts = unproven",
    "candidate_uses_final_cpu_output_as_runtime_proof = forbidden",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "reducing_runtime_allowed = 0",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "gpu_output_authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "current_execution_gate = new_pre_d2h_proof_family_or_path_a_scope_decision",
    "current_next_pr = fasim_design_new_pre_d2h_proof_family_or_scope_decision",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing proof-acceptance phrase(s):\n" + "\n".join(missing))

for forbidden in [
    "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = pass",
    "accepted_pre_d2h_proof_families = 1",
    "runtime_reduction_enabled = 1",
    "first64_runtime_allowed = 1",
    "reducing_runtime_allowed = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 1",
    "gpu_output_authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"proof-acceptance checkpoint contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1=no_go")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_status=first1_no_accepted_proof")
print("accepted_pre_d2h_proof_families=0")
print("reducing_runtime_allowed=0")
print("first64_runtime_allowed=0")
print("current_execution_gate=new_pre_d2h_proof_family_or_path_a_scope_decision")
print("current_next_pr=fasim_design_new_pre_d2h_proof_family_or_scope_decision")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
