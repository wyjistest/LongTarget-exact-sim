#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
EXECUTION_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"
DIRECT="$ROOT/docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$EXECUTION_PLAN" "$DIRECT" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    playbook,
    execution_plan,
    direct,
    current_state,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical,
    closure,
    driver,
    playbook,
    execution_plan,
    direct,
    current_state,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction Design Spec Or Path A Acceptance",
    "phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md",
    "previous_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_gpu_exact_work_unit_compaction_spec_defined = 1",
    "design_family = gpu_exact_work_unit_compaction_replay",
    "not_gpu_upper_bound_reject_certificate_continuation = 1",
    "not_native_cuda_fasim_dp_engine_continuation = 1",
    "not_gasal2_full_align_verifier_continuation = 1",
    "not_gasal2_align_replacement = 1",
    "not_gpu_owned_scoreinfo_consumer_continuation = 1",
    "not_scoreinfo_certificate_engine_continuation = 1",
    "not_post_v5_3_descriptor_stream_continuation = 1",
    "not_final_cpu_output_membership_proof = 1",
    "not_top5_only_contract = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "proof_shape = exact_input_equivalence_compaction",
    "gpu_accepts_rows = 0",
    "gpu_rejects_rows = 0",
    "gpu_emits_final_rows = 0",
    "gpu_endpoint_cigar_traceback_required = 0",
    "cpu_authority_replay_required = 1",
    "fallback_to_full_cpu_replay_on_uncertainty = 1",
    "ExactWorkUnitKey",
    "work_kind",
    "legacy_request_order",
    "translated_query_digest",
    "translated_target_window_digest",
    "target_window_offset",
    "target_window_length",
    "strand",
    "scoring_config_key",
    "gap_config_key",
    "threshold_config_key",
    "translation_config_key",
    "output_context_key",
    "exact_key_match_required = 1",
    "cpu_key_validation_required = 1",
    "key_collision_fallback_to_full_cpu_replay = 1",
    "unsupported_key_fallback_to_full_cpu_replay = 1",
    "hash_match_only_is_not_proof = 1",
    "digest_collision_fallback_to_full_cpu_replay = 1",
    "canonical_key_bytes_must_match = 1",
    "scoreinfo_prealign_compaction",
    "align_candidate_compaction",
    "requires_scoreinfo_prealign_reduction_plan = 1",
    "requires_align_side_reduction_plan = 1",
    "requires_ordered_replay_plan = 1",
    "requires_cpu_authority_result_cache = 1",
    "key_collection_only_is_shadow = 1",
    "duplicate_count_only_is_not_runtime_reduction = 1",
    "required_env = FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_",
    "scoreinfo_key_descriptors",
    "scoreinfo_unique_keys",
    "scoreinfo_duplicate_units",
    "align_key_descriptors",
    "align_unique_keys",
    "align_duplicate_attempts",
    "key_collisions",
    "cpu_key_validation_mismatches",
    "unsupported_key_descriptors",
    "fallback_to_full_cpu_replay = 1",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "scoreinfo_key_descriptors > 0",
    "align_key_descriptors > 0",
    "key_collisions = 0",
    "cpu_key_validation_mismatches = 0",
    "gate_first1_shadow_pass = 1",
    "scoreinfo_duplicate_units > 0",
    "align_duplicate_attempts > 0",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "fallback_accounting_clean = 1",
    "phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined",
    "path_b_gpu_exact_work_unit_compaction_first1_fail_closed_shadow_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "no real opt-in",
    "no runtime reduction in this design/spec checkpoint",
    "no runtime work drop in this design/spec checkpoint",
    "no first64 before first1 fail-closed shadow passes",
    "no GPU accept decision",
    "no GPU reject decision",
    "no GPU score authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no GPU output authority",
    "no GPU digest authority",
    "no final CPU output membership proof",
    "no top5-only contract",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "default behavior unchanged = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing GPU exact work-unit compaction spec phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gpu_accepts_rows = 1",
    "gpu_rejects_rows = 1",
    "gpu_emits_final_rows = 1",
    "key_collision_fallback_to_full_cpu_replay = 0",
    "unsupported_key_fallback_to_full_cpu_replay = 0",
    "hash_match_only_is_not_proof = 0",
    "path_b_runtime_reduction_pr_allowed = 1",
    "path_b_runtime_work_drop_allowed = 1",
    "path_b_first64_runtime_allowed = 1",
    "not_gpu_upper_bound_reject_certificate_continuation = 0",
    "not_native_cuda_fasim_dp_engine_continuation = 0",
    "not_gasal2_full_align_verifier_continuation = 0",
    "not_gasal2_align_replacement = 0",
    "not_gpu_owned_scoreinfo_consumer_continuation = 0",
    "not_scoreinfo_certificate_engine_continuation = 0",
    "not_post_v5_3_descriptor_stream_continuation = 0",
    "GPU score authority = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"GPU exact work-unit compaction spec contains forbidden phrase: {forbidden}")

if "next_valid_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go" not in prev_text:
    raise SystemExit("previous post-upper-bound fork does not point to new design/spec gate")

link = "docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md"
next_gate = "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold"
next_pr = "fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold"
for label, path in [
    ("roadmap", roadmap),
    ("phase-to-completion", phase_plan),
    ("canonical phase plan", canonical),
    ("goal closure phase plan", closure),
    ("phase driver", driver),
    ("playbook", playbook),
    ("phase execution plan", execution_plan),
    ("direct phase roadmap", direct),
]:
    content = path.read_text(encoding="utf-8")
    if link not in content:
        raise SystemExit(f"{label} does not link GPU exact work-unit compaction spec")
    if f"current_gate_document = {link}" not in content:
        raise SystemExit(f"{label} does not set current gate document to GPU exact work-unit compaction spec")
    if (
        f"current_execution_gate = {next_gate}" not in content
        and f"current_gate = {next_gate}" not in content
    ):
        raise SystemExit(f"{label} cursor was not advanced to exact-work-unit first1 shadow")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{label} next PR was not advanced to exact-work-unit first1 shadow")

for phrase in [
    "phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance",
    "phase7_gpu_exact_work_unit_compaction_design_spec_status",
    "gpu_exact_work_unit_compaction_replay",
    "path_b_gpu_exact_work_unit_compaction_spec_defined",
    "path_b_gpu_exact_work_unit_compaction_first1_fail_closed_shadow_allowed",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-design-spec-or-path-a-acceptance:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

target_name = "check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-design-spec-or-path-a-acceptance"
if f"check-fasim-gasal2-roadmap-current-state: {target_name}" not in makefile_text:
    raise SystemExit("current-state aggregate does not include exact-work-unit compaction spec target")

print("phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance=defined")
print("phase7_gpu_exact_work_unit_compaction_design_spec_status=spec_defined")
print("path_b_gpu_exact_work_unit_compaction_spec_defined=1")
print("design_family=gpu_exact_work_unit_compaction_replay")
print("next_valid_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("runtime_reduction_enabled=0")
print("runtime_work_drop_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
