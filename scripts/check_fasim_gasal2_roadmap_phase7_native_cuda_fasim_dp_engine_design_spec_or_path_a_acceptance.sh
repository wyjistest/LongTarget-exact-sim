#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL" "$CLOSURE" "$DRIVER" "$PLAYBOOK" "$CURRENT_STATE" "$MAKEFILE" <<'PY'
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
    current_state,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
phase_text = phase_plan.read_text(encoding="utf-8")
canonical_text = canonical.read_text(encoding="utf-8")
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
playbook_text = playbook.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine Design Spec Or Path A Acceptance",
    "phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md",
    "previous_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_native_cuda_fasim_dp_engine_spec_defined = 1",
    "design_family = native_cuda_fasim_dp_certificate_engine",
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
    "native_scoreinfo_byte_dp_layout",
    "native_forward_score_endpoint_layout",
    "native_reverse_start_layout",
    "native_traceback_cigar_witness_layout",
    "pre_drop_certificate_field_math",
    "consumer_decision_point_before_cpu_align_skip",
    "fallback_accounting_schema",
    "first1_shadow_inputs",
    "first1_shadow_expected_telemetry",
    "FasimByteScoreInfoTile",
    "FasimForwardEndpointWitness",
    "FasimReverseStartWitness",
    "FasimTracebackCigarWitness",
    "FasimDpCertificate",
    "request_id",
    "scoreinfo_id",
    "candidate_id",
    "legacy_request_order",
    "translated_query_digest",
    "translated_target_window_digest",
    "byte_saturation_mode",
    "window_of_5_cluster_id",
    "local_max_tie_policy_id",
    "reverse_start_policy_id",
    "traceback_policy_id",
    "cigar_encoding_digest",
    "certificate_valid_before_cpu_align_skip",
    "certificate_consumed_before_cpu_align_skip = 0",
    "certificate_consumed_before_cpu_replay_selection = 0",
    "CPU aligner.Align() remains verifier and fallback authority.",
    "GPU certificate may only prove that CPU work can be skipped at a later gate.",
    "No GPU result is final score, endpoint, CIGAR, traceback, output, or digest authority.",
    "required_env = FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_native_cuda_fasim_dp_engine_",
    "native_scoreinfo_tiles",
    "forward_endpoint_witnesses",
    "reverse_start_witnesses",
    "traceback_cigar_witnesses",
    "certificates",
    "certificate_false_negatives",
    "missing_required_attempts",
    "scoreinfo_byte_mismatches",
    "endpoint_mismatches",
    "reverse_start_mismatches",
    "cigar_mismatches",
    "full_row_mismatches",
    "digest_mismatches",
    "cpu_align_fallbacks",
    "requested = 1",
    "active = 1",
    "certificates > 0",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "scoreinfo_byte_mismatches = 0",
    "endpoint_mismatches = 0",
    "reverse_start_mismatches = 0",
    "cigar_mismatches = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "gate_first1_shadow_pass = 1",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "candidate_wall_seconds < baseline_wall_seconds",
    "phase7_native_cuda_fasim_dp_engine_design_spec_status = spec_defined",
    "path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "no real opt-in",
    "no runtime reduction in this design/spec checkpoint",
    "no runtime work drop in this design/spec checkpoint",
    "no first64 before first1 fail-closed shadow passes",
    "no GASAL2 proposal semantics",
    "no GPU score authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no GPU output authority",
    "no GPU digest authority",
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
        "missing native CUDA Fasim DP design/spec phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "path_b_runtime_reduction_pr_allowed = 1",
    "path_b_runtime_work_drop_allowed = 1",
    "path_b_first64_runtime_allowed = 1",
    "not_gasal2_full_align_verifier_continuation = 0",
    "not_gasal2_align_replacement = 0",
    "not_gpu_owned_scoreinfo_consumer_continuation = 0",
    "not_scoreinfo_certificate_engine_continuation = 0",
    "not_post_v5_3_descriptor_stream_continuation = 0",
    "certificate_consumed_before_cpu_align_skip = 1",
    "certificate_consumed_before_cpu_replay_selection = 1",
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
        raise SystemExit(
            f"native CUDA Fasim DP design/spec contains forbidden phrase: {forbidden}"
        )

if "next_valid_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous fork does not point to the native CUDA Fasim DP spec gate")

link = "docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md"
next_gate = "phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold"
next_pr = "fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold"
for name, content in [
    ("roadmap", roadmap_text),
    ("phase-to-completion", phase_text),
    ("canonical phase plan", canonical_text),
    ("closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("playbook", playbook_text),
]:
    if link not in content:
        raise SystemExit(f"{name} does not link native CUDA Fasim DP spec")
    if f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{name} cursor was not advanced to the native CUDA Fasim DP first1 shadow gate")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{name} next PR was not advanced to the native CUDA Fasim DP first1 shadow")

for phrase in [
    "phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "phase7_native_cuda_fasim_dp_engine_design_spec_status",
    "path_b_native_cuda_fasim_dp_engine_spec_defined",
    "path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed",
    "phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-design-spec-or-path-a-acceptance:"
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
if "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-design-spec-or-path-a-acceptance" not in current_state_line:
    raise SystemExit("current-state target does not include native CUDA Fasim DP spec check")

print("phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance=defined")
print("phase7_native_cuda_fasim_dp_engine_design_spec_status=spec_defined")
print("path_b_native_cuda_fasim_dp_engine_spec_defined=1")
print("path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed=1")
print("next_valid_gate=phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold")
print("current_next_pr=fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold")
print("runtime_reduction_enabled=0")
print("runtime_work_drop_enabled=0")
print("first64_runtime_allowed=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
