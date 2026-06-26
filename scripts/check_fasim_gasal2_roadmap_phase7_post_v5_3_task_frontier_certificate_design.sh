#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md"
NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md"

python3 - "$DOC" "$NO_GO" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
no_go = Path(sys.argv[2])
for path in [doc, no_go]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
no_go_flat = " ".join(no_go.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Task-Frontier Certificate Design",
    "phase7_post_v5_3_task_frontier_certificate_design = defined",
    "phase7_post_v5_3_task_frontier_certificate_status = design_only",
    "phase7_post_v5_3_task_frontier_certificate_may_implement = 1",
    "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0",
    "previous_status = fixed_prefix_consumer_summary_no_go",
    "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
    "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
    "phase7_post_v5_3_design_family = gpu_task_frontier_certificate_with_cpu_authority_replay",
    "legacy-byte CUDA scoreInfo / attempt descriptor stream",
    "emit a compact task-frontier certificate",
    "differs_from_v5_descriptor_replay = 1",
    "differs_from_fixed_prefix_summary = 1",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "task_frontier_score_bound",
    "task_frontier_nt_bound",
    "task_frontier_stability_bound",
    "fallback_to_full_replay",
    "selected_attempt_count < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1",
    "next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke",
    "source_is_pre_scoreinfo = 1",
    "source_is_legacy_byte_cuda = 1",
    "gasal2_score_only_long_query_dependency = 0",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreinfo = 0",
    "fixed_prefix_per_scoreinfo = 0",
    "task_frontier_certificate_rows > 0",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "digest_match = 1",
    "full_rows_equal = 1",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "do_not_run_first64_until_first1_gate_pass = 1",
    "contract = broad_replacement",
    "phase7_post_v5_3_task_frontier_certificate_status = design_only",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit(
        "missing task-frontier certificate design phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded",
    "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0",
    "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
    "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
]:
    if phrase not in no_go_flat:
        raise SystemExit(f"missing prefix no-go phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"task-frontier design contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_task_frontier_certificate_design=defined")
print("phase7_post_v5_3_task_frontier_certificate_status=design_only")
print("phase7_post_v5_3_task_frontier_certificate_may_implement=1")
print("phase7_post_v5_3_task_frontier_certificate_may_claim_completion=0")
print("phase7_post_v5_3_design_family=gpu_task_frontier_certificate_with_cpu_authority_replay")
print("next_required_gate=post_v5_3_task_frontier_certificate_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
