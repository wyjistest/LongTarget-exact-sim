#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md"
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
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Spec Or Path A Acceptance",
    "phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md",
    "previous_gate = phase7_new_gpu_engine_spec_or_path_a_acceptance",
    "runtime_reduction_enabled = 0",
    "runtime_pr_allowed = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A is allowed only with explicit user scoped acceptance.",
    "Path B is allowed only as an implementation-ready spec before runtime code.",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_spec_checkpoint_defined = 1",
    "path_b_runtime_implementation_allowed = 0",
    "## Implementation-Ready Spec Requirements",
    "encoded query layout",
    "encoded target layout",
    "scoring config key",
    "scoreInfo-compatible scoring mode",
    "candidate ordering rule",
    "skipped scoreInfo upper bound",
    "skipped attempt score upper bound",
    "skipped attempt nt upper bound",
    "skipped attempt identity upper bound",
    "skipped attempt stability upper bound",
    "task output capacity",
    "scoreInfo-local break-state",
    "selected replay attempts",
    "skipped-work certificate",
    "fail-closed fallback counters",
    "proof telemetry",
    "## First1 Gate",
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
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "## First64 Broad Gate",
    "first64_may_run_only_after_first1_passes = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "same equality/reduction/accounting gates as first1",
    "## Runtime Authority",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "## Current Decision",
    "next_valid_gate = phase7_new_gpu_engine_first1_spec_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_first1_spec_or_path_a_acceptance",
    "current_path = Path B",
    "current_phase = Phase 7",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine spec-or-Path-A phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_pr_allowed = 1",
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_runtime_implementation_allowed = 1",
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
            "new GPU engine spec-or-Path-A checkpoint contains forbidden phrase: "
            + forbidden
        )

prev_text = prev.read_text(encoding="utf-8")
if "next_valid_gate = phase7_new_gpu_engine_spec_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous checkpoint no longer points to this gate")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md"
for path in [phase_driver, roadmap]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link new GPU engine spec-or-Path-A checkpoint")

print("phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance=defined")
print("path_a_user_acceptance_recorded=0")
print("path_a_scoped_completion_may_close_goal=0")
print("path_b_spec_checkpoint_defined=1")
print("path_b_runtime_implementation_allowed=0")
print("runtime_pr_allowed=0")
print("next_valid_gate=phase7_new_gpu_engine_first1_spec_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_first1_spec_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
