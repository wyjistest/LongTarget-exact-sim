#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md"
PHASE_DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$PREV" "$PHASE_DRIVER" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev = Path(sys.argv[2])
phase_driver = Path(sys.argv[3])
roadmap = Path(sys.argv[4])

for path in [doc, prev, phase_driver, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Different GPU Execution Design Or Scope Acceptance",
    "phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md",
    "previous_gate = different_gpu_execution_design_or_path_a_scope_acceptance",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "current_descriptor_stream_can_prove_output_inert_skips = 0",
    "accepted_pre_d2h_proof_families = 0",
    "Do not reuse the current PreAlignCudaAttemptDescriptor-only stream.",
    "Do not reuse aggregate proof-search export as runtime proof.",
    "Do not use final CPU output membership as runtime proof.",
    "## Designs Reviewed",
    "### Design A: GPU-resident scoreInfo plus conservative skip certificate",
    "### Design B: GPU full scoreInfo/Align-compatible engine with CPU authority replay",
    "### Design C: Scoped product acceptance path",
    "requires_new_cuda_kernel_family = 1",
    "requires_new_certificate_fields = 1",
    "requires_scoreInfo_compatible_semantics = 1",
    "requires_align_side_reduction = 1",
    "requires_full_row_digest_equality = 1",
    "current_code_can_implement_safely_now = 0",
    "path_a_user_acceptance_required = 1",
    "path_b_different_gpu_execution_design_required = 1",
    "path_b_current_implementation_available = 0",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_only_design_allowed = 1",
    "next_valid_work = path_a_scoped_acceptance_or_new_engine_design_doc",
    "current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "CPU aligner.Align() authority = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing different GPU execution design checkpoint phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first64_runtime_allowed = 1",
    "path_b_current_implementation_available = 1",
    "path_b_runtime_pr_allowed = 1",
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
            "different GPU execution design checkpoint contains forbidden phrase: "
            + forbidden
        )

previous_text = prev.read_text(encoding="utf-8")
if "different_gpu_execution_design_required = 1" not in previous_text:
    raise SystemExit("previous checkpoint no longer requires a different GPU design")

link = "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md"
for path in [phase_driver, roadmap]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link different GPU design checkpoint")

print("phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance=recorded")
print("path_a_user_acceptance_required=1")
print("path_b_different_gpu_execution_design_required=1")
print("path_b_current_implementation_available=0")
print("path_b_runtime_pr_allowed=0")
print("next_valid_work=path_a_scoped_acceptance_or_new_engine_design_doc")
print("current_next_pr=fasim_path_a_scope_acceptance_or_new_gpu_engine_design")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
