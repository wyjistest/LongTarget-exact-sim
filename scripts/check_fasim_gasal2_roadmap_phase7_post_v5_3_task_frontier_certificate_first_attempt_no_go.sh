#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
FINISH_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_finish_plan.md"

python3 - "$DOC" "$ROADMAP" "$FINISH_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
finish_plan = Path(sys.argv[3])

for path in [doc, roadmap, finish_plan]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Task-Frontier Certificate First-Attempt No-Go",
    "phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go = recorded",
    "runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1",
    "implementation_shape = first_scoreinfo_group_per_task_certificate_probe",
    "prealign_cuda_emit_legacy_byte_task_frontier_certificate_descriptors",
    "requested = 1",
    "active = 1",
    "source_is_pre_scoreinfo = 1",
    "source_is_legacy_byte_cuda = 1",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreinfo = 0",
    "fixed_prefix_per_scoreinfo = 0",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "task_frontier_certificate_rows = 48",
    "gpu_selected_attempts = 192",
    "reference_align_attempts = 2872",
    "candidate_align_attempts = 138",
    "v5_candidate_align_attempts = 2872",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "baseline_lite_rows = 19",
    "candidate_lite_rows = 2",
    "missing_rows = 17",
    "extra_rows = 0",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "gate_first1_pass = 0",
    "phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go",
    "phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0",
    "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0",
    "do_not_run_first64_from_this_probe = 1",
    "do_not_add_broad_replacement_row_from_this_probe = 1",
    "next_required_gate = stronger_task_frontier_certificate_design_or_path_a_acceptance",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing task-frontier first-attempt no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 1",
    "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 1",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
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

link = "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md"
for path in [roadmap, finish_plan]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link task-frontier first-attempt no-go")

print("phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go=recorded")
print("phase7_post_v5_3_task_frontier_certificate_first1_gate_pass=0")
print("next_required_gate=stronger_task_frontier_certificate_design_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
