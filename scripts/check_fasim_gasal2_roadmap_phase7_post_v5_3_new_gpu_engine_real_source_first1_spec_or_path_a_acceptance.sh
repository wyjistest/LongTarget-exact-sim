#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md"
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
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source First1 Spec Or Path A Acceptance",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md",
    "previous_gate = phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance",
    "runtime_reduction_enabled = 0",
    "runtime_pr_allowed = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_real_source_first1_spec_defined = 1",
    "path_b_first1_shadow_runtime_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "real_runtime_hook_location = scoreInfo/preAlign task construction before CPU replay attempts are selected",
    "certificate_producer_location = GPU scoreInfo/attempt engine before D2H",
    "certificate_consumer_location = CPU replay scheduler before dropping replay work",
    "work_drop_decision_point = before CPU aligner.Align() attempts are skipped",
    "fallback_to_full_cpu_replay_point = before output rows are materialized",
    "real_fasim_runtime_certificate_source_required = 1",
    "real_fasim_runtime_work_drop_path_required = 1",
    "runtime_certificate_is_synthetic_allowed = 0",
    "host_only_after_full_descriptor_export_allowed = 0",
    "final_cpu_output_membership_required_for_certificate = 0",
    "RealSourceGpuScoreInfoTask",
    "task_id",
    "query_id",
    "query_offset",
    "query_length",
    "target_id",
    "target_offset",
    "target_length",
    "scoring_config_key",
    "min_score",
    "min_nt",
    "task_order",
    "output_slot",
    "RealSourceGpuCandidateGroup",
    "group_id",
    "scoreinfo_score",
    "target_end",
    "query_end",
    "candidate_order_key",
    "first_attempt_id",
    "attempt_count",
    "RealSourceGpuReplayAttempt",
    "attempt_id",
    "target_start",
    "target_end",
    "query_start",
    "query_end",
    "legacy_attempt_order",
    "replay_required",
    "RealSourceGpuSkippedWorkCertificate",
    "skipped_group_id",
    "skipped_attempt_id",
    "skipped_scoreinfo_upper_bound_score",
    "skipped_attempt_upper_bound_score",
    "skipped_attempt_upper_bound_nt",
    "skipped_attempt_upper_bound_identity",
    "skipped_attempt_upper_bound_stability",
    "scoreinfo_local_break_state",
    "task_output_capacity",
    "certificate_valid_before_d2h",
    "certificate_reason",
    "fallback_on_missing_certificate = 1",
    "fallback_on_order_ambiguity = 1",
    "fallback_on_capacity_exhaustion = 1",
    "fallback_on_unsupported_query_or_target_shape = 1",
    "fallback_on_cuda_error = 1",
    "fallback_to_full_cpu_replay = 1",
    "real_source_first1_requested",
    "real_source_first1_active",
    "real_fasim_runtime_certificate_source",
    "real_fasim_runtime_work_drop_path",
    "runtime_certificate_is_synthetic",
    "gpu_tasks",
    "gpu_candidate_groups",
    "gpu_replay_attempts",
    "gpu_selected_attempts",
    "gpu_skipped_groups",
    "gpu_skipped_attempts",
    "cpu_replay_attempts",
    "baseline_cpu_attempts",
    "scoreInfo_prealign_reduced",
    "align_side_reduced",
    "fallback_reason_counts",
    "certificate_false_negatives",
    "missing_required_attempts",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "full_rows_equal",
    "digest_match",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 1",
    "runtime_certificate_is_synthetic = 0",
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
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "next_valid_gate = phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing real-source first1 spec phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_pr_allowed = 1",
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_first1_shadow_runtime_allowed = 1",
    "path_b_first64_runtime_allowed = 1",
    "runtime_certificate_is_synthetic_allowed = 1",
    "host_only_after_full_descriptor_export_allowed = 1",
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
            "real-source first1 spec contains forbidden phrase: " + forbidden
        )

if "current_execution_gate = phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous after-first1-no-go design no longer points to this gate")

doc_link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md"
for path_name, path_text in [
    ("roadmap", roadmap_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("canonical phase plan", canonical_text),
]:
    if doc_link not in path_text:
        raise SystemExit(f"{path_name} does not link real-source first1 spec")

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

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance:"
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
target_name = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include real-source first1 spec target")

print("phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance=defined")
print("path_b_real_source_first1_spec_defined=1")
print("path_b_first1_shadow_runtime_allowed=0")
print("path_b_first64_runtime_allowed=0")
print("next_valid_gate=phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
