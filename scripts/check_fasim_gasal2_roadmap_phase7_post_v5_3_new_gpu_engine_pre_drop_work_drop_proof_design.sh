#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    current_state,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    current_state,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_text = phase_plan.read_text(encoding="utf-8")
canonical_text = canonical.read_text(encoding="utf-8")
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Pre-Drop Work-Drop Proof Design",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined",
    "design_only = 1",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md",
    "previous_gate = design_pre_drop_output_inert_work_drop_proof",
    "real_source_certificate_source_gate_pass = 1",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "runtime_certificate_is_synthetic = 0",
    "source_is_pre_drop = 1",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "proof_must_be_pre_drop = 1",
    "proof_must_be_output_inert = 1",
    "proof_must_not_use_final_cpu_output_membership = 1",
    "proof_must_not_use_top5_only_contract = 1",
    "proof_must_cover_complete_row_set = 1",
    "certificate_production_separate_from_consumption = 1",
    "consumer_must_fail_closed = 1",
    "fallback_to_full_cpu_replay = 1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "required_future_telemetry:",
    "uses_pre_drop_output_inert_proof",
    "candidate_proof_false_negatives",
    "candidate_proof_missing_required_attempts",
    "candidate_uses_final_cpu_output_as_runtime_proof",
    "gate_first1_proof_pass",
    "scoreInfo_prealign_reduced",
    "align_side_reduced",
    "full_rows_equal",
    "digest_match",
    "next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow",
    "current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing pre-drop work-drop proof design phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "design_only = 0",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "proof_must_not_use_final_cpu_output_membership = 0",
    "proof_must_not_use_top5_only_contract = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"pre-drop work-drop proof design doc contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md"
for source_name, source_text in [
    ("roadmap", roadmap_text),
    ("phase-to-completion plan", phase_text),
    ("canonical phase plan", canonical_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
]:
    if link not in source_text:
        raise SystemExit(f"{source_name} does not link {link}")

for source_name, source_text in [
    ("phase-to-completion plan", phase_text),
    ("canonical phase plan", canonical_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
]:
    if (
        "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance"
        not in source_text
    ):
        raise SystemExit(f"{source_name} no longer records the current GPU-owned scoreInfo consumer spec cursor")
    if (
        "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance"
        not in source_text
    ):
        raise SystemExit(f"{source_name} no longer records the current GPU-owned scoreInfo consumer spec PR")
    if "first64_runtime_allowed = 0" not in source_text:
        raise SystemExit(f"{source_name} must keep first64 disabled")
    if "runtime_reduction_enabled = 0" not in source_text and "runtime_reduction_allowed = 0" not in source_text:
        raise SystemExit(f"{source_name} must keep runtime reduction disabled")

for source_name, source_text in [
    ("phase-to-completion plan", phase_text),
    ("canonical phase plan", canonical_text),
    ("goal closure phase plan", closure_text),
]:
    if "implement_pre_drop_output_inert_work_drop_proof_first1_shadow" not in source_text:
        raise SystemExit(f"{source_name} no longer records the first1 proof shadow gate")

for phrase in [
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_status",
    "current_execution_gate",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "current_next_pr",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design:"
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
if "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design" not in current_state_line:
    raise SystemExit("current-state aggregate does not include pre-drop work-drop proof design target")

print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design=defined")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_status=design_only")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_runtime_reduction_enabled=0")
print("phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_next_gate=implement_pre_drop_output_inert_work_drop_proof_first1_shadow")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
