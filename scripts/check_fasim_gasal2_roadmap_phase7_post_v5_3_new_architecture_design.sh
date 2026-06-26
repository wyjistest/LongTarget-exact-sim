#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md"
DECISION="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_architecture_decision.md"

python3 - "$DOC" "$DECISION" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
decision = Path(sys.argv[2])
for path in [doc, decision]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
decision_flat = " ".join(decision.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New Architecture Design",
    "phase7_post_v5_3_new_architecture_design = defined",
    "phase7_post_v5_3_design_family = gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay",
    "previous_status = stopped_no_go",
    "runtime_default = off",
    "candidate_vs_baseline = 0.706009",
    "missing_required_attempts = 624",
    "fallback_accounting_clean = 0",
    "gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay",
    "compact_task_consumer_summary_plus_selected_attempts",
    "differs_from_v5_descriptor_replay = 1",
    "no_full_descriptor_replay = 1",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "selected_attempts_must_be_less_than_v5_candidate_attempts = 1",
    "coverage_accounting_must_be_clean_before_broad_claim = 1",
    "gpu_selected_attempts < v5_candidate_align_attempts",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1",
    "post_v5_3_gpu_consumer_summary_first1_smoke",
    "phase7_post_v5_3_new_architecture_may_implement = 1",
    "phase7_post_v5_3_new_architecture_may_claim_completion = 0",
    "next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit(
        "missing post-v5.3 new architecture design phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "phase7_post_v5_3_architecture_decision = defined",
    "phase7_post_v5_3_current_v5_status = stopped_no_go",
    "path_b_new_broad_architecture_required = 1",
]:
    if phrase not in decision_flat:
        raise SystemExit(f"missing post-v5.3 decision phrase: {phrase}")

for forbidden in [
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "phase7_post_v5_3_new_architecture_may_claim_completion = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"new architecture design contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_new_architecture_design=defined")
print("phase7_post_v5_3_design_family=gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay")
print("phase7_post_v5_3_new_architecture_may_implement=1")
print("phase7_post_v5_3_new_architecture_may_claim_completion=0")
print("next_required_gate=post_v5_3_gpu_consumer_summary_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
