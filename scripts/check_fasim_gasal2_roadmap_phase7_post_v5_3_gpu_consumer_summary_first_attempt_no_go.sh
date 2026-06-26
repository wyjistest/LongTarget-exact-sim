#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CLOSE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_close_plan.md"

python3 - "$DOC" "$ROADMAP" "$CLOSE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
close_plan = Path(sys.argv[3])

for path in [doc, roadmap, close_plan]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 GPU Consumer Summary First-Attempt No-Go",
    "phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go = recorded",
    "runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1",
    "workload = NEAT1 first1",
    "implementation_shape = first_descriptor_per_scoreinfo_gpu_summary",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "gpu_selected_attempts = 718",
    "reference_align_attempts = 2872",
    "candidate_align_attempts = 718",
    "v5_candidate_align_attempts = 2872",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "baseline_lite_rows = 19",
    "candidate_lite_rows = 25",
    "8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437",
    "9658ddf83036fd501d8dc1097ccce38f2e5c5b18212f59e9e110bb46614cc5a1",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "gate_first1_pass = 0",
    "internal_digest_match_claim_trusted = 0",
    "internal_full_rows_equal_claim_trusted = 0",
    "external_output_comparison_authority = 1",
    "first_descriptor_per_scoreinfo_preserves_output = 0",
    "first_descriptor_per_scoreinfo_may_continue_as_gate_v5_5 = 0",
    "phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go",
    "phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass = 0",
    "phase7_post_v5_3_gpu_consumer_summary_may_claim_completion = 0",
    "do_not_run_first64_from_this_probe = 1",
    "do_not_add_broad_replacement_row_from_this_probe = 1",
    "next_required_gate = stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance",
    "required_next_design_property = prefix_boundary_or_equivalent_replay_proof",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit(
        "missing post-v5.3 first-attempt no-go phrase(s):\n" +
        "\n".join(missing)
    )

for forbidden in [
    "first_descriptor_per_scoreinfo_preserves_output = 1",
    "first_descriptor_per_scoreinfo_may_continue_as_gate_v5_5 = 1",
    "phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass = 1",
    "phase7_post_v5_3_gpu_consumer_summary_may_claim_completion = 1",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "do_not_add_broad_replacement_row_from_this_probe = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"forbidden first-attempt no-go phrase present: {forbidden}")

roadmap_text = roadmap.read_text(encoding="utf-8")
close_plan_text = close_plan.read_text(encoding="utf-8")
link = "docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md"
if link not in roadmap_text:
    raise SystemExit("roadmap does not mention first-attempt no-go doc")
if "post_v5_3_stronger_consumer_summary_first1_smoke_or_path_a_acceptance" not in close_plan_text:
    raise SystemExit("close plan does not point to the stronger summary runtime gate")
if "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md" not in close_plan_text:
    raise SystemExit("close plan does not link stronger summary design")

print("phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go=recorded")
print("phase7_post_v5_3_gpu_consumer_summary_first_attempt_status=no_go")
print("phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass=0")
print("next_required_gate=stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
