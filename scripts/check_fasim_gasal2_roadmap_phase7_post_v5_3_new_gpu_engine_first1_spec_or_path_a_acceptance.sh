#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md"
PHASE_DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$PREV" "$PHASE_DRIVER" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev = Path(sys.argv[2])
phase_driver = Path(sys.argv[3])
roadmap = Path(sys.argv[4])

for path in [doc, prev, phase_driver, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Spec Or Path A Acceptance",
    "phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_new_gpu_engine_first1_spec_or_path_a_acceptance",
    "runtime_reduction_enabled = 0",
    "runtime_pr_allowed = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_first1_spec_defined = 1",
    "path_b_first1_runtime_allowed = 0",
    "## First1 Data Layout Contract",
    "GpuScoreInfoTask",
    "query_id",
    "query_offset",
    "query_length",
    "target_id",
    "target_offset",
    "target_length",
    "scoring_config_key",
    "min_score",
    "output_slot",
    "task_order",
    "GpuCandidateGroup",
    "scoreinfo_group_id",
    "score",
    "target_end",
    "query_end",
    "candidate_order_key",
    "attempt_start_index",
    "attempt_count",
    "GpuReplayAttempt",
    "attempt_id",
    "group_id",
    "target_start",
    "target_end",
    "query_start",
    "query_end",
    "legacy_attempt_order",
    "## Certificate Contract",
    "skipped_scoreinfo_upper_bound_score",
    "skipped_attempt_upper_bound_score",
    "skipped_attempt_upper_bound_nt",
    "skipped_attempt_upper_bound_identity",
    "skipped_attempt_upper_bound_stability",
    "task_output_capacity_exhausted",
    "scoreinfo_local_break_state",
    "certificate_valid_before_d2h = 1",
    "final_cpu_output_membership_required_for_certificate = 0",
    "## Fail-Closed Rules",
    "fallback_on_missing_bound = 1",
    "fallback_on_capacity_exhaustion = 1",
    "fallback_on_order_ambiguity = 1",
    "fallback_on_unsupported_shape = 1",
    "fallback_to_full_cpu_replay = 1",
    "## First1 Telemetry",
    "gpu_tasks",
    "gpu_candidate_groups",
    "gpu_selected_attempts",
    "gpu_skipped_groups",
    "gpu_skipped_attempts",
    "cpu_replay_attempts",
    "baseline_cpu_attempts",
    "scoreInfo_prealign_reduction_ratio",
    "align_side_reduction_ratio",
    "fallback_reason_counts",
    "certificate_false_negatives",
    "missing_required_attempts",
    "## First1 Acceptance Gate",
    "digest_match = 1",
    "full_rows_equal = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "scoreInfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_accounting_clean = 1",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "## Current Decision",
    "next_valid_gate = phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_first1_shadow_or_path_a_acceptance",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine first1 spec phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_pr_allowed = 1",
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_first1_runtime_allowed = 1",
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
            "new GPU engine first1 spec checkpoint contains forbidden phrase: "
            + forbidden
        )

prev_text = prev.read_text(encoding="utf-8")
if "next_valid_gate = phase7_new_gpu_engine_first1_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous checkpoint no longer points to first1 spec gate")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md"
for path in [phase_driver, roadmap]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link first1 spec checkpoint")

print("phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance=defined")
print("path_a_user_acceptance_recorded=0")
print("path_a_scoped_completion_may_close_goal=0")
print("path_b_first1_spec_defined=1")
print("path_b_first1_runtime_allowed=0")
print("runtime_pr_allowed=0")
print("next_valid_gate=phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_first1_shadow_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
