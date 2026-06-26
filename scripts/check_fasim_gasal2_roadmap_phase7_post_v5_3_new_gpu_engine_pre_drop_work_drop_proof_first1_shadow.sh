#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc, prev, roadmap, phase_plan, current_state, makefile = [
    Path(arg) for arg in sys.argv[1:]
]
for path in [doc, prev, roadmap, phase_plan, current_state, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_text = phase_plan.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Pre-Drop Work-Drop Proof First1 Shadow",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow = fail_closed_shadow",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md",
    "previous_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow",
    "required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_PRE_DROP_WORK_DROP_PROOF_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_",
    "real_fasim_runtime_certificate_source = 1",
    "uses_pre_drop_output_inert_proof = 0",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "real_fasim_runtime_work_drop_path = 0",
    "candidate_uses_final_cpu_output_as_runtime_proof = 0",
    "proof_must_not_use_top5_only_contract = 1",
    "proof_must_cover_complete_row_set = 1",
    "fallback_to_full_cpu_replay = 1",
    "candidate_proof_false_negatives = 0",
    "candidate_proof_missing_required_attempts = 0",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "fallback_accounting_clean = 0",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "full_rows_equal = 0",
    "digest_match = 0",
    "gate_first1_proof_pass = 0",
    "gate_first1_pass = 0",
    "next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go",
    "current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing pre-drop proof first1 shadow phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "uses_pre_drop_output_inert_proof = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "real_fasim_runtime_work_drop_path = 1",
    "candidate_uses_final_cpu_output_as_runtime_proof = 1",
    "fallback_accounting_clean = 1",
    "gate_first1_proof_pass = 1",
    "gate_first1_pass = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"pre-drop proof first1 shadow doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow" not in prev_text:
    raise SystemExit("previous design doc no longer points to first1 proof shadow")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md"
if link not in roadmap_text:
    raise SystemExit("roadmap does not link pre-drop proof first1 shadow checkpoint")
if link not in phase_text:
    raise SystemExit("phase-to-completion plan does not link pre-drop proof first1 shadow checkpoint")
if "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go" not in phase_text:
    raise SystemExit("phase-to-completion plan no longer records the after-consumer no-go next gate")
if (
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance"
    not in phase_text
):
    raise SystemExit("phase-to-completion plan no longer records the current GPU-owned scoreInfo consumer spec cursor")

for phrase in [
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_status",
    "current_execution_gate",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "current_next_pr",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow:"
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
if "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow" not in current_state_line:
    raise SystemExit("current-state aggregate does not include pre-drop proof first1 shadow target")

print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow=fail_closed_shadow")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled=0")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass=0")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_next_gate=implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
