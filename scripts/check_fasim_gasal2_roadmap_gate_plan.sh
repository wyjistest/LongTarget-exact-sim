#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_gate_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])

for path in [doc, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Goal Completion Gate Plan",
    "This is the short execution plan for making the active GASAL2/Fasim goal closable.",
    "It is a plan, not a completion claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A: scoped completion",
    "Path B: broad completion",
    "Path B is active unless the user explicitly accepts Path A.",
    "current_phase:",
    "Phase 7 - Post-v5.3 Broad Replacement Restart",
    "current_gate:",
    "different_gpu_execution_design_or_path_a_scope_acceptance",
    "current_next_work:",
    "design a different GPU execution design or record Path A scoped completion acceptance",
    "do not implement the current stronger task-frontier runtime as-is",
    "keep runtime_reduction_enabled = 0",
    "current proof acceptance audit has accepted_pre_d2h_proof_families = 0",
    "do not run first64 or reducing runtime from the current proof-search export",
    "no broad_replacement workload row before a first64 broad gate passes",
    "no first64 run from the failed first-descriptor-per-scoreInfo probe",
    "write a no-go checkpoint for this architecture",
    "## Phase Plan",
    "### Phase 0: Reproducibility",
    "### Phase 1: Scoped Product Decision",
    "### Phase 2: Full-Output Equivalence Baseline",
    "### Phase 3: Pre-Convert CPU Reduction",
    "### Phase 4: Sort/Top-N Optimization",
    "### Phase 5: Archive Artifact",
    "### Phase 6: Workload Matrix",
    "### Phase 7: Broad Replacement Restart",
    "### Phase 8: Completion Decision",
    "Gate v5.1:",
    "true pre-scoreInfo descriptor source first1 smoke passed",
    "Gate v5.2:",
    "CPU-authority replay first1 smoke passed",
    "Gate v5.3:",
    "first64 CPU-authority replay was correctness-clean but performance no-go",
    "Gate v5.5 first attempt:",
    "first_descriptor_per_scoreInfo reduced attempts",
    "external output comparison failed",
    "first_descriptor_per_scoreInfo is stopped",
    "Gate v5.5 fixed-prefix attempt:",
    "prefix 1/2/3 reduced GPU-selected attempts but changed output",
    "prefix 4/5 preserved output but did not reduce GPU-selected attempts",
    "fixed-prefix consumer summary is stopped",
    "pre_d2h_output_inert_proof_search_first1_export",
    "make build-fasim-gasal2",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design",
    "Gate v5.6 task-frontier first1 passes only if:",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreInfo = 0",
    "fixed_prefix_per_scoreInfo = 0",
    "external_full_rows_equal = 1",
    "external_digest_match = 1",
    "gpu_selected_attempts < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "Gate v5.7 first64 passes only if:",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo/preAlign work reduced or replaced",
    "Align-side work reduced or replaced",
    "fallback_accounting_clean = true",
    "write a no-go checkpoint for this architecture",
    "add exactly one contract=broad_replacement row to the workload matrix",
    "goal_completion_status = not_complete",
    "## Immediate Next Steps",
]

missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit("missing gate-plan phrase(s):\n" + "\n".join(missing))

phase_order = [
    "### Phase 0: Reproducibility",
    "### Phase 1: Scoped Product Decision",
    "### Phase 2: Full-Output Equivalence Baseline",
    "### Phase 3: Pre-Convert CPU Reduction",
    "### Phase 4: Sort/Top-N Optimization",
    "### Phase 5: Archive Artifact",
    "### Phase 6: Workload Matrix",
    "### Phase 7: Broad Replacement Restart",
    "### Phase 8: Completion Decision",
]
positions = [text.index(item) for item in phase_order]
if positions != sorted(positions):
    raise SystemExit("gate-plan phase order is invalid")

for forbidden in [
    "top5-only evidence may close the broad objective",
    "archive-only evidence may close the broad objective",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "may add a broad_replacement workload row before v5.3 passes",
    "Gate v5.3: first64 broad gate",
]:
    if forbidden in flat:
        raise SystemExit(f"gate-plan contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_gate_plan.md"
if link not in roadmap_text:
    raise SystemExit(f"roadmap does not link {link}")

print("gate_plan_document=present")
print("gate_plan_current_phase=phase7")
print("gate_plan_current_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("gate_plan_path_a_requires_user_acceptance=1")
print("gate_plan_path_b_requires_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
