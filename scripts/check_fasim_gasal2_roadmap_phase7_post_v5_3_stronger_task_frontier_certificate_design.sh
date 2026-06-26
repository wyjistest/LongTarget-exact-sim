#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md"
NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
FINISH_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_finish_plan.md"

python3 - "$DOC" "$NO_GO" "$ROADMAP" "$FINISH_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
no_go = Path(sys.argv[2])
roadmap = Path(sys.argv[3])
finish_plan = Path(sys.argv[4])

for path in [doc, no_go, roadmap, finish_plan]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
no_go_flat = " ".join(no_go.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Task-Frontier Certificate Design",
    "phase7_post_v5_3_stronger_task_frontier_certificate_design = defined",
    "phase7_post_v5_3_stronger_task_frontier_certificate_status = design_only",
    "phase7_post_v5_3_stronger_task_frontier_certificate_may_implement = 1",
    "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0",
    "previous_status = first_scoreinfo_group_per_task_certificate_no_go",
    "task_frontier_certificate_rows = 48",
    "gpu_selected_attempts = 192",
    "v5_candidate_align_attempts = 2872",
    "candidate_align_attempts = 138",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "missing_rows = 17",
    "first_scoreinfo_group_per_task = 1",
    "scoreinfo_group_selection_without_output_bound = 1",
    "task_frontier_certificate_rows_without_skipped_group_proof = 1",
    "skipped_scoreinfo_score_upper_bound",
    "skipped_attempt_score_upper_bound",
    "skipped_attempt_nt_upper_bound",
    "skipped_attempt_identity_upper_bound",
    "skipped_attempt_stability_upper_bound",
    "fallback_to_full_replay = 1 if any skipped group could affect output",
    "differs_from_first_scoreinfo_group_probe = 1",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreinfo = 0",
    "fixed_prefix_per_scoreinfo = 0",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "external_output_comparison_authority = 1",
    "FASIM_GASAL2_PHASE7_POST_V5_3_STRONGER_TASK_FRONTIER_CERTIFICATE=1",
    "next_required_gate = stronger_task_frontier_certificate_first1_smoke",
    "fallback_to_full_replay = 0",
    "gpu_selected_attempts < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "gate_first1_pass = 1",
    "do_not_run_first64_until_stronger_task_frontier_first1_pass = 1",
    "the proof depends on final CPU output after replay",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing stronger task-frontier design phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go",
    "phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0",
    "external_digest_match = 0",
    "missing_rows = 17",
]:
    if phrase not in no_go_flat:
        raise SystemExit(f"missing first-attempt no-go phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_replacement workload matrix promotion = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"forbidden phrase found: {forbidden}")

link = "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md"
for path in [roadmap, finish_plan]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link stronger task-frontier design")

print("phase7_post_v5_3_stronger_task_frontier_certificate_design=defined")
print("phase7_post_v5_3_stronger_task_frontier_certificate_status=design_only")
print("phase7_post_v5_3_stronger_task_frontier_certificate_may_implement=1")
print("phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion=0")
print("next_required_gate=stronger_task_frontier_certificate_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
