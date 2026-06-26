#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CLOSE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_close_plan.md"

python3 - "$DOC" "$ROADMAP" "$CLOSE_PLAN" <<'PY'
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
    "# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Consumer Summary Prefix No-Go",
    "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded",
    "runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1",
    "implementation_shape = gpu_prefix_attempt_descriptors_per_scoreinfo",
    "new_cuda_api = prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors",
    "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY_PREFIX_ATTEMPTS",
    "external_output_comparison_authority = 1",
    "prefix = 1:",
    "external_digest_match = 0",
    "candidate_lite_rows = 25",
    "gpu_selected_attempts = 718",
    "prefix = 2:",
    "candidate_lite_rows = 23",
    "gpu_selected_attempts = 1436",
    "prefix = 3:",
    "candidate_lite_rows = 20",
    "gpu_selected_attempts = 2154",
    "prefix = 4:",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "gpu_selected_attempts = 2872",
    "selected_prefix_attempts = 2872",
    "candidate_align_attempts = 2008",
    "v5_candidate_align_attempts = 2872",
    "prefix = 5:",
    "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
    "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
    "gpu_selected_attempts < v5_candidate_align_attempts = 0",
    "selected_prefix_attempts < v5_candidate_align_attempts = 0",
    "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0",
    "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0",
    "do_not_run_first64_from_this_probe = 1",
    "do_not_add_broad_replacement_row_from_this_probe = 1",
    "next_required_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit("missing stronger prefix no-go phrase(s):\n" + "\n".join(missing))

for forbidden in [
    "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 1",
    "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_replacement workload matrix promotion = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"forbidden phrase found: {forbidden}")

link = "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md"
if link not in roadmap.read_text(encoding="utf-8"):
    raise SystemExit("roadmap does not link stronger prefix no-go checkpoint")
if link not in close_plan.read_text(encoding="utf-8"):
    raise SystemExit("close plan does not link stronger prefix no-go checkpoint")

print("phase7_post_v5_3_stronger_consumer_summary_prefix_no_go=recorded")
print("phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass=0")
print("next_required_gate=different_gpu_execution_design_or_path_a_scope_decision")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
