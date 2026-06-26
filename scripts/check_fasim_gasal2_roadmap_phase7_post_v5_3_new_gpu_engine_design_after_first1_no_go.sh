#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$CLOSURE" "$DRIVER" "$CANONICAL" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc, prev, roadmap, closure, driver, canonical, makefile = [
    Path(arg) for arg in sys.argv[1:]
]

for path in [doc, prev, roadmap, closure, driver, canonical, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
canonical_text = canonical.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Design After First1 No-Go",
    "phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md",
    "previous_gate = path_a_scoped_acceptance_or_new_engine_design_doc",
    "runtime_reduction_enabled = 0",
    "runtime_pr_allowed = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "first1_runtime_reduction_gate_pass = 0",
    "real_fasim_runtime_certificate_source = 0",
    "real_fasim_runtime_work_drop_path = 0",
    "prealign_cuda_emit_new_engine_skipped_work_certificates_runtime_call_count = 0",
    "design_family = real_source_fasim_compatible_gpu_scoreinfo_attempt_engine",
    "not_synthetic_certificate_producer_continuation = 1",
    "not_v5_cpu_authority_replay_relabel = 1",
    "not_current_descriptor_stream_continuation = 1",
    "requires_real_fasim_runtime_certificate_source = 1",
    "requires_real_fasim_runtime_work_drop_point = 1",
    "real_runtime_hook_location",
    "scoreInfo_task_construction_point",
    "gpu_input_layout",
    "gpu_candidate_group_layout",
    "gpu_replay_attempt_layout",
    "certificate_producer_location",
    "certificate_consumer_location",
    "work_drop_decision_point",
    "fallback_to_full_cpu_replay_point",
    "telemetry_namespace",
    "skipped_scoreinfo_upper_bound_score",
    "skipped_attempt_upper_bound_score",
    "skipped_attempt_upper_bound_nt",
    "skipped_attempt_upper_bound_identity",
    "skipped_attempt_upper_bound_stability",
    "scoreinfo_local_break_state",
    "task_output_capacity",
    "certificate_valid_before_d2h = 1",
    "final_cpu_output_membership_required_for_certificate = 0",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 1",
    "runtime_certificate_is_synthetic = 0",
    "fallback_to_full_cpu_replay_on_uncertainty = 1",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "candidate_wall_seconds < baseline_wall_seconds",
    "do_not_run_first64_before_real_source_first1_pass = 1",
    "do_not_reuse_synthetic_certificate_producer_as_runtime_proof = 1",
    "do_not_use_final_cpu_output_membership_as_runtime_proof = 1",
    "do_not_relabel_v5_cpu_authority_replay_as_new_engine = 1",
    "do_not_promote_gpu_endpoint_cigar_traceback_output_digest_authority = 1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_real_source_design_checkpoint_defined = 1",
    "path_b_runtime_pr_allowed = 0",
    "current_execution_gate = phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing after-first1-no-go design phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_pr_allowed = 1",
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_runtime_pr_allowed = 1",
    "runtime_certificate_is_synthetic = 1",
    "final_cpu_output_membership_required_for_certificate = 1",
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
            "after-first1-no-go design contains forbidden phrase: " + forbidden
        )

for phrase in [
    "phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go = recorded",
    "first1_runtime_reduction_gate_pass = 0",
    "real_fasim_runtime_certificate_source = 0",
    "real_fasim_runtime_work_drop_path = 0",
    "path_b_runtime_pr_allowed = 0",
]:
    if phrase not in prev_text:
        raise SystemExit(f"previous no-go checkpoint missing phrase: {phrase}")

doc_link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md"
for path_name, path_text in [
    ("roadmap", roadmap_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("canonical phase plan", canonical_text),
]:
    if doc_link not in path_text:
        raise SystemExit(f"{path_name} does not link after-first1-no-go design")

for path_name, path_text in [
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("canonical phase plan", canonical_text),
]:
    for phrase in [
        "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
        "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
        "runtime_pr_allowed = 0",
        "first64_runtime_allowed = 0",
    ]:
        if phrase not in path_text:
            raise SystemExit(f"{path_name} missing updated cursor phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go:"
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
target_name = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include after-first1-no-go design target")

print("phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go=defined")
print("design_family=real_source_fasim_compatible_gpu_scoreinfo_attempt_engine")
print("path_b_real_source_design_checkpoint_defined=1")
print("path_b_runtime_pr_allowed=0")
print("current_execution_gate=phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
