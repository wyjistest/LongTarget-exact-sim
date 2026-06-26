#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_phase_checklist.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
phase_plan = Path(sys.argv[3])

for path in [doc, roadmap, phase_plan]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_plan_text = phase_plan.read_text(encoding="utf-8")
phase_plan_flat = " ".join(phase_plan_text.split())

required_phrases = [
    "# Fasim GASAL2 Goal Completion Phase Checklist",
    "Path A: scoped completion",
    "Path B: broad completion",
    "broad_objective_status = open",
    "Current Path A decision:",
    "scope_or_broad_design_decision_required = 0",
    "path_a_user_acceptance_required = 0",
    "path_b_new_broad_architecture_required = 0",
    "completion_guard_cleared = 1",
    "goal_completion_status = complete",
    "must_not_call_update_goal_complete = 0",
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Contract",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
    "make check-fasim-gasal2-roadmap-phase0-reproducibility",
    "make check-fasim-gasal2-roadmap-phase1-scoped-product",
    "make check-fasim-gasal2-roadmap-path-a-scoped-acceptance",
    "make check-fasim-gasal2-roadmap-phase5-archive-artifact",
    "make check-fasim-gasal2-roadmap-phase6-workload-matrix",
    "make check-fasim-gasal2-roadmap-phase7-current-broad-stop-decision",
    "make check-fasim-gasal2-roadmap-phase8-completion-decision",
    "make check-fasim-gasal2-roadmap-current-state",
    "user_scope_acceptance_recorded = 1",
    "scoped_completion_may_close_goal = 1",
    "active_goal_completion_status = complete_scoped_path_a",
    "broad_gate_pass = 1",
    "claimed_broad_replacement_rows > 0",
    "v4 scoreInfo-native GPU design defined",
    "v4 legacy-byte scoreInfo host-contract smoke clean",
    "v4 GPU legacy-byte scoreInfo first1 shadow clean",
    "v4 GPU legacy-byte scoreInfo source replay first1 clean",
    "v4 GPU legacy-byte scoreInfo source first64 broad gate no-go",
    "v5 post-scoreInfo descriptor scaffold no-go",
    "v5 true pre-scoreInfo descriptor source design defined",
    "v5 true pre-scoreInfo descriptor source env scaffold fail-closed",
    "v5 true pre-scoreInfo descriptor source strict runtime smoke pass",
    "v5 CPU-authority replay first1 smoke pass",
    "v5 CPU-authority replay first64 broad gate no-go",
    "next Path B gate = pre_d2h_output_inert_proof_search_first1_export",
    "post-v5.3 pre-D2H proof-search design defined",
    "docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = gate_v5_1_pass_first1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1",
    "existing_v4_gpu_source_materializes_host_visible_scoreinfo_rows = 1",
    "existing_cuda_api_emits_prealign_cuda_peaks_not_attempt_descriptors = 1",
    "do_not_rebrand_v4_source_replay_as_v5 = 1",
    "next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
    "docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md",
    "phase7_broad_restart_v5_cpu_authority_replay_smoke = gate_v5_2_pass_first1",
    "root_cause_fix = legacy_float_identity_cutlength_descriptor_generation",
    "phase7_v5_cpu_authority_replay_full_rows_equal = 1",
    "phase7_v5_cpu_authority_replay_digest_match = 1",
    "phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008",
    "phase7_v5_cpu_authority_replay_reference_align_attempts = 2872",
    "phase7_broad_restart_v5_gate_v5_2_pass = 1",
    "next_required_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md",
    "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
    "phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009",
    "phase7_broad_restart_v5_first64_missing_required_attempts = 624",
    "phase7_broad_restart_v5_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0",
    "next_required_gate = pre_d2h_output_inert_proof_acceptance_first1",
    "current_next_pr = fasim: audit pre-D2H output-inert proof-search first1",
    "runtime_reduction_enabled = 0",
    "v5 CUDA descriptor emission design defined",
    "docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md",
    "phase7_broad_restart_v5_cuda_descriptor_emission_design = defined",
    "phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only",
    "new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors",
    "output_contract = compact_attempt_descriptors_not_scoreinfo_rows",
    "host-visible full legacy scoreInfo row stream = forbidden",
    "CPU aligner.Align() authority replay = 1",
    "GPU endpoint/CIGAR/traceback/output authority = 0",
    "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design",
    "current broad sources are stopped/no-go",
    "Keep CPU aligner.Align() as authority",
    "docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md",
    "Do not continue to first64 because the current all-column certificate overgenerates attempts and has a preflight CPU replay no-go.",
    "Do not run all-column CPU replay; it would require 168,730,848 candidate Align attempts against 2,872 reference Align attempts.",
    "docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md",
    "Do not continue the bounded narrow probe to first64 because it has candidate certificate false negatives and missing required attempts.",
    "docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md",
    "Do not continue the existing exact-column GPU scoreInfo source because non-opt-in launch fails and smem opt-in has scoreInfo mismatches.",
    "docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md",
    "docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md",
    "task/scoreInfo coverage clean",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts > 0",
    "Do not continue the strong-seed source to replay while required attempt coverage is missing.",
    "docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md",
    "missing_required_attempts = 0",
    "candidate_attempts below all-column replay scale",
    "candidate_attempts_below_reference = 0",
    "candidate_min_cover_positions_below_reference = 1",
    "oracle_min_cover_uses_legacy_attempt_windows = 1",
    "docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md",
    "candidate_align_attempts = 463",
    "reference_align_attempts = 2,872",
    "missing_rows = 11",
    "extra_rows = 9",
    "phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0",
    "Do not continue the oracle min-cover replay shape to first64 because full output rows differ.",
    "docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md",
    "phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md",
    "phase7_broad_restart_v4_scoreinfo_native_design = defined",
    "phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1",
    "docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md",
    "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke = host_contract_clean_needs_gpu",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0",
    "phase7_broad_restart_v4_host_contract_pass = 1",
    "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =",
    "gpu_contract_clean_first1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718",
    "phase7_broad_restart_v4_gate_v4_1_pass = 1",
    "gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay",
    "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =",
    "cpu_authority_replay_clean_first1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864",
    "phase7_broad_restart_v4_gate_v4_2_pass = 1",
    "gpu_legacy_byte_scoreinfo_source_first64_broad_gate",
    "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate = correctness_clean_performance_no_go",
    "baseline_wall_seconds = 86.358386",
    "candidate_wall_seconds = 134.744406",
    "candidate_vs_baseline = 0.640905",
    "digest_match = 1",
    "candidate_realpath_extend_align_attempts = 140087",
    "reference_align_attempts = 211976",
    "align_attempt_reduction = 71889",
    "phase7_broad_restart_v4_gate_v4_3_pass = 0",
    "different_gpu_execution_design_or_path_a_scope_decision",
    "Do not continue the current v4 source replay implementation as a broad completion path because first64 wall time is slower than CPU baseline.",
    "Continue Path B only with a different GPU execution design that proves:",
    "scoreinfo_rows_equal = true",
    "scoreinfo_order_equal = true",
    "scoreinfo_attempt_windows_equal = true",
    "candidate_align_attempts < reference_align_attempts",
    "real_pre_scoreinfo_reducer_proven = 1 before broad promotion",
    "candidate_wall_seconds < baseline_wall_seconds",
    "Add `contract=broad_replacement` only after a future first64 path passes with full equality, wall-time win, scoreInfo/preAlign reduction, Align-side reduction, and fallback accounting clean.",
]

missing = [phrase for phrase in required_phrases if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit("missing required checklist phrase(s):\n" + "\n".join(missing))

phase_order = [
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Contract",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("phase headings are out of order")

link = "docs/fasim_gasal2_goal_completion_phase_checklist.md"
if link not in roadmap_text:
    raise SystemExit("roadmap does not link phase checklist")
if link not in phase_plan_text:
    raise SystemExit("phase plan does not link phase checklist")

for phrase in [
    "The next phase must run the same GPU legacy-byte scoreInfo source through first64",
]:
    if phrase in phase_plan_flat:
        raise SystemExit(f"phase plan contains stale forbidden phrase: {phrase}")

print("phase_checklist_document=present")
print("phase_checklist_paths=linked")
print("phase_checklist_phase_count=9")
print("phase_checklist_completion_paths=path_a_path_b")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
