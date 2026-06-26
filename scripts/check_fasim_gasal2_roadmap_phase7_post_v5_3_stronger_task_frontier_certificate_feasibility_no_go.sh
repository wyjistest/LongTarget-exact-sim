#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md"
FIRST_NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md"
PREFIX_NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_EXEC="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"

python3 - "$DOC" "$DESIGN" "$FIRST_NO_GO" "$PREFIX_NO_GO" "$ROADMAP" "$PHASE_EXEC" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
design = Path(sys.argv[2])
first_no_go = Path(sys.argv[3])
prefix_no_go = Path(sys.argv[4])
roadmap = Path(sys.argv[5])
phase_exec = Path(sys.argv[6])

for path in [doc, design, first_no_go, prefix_no_go, roadmap, phase_exec]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Task-Frontier Certificate Feasibility No-Go",
    "phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go = recorded",
    "phase7_post_v5_3_stronger_task_frontier_certificate_status = feasibility_no_go",
    "FASIM_GASAL2_PHASE7_POST_V5_3_STRONGER_TASK_FRONTIER_CERTIFICATE=1",
    "runtime_default = off",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "previous_implementation_shape = first_scoreinfo_group_per_task_certificate_probe",
    "task_frontier_certificate_rows = 48",
    "gpu_selected_attempts = 192",
    "v5_candidate_align_attempts = 2872",
    "candidate_align_attempts = 138",
    "reference_align_attempts = 2872",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "missing_rows = 17",
    "gate_first1_pass = 0",
    "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
    "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
    "skipped_scoreinfo_score_upper_bound",
    "skipped_attempt_score_upper_bound",
    "scoreInfo.score alone is not an output-inert proof",
    "fixed prefix is not an output-inert proof",
    "first scoreInfo group per task is not an output-inert proof",
    "final CPU output after replay is not an allowed safety proof",
    "fallback_to_full_replay = 1",
    "phase7_post_v5_3_stronger_task_frontier_certificate_feasibility = no_go",
    "phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 0",
    "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0",
    "do_not_implement_current_stronger_task_frontier_runtime = 1",
    "do_not_run_first64_from_current_stronger_task_frontier_design = 1",
    "do_not_add_broad_replacement_row_from_current_stronger_task_frontier = 1",
    "new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "candidate_vs_baseline > 1.0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "goal completion claim = 0",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing stronger task-frontier feasibility no-go phrase(s):\n"
        + "\n".join(missing)
    )

for source, phrases in {
    design: [
        "phase7_post_v5_3_stronger_task_frontier_certificate_design = defined",
        "next_required_gate = stronger_task_frontier_certificate_first1_smoke",
    ],
    first_no_go: [
        "phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go",
        "external_digest_match = 0",
        "missing_rows = 17",
    ],
    prefix_no_go: [
        "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded",
        "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
        "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
    ],
}.items():
    source_flat = " ".join(source.read_text(encoding="utf-8").split())
    for phrase in phrases:
        if phrase not in source_flat:
            raise SystemExit(f"{source} missing supporting phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 1",
    "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 1",
    "do_not_implement_current_stronger_task_frontier_runtime = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_replacement workload matrix promotion = 1",
    "goal completion claim = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"forbidden phrase found: {forbidden}")

link = (
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_"
    "feasibility_no_go.md"
)
for path in [roadmap, phase_exec]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link feasibility no-go checkpoint")

print("phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go=recorded")
print("phase7_post_v5_3_stronger_task_frontier_certificate_status=feasibility_no_go")
print("phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed=0")
print("next_required_gate=new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
