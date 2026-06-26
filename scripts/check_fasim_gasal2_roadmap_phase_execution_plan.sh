#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"

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
    "# Fasim GASAL2 Goal Completion Phase Execution Plan",
    "This document is the phase-by-phase execution plan for making the active",
    "It is not a success claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A: scoped completion",
    "Path B: broad completion",
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
    "runtime_reduction_allowed = 0",
    "runtime_work_drop_allowed = 0",
    "first64_runtime_allowed = 0",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md",
    "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md",
    "accepted_scoreinfo_certificate_engine_consumer = 0",
    "accepted_pre_drop_output_inert_certificate = 0",
    "accepted_gpu_owned_scoreinfo_consumer = 0",
    "accepted_pre_drop_frontier_certificate = 0",
    "path_b_gpu_owned_scoreinfo_consumer_family_stopped = 1",
    "certificate_produced_before_work_drop = 0",
    "certificate_consumed_before_cpu_replay_selection = 0",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "current_execution_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "baseline_rows = 19",
    "candidate_rows = 2",
    "missing_rows = 17",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "GPU-owned scoreInfo consumer:",
    "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md",
    "gasal2_full_align_result_with_cpu_verifier_certificate",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "## Phase Overview",
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Decision",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: CPU Output-Side Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
    "### Phase 7a: Historical No-Go Ledger",
    "### Phase 7b: Post-No-Go Fork Checkpoint",
    "### Phase 7c: Full-Align Verifier First1 Fail-Closed Shadow",
    "### Phase 7d: Reducing Runtime First1",
    "### Phase 7e: First64 Broad Characterization",
    "### Phase 7f: Scale Gate",
    "### Phase 7g: Workload-Matrix Promotion",
    "make check-fasim-gasal2-roadmap-phase0-reproducibility",
    "make check-fasim-gasal2-roadmap-phase1-scoped-product",
    "make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert",
    "make check-fasim-gasal2-roadmap-phase4-sort-topn",
    "make check-fasim-gasal2-roadmap-phase5-archive-artifact",
    "make check-fasim-gasal2-roadmap-phase6-workload-matrix",
    "make check-fasim-gasal2-roadmap-phase8-completion-decision",
    "make check-fasim-gasal2-roadmap-current-state",
    "requested = 1",
    "active = 1",
    "proposals > 0",
    "verifier_pass > 0 or verifier failure taxonomy complete",
    "score_mismatches = 0",
    "endpoint_mismatches = 0",
    "cigar_mismatches = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "gpu_output_digest_authority = 0",
    "gate_first1_shadow_pass = 1",
    "uses_cpu_verifier_certificate = 1",
    "verifier_consumed_before_cpu_align_skip = 1",
    "candidate_align_attempts < reference_align_attempts",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "gate_first1_pass = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "claimed_broad_replacement_rows > 0",
    "path_a_close_packet_pass = 1",
    "path_b_close_packet_pass = 1",
    "fasim: design GASAL2 full-align verifier certificate shadow",
    "use docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md as input",
    "no runtime reduction in the verifier spec checkpoint",
    "no continuation of the stopped GPU-owned shadow as a reducing runtime",
    "no continuation of the stopped scoreInfo certificate-engine family",
    "no continuation of the stopped post-v5.3 descriptor-stream family",
    "no first64 before first1 passes",
    "no broad_replacement matrix promotion before first64 or larger gate passes",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing phase execution plan phrase(s):\n" + "\n".join(missing)
    )

phase_order = [
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Decision",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: CPU Output-Side Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("phase execution plan headings are out of order")

gate_order = [
    "### Phase 7a: Historical No-Go Ledger",
    "### Phase 7b: Post-No-Go Fork Checkpoint",
    "### Phase 7c: Full-Align Verifier First1 Fail-Closed Shadow",
    "### Phase 7d: Reducing Runtime First1",
    "### Phase 7e: First64 Broad Characterization",
    "### Phase 7f: Scale Gate",
    "### Phase 7g: Workload-Matrix Promotion",
]
gate_positions = [text.index(heading) for heading in gate_order]
if gate_positions != sorted(gate_positions):
    raise SystemExit("phase execution plan Phase 7 gates are out of order")

for forbidden in [
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "top5-only evidence closes broad objective = 1",
    "archive-only evidence closes broad objective = 1",
    "output-drift speedup counts as success = 1",
    "run first64 from a failed first1 producer",
]:
    if forbidden in text:
        raise SystemExit(f"phase execution plan contains forbidden phrase: {forbidden}")

print("phase_execution_plan_document=present")
print("phase_execution_plan_current_phase=phase7")
print("phase_execution_plan_current_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("phase_execution_plan_path_a_requires_user_acceptance=1")
print("phase_execution_plan_path_b_requires_phase7_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
