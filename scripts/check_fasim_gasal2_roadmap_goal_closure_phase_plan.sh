#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])

for path in [doc, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Goal Closure Phase Plan",
    "This document is a closure plan, not a completion claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A: scoped completion",
    "Path B: broad completion",
    "Do not mix Path A evidence into Path B completion.",
    "current_path = Path B",
    "current_phase = Phase 7",
    "current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md",
    "Historical pre-upper-bound-reject-spec cursor:",
    "current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "Historical pre-post-native-DP-fork cursor:",
    "current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "Historical pre-native-DP-fork cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "Historical pre-native-DP-consumer cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "Historical pre-native-DP-shadow cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "Historical pre-native-DP-spec cursor:",
    "current_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "Historical pre-consumer-no-go cursor:",
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "Historical pre-scaffold cursor:",
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md",
    "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go = recorded",
    "current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "runtime_reduction_allowed = 0",
    "runtime_work_drop_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "## Phase Ladder",
    "### Phase 0 - Reproducibility",
    "### Phase 1 - Scope Decision",
    "### Phase 2 - Full-Output Baseline",
    "### Phase 3 - CPU Output-Side Reduction",
    "### Phase 4 - Sort/Top-N Reduction",
    "### Phase 5 - Archive Artifact",
    "### Phase 6 - Workload Matrix",
    "### Phase 7 - Broad GPU Path",
    "### Phase 8 - Closure Decision",
    "## Phase 7 Breakdown",
    "Phase 7.1 - New GPU Engine First1 Shadow or Path A Acceptance",
    "Status:",
    "fail-closed scaffold present",
    "next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance",
    "Phase 7.2 - New Certificate CUDA API",
    "certificate producer first1 synthetic gate present",
    "certificate_producer_active = 1",
    "certificate_valid_before_d2h = 1",
    "certificate_cuda_api_gate_pass = 1",
    "next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go",
    "Phase 7.3 - First1 Reducing Runtime",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md",
    "Phase 7.3B - Real Runtime Certificate Source",
    "source-only checkpoint recorded",
    "real_source_certificate_source_gate_pass = 1",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "runtime_certificate_is_synthetic = 0",
    "source_is_pre_drop = 1",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "runtime_reduction_enabled = 0",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md",
    "design_pre_drop_output_inert_work_drop_proof",
    "Phase 7.3C - Pre-Drop Work-Drop Proof Design",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined",
    "design_only = 1",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md",
    "implement_pre_drop_output_inert_work_drop_proof_first1_shadow",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream",
    "path_b_current_family_stopped = 1",
    "Phase 7.4c - Different GPU Execution Design After Consumer No-Go",
    "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go =",
    "defined",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status =",
    "design_defined",
    "fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "Next valid gate:",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "Phase 7.4d - GPU ScoreInfo Certificate Engine Spec",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance =",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status =",
    "spec_defined",
    "path_b_scoreinfo_certificate_engine_spec_defined = 1",
    "path_b_first1_fail_closed_shadow_scaffold_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "Phase 7.4e - GPU ScoreInfo Certificate Engine First1 Shadow Scaffold",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold =",
    "fail_closed_shadow",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status =",
    "fail_closed_no_runtime_reduction",
    "gate_first1_shadow_pass = 0",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go",
    "Phase 7.4f - GPU ScoreInfo Certificate Engine Consumer No-Go",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md",
    "no_go_no_valid_pre_drop_certificate",
    "accepted_scoreinfo_certificate_engine_consumer = 0",
    "accepted_pre_drop_output_inert_certificate = 0",
    "path_b_scoreinfo_certificate_engine_family_stopped = 1",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "Phase 7.4g - Path A Scope Acceptance Or Different GPU Execution Design After ScoreInfo Cert Engine No-Go",
    "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md",
    "path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined",
    "path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate",
    "next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
    "Phase 7.4 - First1 Proof Shadow",
    "Phase 7.5 - First64 Broad Gate",
    "Phase 7.6 - Scale Gate and Workload-Matrix Promotion",
    "GpuScoreInfoTask",
    "GpuCandidateGroup",
    "GpuReplayAttempt",
    "skipped-work certificate",
    "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW=1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "candidate_wall_seconds < baseline_wall_seconds",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "claimed_broad_replacement_rows > 0",
    "user_scope_acceptance_recorded = 1",
    "scoped_completion_may_close_goal = 1",
    "broad_replacement rows may be added only after Phase 7.5 or larger passes.",
    "The existing v5 CPU-authority replay must not be relabelled as the new GPU engine.",
    "Do not use final CPU output membership as runtime proof.",
    "Do not run first64 from a failed first1 gate.",
    "Only Phase 8 may justify marking the active goal complete.",
    "## Immediate Next Actions",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md",
    "The current proof consumer family is stopped as no-go.",
    "The next Path B artifact must be a different GPU execution design with a new proof source.",
    "make check-fasim-gasal2-roadmap-goal-closure-phase-plan",
    "make check-fasim-gasal2-roadmap-phase-driver",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing goal-closure phase-plan phrase(s):\n" + "\n".join(missing))

phase_order = [
    "### Phase 0 - Reproducibility",
    "### Phase 1 - Scope Decision",
    "### Phase 2 - Full-Output Baseline",
    "### Phase 3 - CPU Output-Side Reduction",
    "### Phase 4 - Sort/Top-N Reduction",
    "### Phase 5 - Archive Artifact",
    "### Phase 6 - Workload Matrix",
    "### Phase 7 - Broad GPU Path",
    "### Phase 8 - Closure Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("goal-closure phase headings are out of order")

phase7_order = [
    "Phase 7.1 - New GPU Engine First1 Shadow or Path A Acceptance",
    "Phase 7.2 - New Certificate CUDA API",
    "Phase 7.3 - First1 Reducing Runtime",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md",
    "Phase 7.3B - Real Runtime Certificate Source",
    "Phase 7.3C - Pre-Drop Work-Drop Proof Design",
    "Phase 7.4 - First1 Proof Shadow",
    "Phase 7.4c - Different GPU Execution Design After Consumer No-Go",
    "Phase 7.4d - GPU ScoreInfo Certificate Engine Spec",
    "Phase 7.5 - First64 Broad Gate",
    "Phase 7.6 - Scale Gate and Workload-Matrix Promotion",
]
phase7_positions = [text.index(heading) for heading in phase7_order]
if phase7_positions != sorted(phase7_positions):
    raise SystemExit("goal-closure Phase 7 subphases are out of order")

for forbidden in [
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "top5-only evidence closes broad objective = 1",
    "archive-only evidence closes broad objective = 1",
    "output-drift speedup counts as success = 1",
    "first64_runtime_allowed = 1",
    "relabel existing v5 replay as new GPU engine = 1",
]:
    if forbidden in text:
        raise SystemExit(f"goal-closure phase plan contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_closure_phase_plan.md"
if link not in roadmap_text:
    raise SystemExit(f"roadmap does not link {link}")

print("goal_closure_phase_plan_document=present")
print("goal_closure_phase_plan_current_phase=phase7")
print("goal_closure_phase_plan_current_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("goal_closure_phase_plan_path_a_requires_user_acceptance=1")
print("goal_closure_phase_plan_path_b_requires_phase7_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
