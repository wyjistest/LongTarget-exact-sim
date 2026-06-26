#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_finish_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_phase_roadmap.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
phase_roadmap = Path(sys.argv[3])

for path in [doc, roadmap, phase_roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Goal Completion Finish Plan",
    "This document is the current execution plan for making the active",
    "It is not a success claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A - scoped completion:",
    "Path B - broad completion:",
    "current_phase:",
    "Phase 7 - post-v5.3 broad replacement restart.",
    "current_gate:",
    "different_gpu_execution_design_or_path_a_scope_acceptance.",
    "current_runtime_env:",
    "FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1",
    "first task-frontier certificate producer ran.",
    "first attempt reduced attempts but changed output.",
    "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md",
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md",
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Decision",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
    "### Phase 7a: Task-Frontier Certificate First1",
    "### Phase 7b: First64 Broad Characterization",
    "### Phase 7c: Workload-Matrix Promotion",
    "gpu_task_frontier_certificate_with_cpu_authority_replay",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "source_is_pre_scoreinfo = 1",
    "source_is_legacy_byte_cuda = 1",
    "gasal2_score_only_long_query_dependency = 0",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreinfo = 0",
    "fixed_prefix_per_scoreinfo = 0",
    "task_frontier_certificate_rows > 0",
    "gpu_selected_attempts < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "digest_match = 1",
    "full_rows_equal = 1",
    "triplex_mismatches = 0",
    "gate_first1_pass = 1",
    "do not run first64 before first1 passes",
    "do not promote broad_replacement before first64 passes",
    "make check-fasim-gasal2-roadmap-finish-plan",
    "new pre-D2H output-inert proof",
    "proof_search_rows, task_count, scoreinfo_count, and attempt_count",
    "first1 pre-D2H proof-search export is recorded",
    "proof acceptance audit found no accepted pre-D2H proof family",
    "keep runtime_reduction_enabled = 0",
    "do not implement the current stronger task-frontier runtime as-is",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing finish plan phrase(s):\n" + "\n".join(missing))

phase_order = [
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Decision",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("finish plan phase headings are out of order")

for forbidden in [
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "top5-only evidence closes broad objective",
    "archive-only evidence closes broad objective",
]:
    if forbidden in text:
        raise SystemExit(f"finish plan contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_finish_plan.md"
for path in [roadmap, phase_roadmap]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link {link}")

no_go_link = (
    "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_"
    "first_attempt_no_go.md"
)
if no_go_link not in text:
    raise SystemExit("finish plan does not link task-frontier first-attempt no-go")

stronger_link = (
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_"
    "certificate_design.md"
)
if stronger_link not in text:
    raise SystemExit("finish plan does not link stronger task-frontier design")

print("finish_plan_document=present")
print("finish_plan_current_phase=phase7")
print("finish_plan_current_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("finish_plan_path_a_requires_user_acceptance=1")
print("finish_plan_path_b_requires_new_proof_or_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
