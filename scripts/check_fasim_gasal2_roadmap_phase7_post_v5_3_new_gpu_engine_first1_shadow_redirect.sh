#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$PREV" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev = Path(sys.argv[2])
roadmap = Path(sys.argv[3])

for path in [doc, prev, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Shadow Redirect",
    "phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance",
    "runtime_reduction_enabled = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "reviewed_existing_runtime = FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY",
    "reviewed_existing_source = PreAlignCudaAttemptDescriptor",
    "existing_v5_cpu_authority_replay_first1_gate_pass = 1",
    "existing_v5_cpu_authority_replay_matches_new_engine_spec = 0",
    "reason = missing_pre_d2h_skipped_work_certificate",
    "skipped_scoreinfo_upper_bound_score = missing",
    "skipped_attempt_upper_bound_score = missing",
    "skipped_attempt_upper_bound_nt = missing",
    "skipped_attempt_upper_bound_identity = missing",
    "skipped_attempt_upper_bound_stability = missing",
    "task_output_capacity_exhausted = missing",
    "scoreinfo_local_break_state = missing",
    "certificate_valid_before_d2h = 0",
    "final_cpu_output_membership_required_for_certificate = forbidden",
    "new_gpu_engine_first1_shadow_gate_pass = 0",
    "do_not_relabel_v5_cpu_authority_replay_as_new_engine = 1",
    "do_not_run_first64_from_v5_replay_for_new_engine = 1",
    "do_not_add_broad_replacement_row_from_v5_replay = 1",
    "path_a_user_acceptance_required = 1",
    "path_b_new_engine_runtime_required = 1",
    "current_next_pr = fasim_new_gpu_engine_first1_shadow_runtime_or_path_a_acceptance",
    "next_valid_gate = implement_new_gpu_engine_first1_shadow_or_path_a_acceptance",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine first1 shadow redirect phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "existing_v5_cpu_authority_replay_matches_new_engine_spec = 1",
    "certificate_valid_before_d2h = 1",
    "new_gpu_engine_first1_shadow_gate_pass = 1",
    "do_not_relabel_v5_cpu_authority_replay_as_new_engine = 0",
    "do_not_run_first64_from_v5_replay_for_new_engine = 0",
    "do_not_add_broad_replacement_row_from_v5_replay = 0",
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
            "new GPU engine first1 shadow redirect contains forbidden phrase: "
            + forbidden
        )

prev_text = prev.read_text(encoding="utf-8")
if "next_valid_gate = phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous checkpoint no longer points to first1 shadow gate")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md"
if link not in roadmap.read_text(encoding="utf-8"):
    raise SystemExit("roadmap does not link first1 shadow redirect checkpoint")

print("phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect=recorded")
print("existing_v5_cpu_authority_replay_matches_new_engine_spec=0")
print("new_gpu_engine_first1_shadow_gate_pass=0")
print("next_valid_gate=implement_new_gpu_engine_first1_shadow_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_first1_shadow_runtime_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
