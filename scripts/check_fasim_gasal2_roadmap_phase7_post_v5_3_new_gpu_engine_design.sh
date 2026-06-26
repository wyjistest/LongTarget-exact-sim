#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md"
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
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Design",
    "phase7_post_v5_3_new_gpu_engine_design = defined",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md",
    "previous_status = path_b_runtime_pr_allowed_0",
    "runtime_default = off",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "design_family = fasim_compatible_gpu_scoreinfo_attempt_engine",
    "not_gasal2_align_replacement = 1",
    "not_current_descriptor_stream_continuation = 1",
    "requires_fasim_byte_saturation_semantics = 1",
    "requires_scoreinfo_window_of_5_cluster_semantics = 1",
    "requires_candidate_attempt_order_equivalence = 1",
    "requires_pre_d2h_output_inert_certificate = 1",
    "requires_cpu_authority_replay = 1",
    "requires_scoreinfo_prealign_reduction = 1",
    "requires_align_side_reduction = 1",
    "requires_full_row_digest_equality = 1",
    "current_runtime_implementation_available = 0",
    "runtime_pr_allowed = 0",
    "docs_spec_checkpoint_only = 1",
    "next_valid_gate = phase7_new_gpu_engine_spec_or_path_a_acceptance",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "first1_spec_gate_required = 1",
    "first64_broad_gate_required = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine design phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first64_runtime_allowed = 1",
    "current_runtime_implementation_available = 1",
    "runtime_pr_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"new GPU engine design contains forbidden phrase: {forbidden}")

prev_text = prev.read_text(encoding="utf-8")
if "path_b_runtime_pr_allowed = 0" not in prev_text:
    raise SystemExit("previous checkpoint no longer blocks Path B runtime PR")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md"
if link not in roadmap.read_text(encoding="utf-8"):
    raise SystemExit(f"roadmap does not link {link}")

print("phase7_post_v5_3_new_gpu_engine_design=defined")
print("design_family=fasim_compatible_gpu_scoreinfo_attempt_engine")
print("runtime_pr_allowed=0")
print("current_runtime_implementation_available=0")
print("next_valid_gate=phase7_new_gpu_engine_spec_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
