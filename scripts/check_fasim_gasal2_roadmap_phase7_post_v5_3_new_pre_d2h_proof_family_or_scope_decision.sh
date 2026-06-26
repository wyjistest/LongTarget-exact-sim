#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md"

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
    "# Fasim GASAL2 Phase 7 Post-v5.3 New Pre-D2H Proof Family Or Scope Decision",
    "phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md",
    "previous_status = first1_no_accepted_proof",
    "path_a_user_acceptance_required = 1",
    "path_b_new_pre_d2h_proof_family_required = 1",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "gpu_output_authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "candidate_proof_false_negatives = 0",
    "candidate_proof_missing_required_attempts = 0",
    "candidate_selected_attempts < v5_candidate_align_attempts",
    "candidate_selected_attempts < reference_align_attempts",
    "candidate_uses_final_cpu_output_as_runtime_proof = 0",
    "source_is_pre_scoreinfo = 1",
    "source_is_legacy_byte_cuda = 1",
    "CPU aligner.Align() authority = 1",
    "do_not_reuse_failed_proof_search_aggregate_export = 1",
    "do_not_use_final_cpu_output_as_runtime_proof = 1",
    "runtime reduction = forbidden",
    "first64 runtime = forbidden",
    "broad_replacement workload matrix promotion = forbidden",
    "current_execution_gate = implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance",
    "current_next_pr = fasim_new_pre_d2h_proof_family_first1_smoke_or_scope_acceptance",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing new proof-family phrase(s):\n" + "\n".join(missing))

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first64_runtime_allowed = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 1",
    "gpu_output_authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
    "candidate_uses_final_cpu_output_as_runtime_proof = 1",
    "source_is_pre_scoreinfo = 0",
    "source_is_legacy_byte_cuda = 0",
]:
    if forbidden in text:
        raise SystemExit(f"new proof-family checkpoint contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision=defined")
print("path_a_user_acceptance_required=1")
print("path_b_new_pre_d2h_proof_family_required=1")
print("runtime_reduction_enabled=0")
print("first64_runtime_allowed=0")
print("current_execution_gate=implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance")
print("current_next_pr=fasim_new_pre_d2h_proof_family_first1_smoke_or_scope_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
