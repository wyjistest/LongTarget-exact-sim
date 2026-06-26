#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md"
FEASIBILITY="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_EXEC="$ROOT/docs/fasim_gasal2_goal_completion_phase_execution_plan.md"

python3 - "$DOC" "$FEASIBILITY" "$ROADMAP" "$PHASE_EXEC" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
feasibility = Path(sys.argv[2])
roadmap = Path(sys.argv[3])
phase_exec = Path(sys.argv[4])

for path in [doc, feasibility, roadmap, phase_exec]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Pre-D2H Output-Inert Proof Search Design",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = design_only",
    "previous_status = stronger_task_frontier_certificate_feasibility_no_go",
    "runtime_default = off",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 0",
    "do_not_implement_current_stronger_task_frontier_runtime = 1",
    "pre-D2H proof",
    "CPU output labels only for offline discovery",
    "future runtime proof may not depend on final CPU output after replay",
    "score upper bound dominance",
    "target-end fallback impossibility",
    "task-local output capacity dominance",
    "first scoreInfo group per task",
    "fixed prefix per scoreInfo",
    "arbitrary sparse subset",
    "final CPU output membership",
    "FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1",
    "next_required_gate = pre_d2h_output_inert_proof_search_first1_export",
    "proof_search_rows > 0",
    "label_source = cpu_authority_external_output",
    "runtime_reduction_enabled = 0",
    "candidate_proof_false_negatives = 0",
    "candidate_selected_attempts < v5_candidate_align_attempts",
    "candidate_uses_final_cpu_output_as_runtime_proof = 0",
    "first64_runtime_reduction_enabled = 0",
    "real reduction",
    "broad_replacement workload matrix row",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
    "GPU output authority",
    "GPU digest authority",
    "no pre-D2H proof family has false negatives = 0",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing pre-D2H proof search design phrase(s):\n"
        + "\n".join(missing)
    )

feasibility_flat = " ".join(feasibility.read_text(encoding="utf-8").split())
for phrase in [
    "phase7_post_v5_3_stronger_task_frontier_certificate_feasibility = no_go",
    "do_not_implement_current_stronger_task_frontier_runtime = 1",
    "new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision",
]:
    if phrase not in feasibility_flat:
        raise SystemExit(f"feasibility checkpoint missing phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 1",
    "runtime_reduction_enabled = 1",
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

link = "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md"
for path in [roadmap, phase_exec]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link proof-search design")

print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_design=defined")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_status=design_only")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement=1")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion=0")
print("next_required_gate=pre_d2h_output_inert_proof_search_first1_export")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
