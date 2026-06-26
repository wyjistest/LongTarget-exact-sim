#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ROADMAP" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
makefile = Path(sys.argv[3])

for path in [doc, roadmap, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Goal Completion Canonical Phase Plan",
    "This document is the execution entry point for closing the active Fasim/GASAL2 goal.",
    "It is a plan, not a completion claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A: scoped product completion",
    "Path B: broad objective completion",
    "Do not mix the paths.",
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
    "runtime_pr_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "certificate_producer_active = 1",
    "certificate_valid_before_d2h = 1",
    "runtime_reduction_enabled = 0",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "default behavior unchanged = 1",
    "top5-only evidence closes broad objective = 0",
    "archive-only evidence closes broad objective = 0",
    "output-drift speedup counts as success = 0",
    "fallback-heavy evidence counts as GPU-fast-path clean = 0",
    "existing v5 CPU-authority replay relabelled as new engine = 0",
    "final CPU output membership used as runtime proof = 0",
    "## Phase Summary",
    "## Phase 0 - Reproducibility",
    "## Phase 1 - Scoped Product Decision",
    "## Phase 2 - Full-Output Baseline",
    "## Phase 3 - CPU Output-Side Reduction",
    "## Phase 4 - Sort/Top-N Reduction",
    "## Phase 5 - Archive Artifact",
    "## Phase 6 - Workload Matrix",
    "## Phase 7 - Broad GPU Path",
    "## Phase 8 - Close Decision",
    "### Phase 7.1 - New GPU Engine First1 Spec And Shadow",
    "### Phase 7.2 - Certificate CUDA API Producer",
    "### Phase 7.3 - First1 Reducing Runtime",
    "This gate is a no-go for the current certificate-producer line.",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md",
    "path_b_real_source_design_checkpoint_defined = 1",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md",
    "path_b_real_source_first1_spec_defined = 1",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md",
    "real_source_certificate_source_gate_pass = 1",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "runtime_certificate_is_synthetic = 0",
    "source_is_pre_drop = 1",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "next_valid_gate = design_pre_drop_output_inert_work_drop_proof",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined",
    "design_only = 1",
    "next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md",
    "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream",
    "path_b_current_family_stopped = 1",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go",
    "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined",
    "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined",
    "path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine",
    "path_b_runtime_pr_allowed = 0",
    "path_b_docs_spec_allowed = 1",
    "path_b_current_descriptor_family_stopped = 1",
    "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance = defined",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status = spec_defined",
    "path_b_scoreinfo_certificate_engine_spec_defined = 1",
    "path_b_first1_fail_closed_shadow_scaffold_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold = fail_closed_shadow",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction",
    "runtime_work_drop_enabled = 0",
    "gate_first1_shadow_pass = 0",
    "next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go = recorded",
    "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate",
    "accepted_scoreinfo_certificate_engine_consumer = 0",
    "accepted_pre_drop_output_inert_certificate = 0",
    "path_b_scoreinfo_certificate_engine_family_stopped = 1",
    "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded",
    "path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined",
    "path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate",
    "next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
    "### Phase 7.4 - First1 Proof Shadow",
    "Run only after first1 reducing runtime passes.",
    "### Phase 7.5 - First64 Broad Gate",
    "### Phase 7.6 - Broad Promotion",
    "GpuScoreInfoTask",
    "GpuCandidateGroup",
    "GpuReplayAttempt",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "claimed_broad_replacement_rows > 0",
    "Only Phase 8 can close the active goal.",
    "## Immediate Next Actions",
    "Do not run first64 from the failed Phase 7.3 first1 runtime gate.",
    "Do not mark the goal complete unless Phase 8 closes Path A or Path B.",
    "make check-fasim-gasal2-roadmap-goal-closure-phase-plan",
    "make check-fasim-gasal2-roadmap-phase-driver",
    "make check-fasim-gasal2-roadmap-current-state",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing canonical phase-plan phrase(s):\n" + "\n".join(missing))

phase_order = [
    "## Phase 0 - Reproducibility",
    "## Phase 1 - Scoped Product Decision",
    "## Phase 2 - Full-Output Baseline",
    "## Phase 3 - CPU Output-Side Reduction",
    "## Phase 4 - Sort/Top-N Reduction",
    "## Phase 5 - Archive Artifact",
    "## Phase 6 - Workload Matrix",
    "## Phase 7 - Broad GPU Path",
    "## Phase 8 - Close Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("canonical phase headings are out of order")

phase7_order = [
    "### Phase 7.1 - New GPU Engine First1 Spec And Shadow",
    "### Phase 7.2 - Certificate CUDA API Producer",
    "### Phase 7.3 - First1 Reducing Runtime",
    "### Phase 7.4 - First1 Proof Shadow",
    "### Phase 7.5 - First64 Broad Gate",
    "### Phase 7.6 - Broad Promotion",
]
phase7_positions = [text.index(heading) for heading in phase7_order]
if phase7_positions != sorted(phase7_positions):
    raise SystemExit("canonical Phase 7 subphases are out of order")

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
    "fallback-heavy evidence counts as GPU-fast-path clean = 1",
    "existing v5 CPU-authority replay relabelled as new engine = 1",
    "final CPU output membership used as runtime proof = 1",
]:
    if forbidden in text:
        raise SystemExit(f"canonical phase plan contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
if link not in roadmap_text:
    raise SystemExit(f"roadmap does not link {link}")

target = "check-fasim-gasal2-roadmap-canonical-phase-plan:"
if target not in makefile_text:
    raise SystemExit(f"Makefile missing target: {target}")

current_state_target = "check-fasim-gasal2-roadmap-current-state:"
current_state_line = next(
    (line for line in makefile_text.splitlines() if line.startswith(current_state_target)),
    "",
)
if "check-fasim-gasal2-roadmap-canonical-phase-plan" not in current_state_line:
    raise SystemExit("current-state target does not depend on canonical phase-plan check")

print("canonical_phase_plan_document=present")
print("canonical_phase_plan_current_phase=phase7")
print("canonical_phase_plan_current_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("canonical_phase_plan_path_a_requires_user_acceptance=1")
print("canonical_phase_plan_path_b_requires_phase7_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
