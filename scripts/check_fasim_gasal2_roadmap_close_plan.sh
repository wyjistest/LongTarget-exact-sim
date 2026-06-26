#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_close_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
RUNBOOK="$ROOT/docs/fasim_gasal2_goal_completion_runbook.md"
CHECKLIST="$ROOT/docs/fasim_gasal2_goal_completion_phase_checklist.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
PHASE_ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_phase_roadmap.md"

python3 - "$DOC" "$ROADMAP" "$RUNBOOK" "$CHECKLIST" "$PHASE_PLAN" "$PHASE_ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
linked = [Path(path) for path in sys.argv[2:]]

for path in [doc, *linked]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Goal Completion Close Plan",
    "This document is the canonical phase plan for making the active Fasim/GASAL2 goal closable.",
    "It is not a completion claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "## Current Cursor",
    "current_path:",
    "Path B remains active unless the user explicitly accepts Path A.",
    "current_phase:",
    "Phase 7 - Post-v5.3 Broad Replacement Restart",
    "current_gate:",
    "different_gpu_execution_design_or_path_a_scope_acceptance",
    "current_next_pr:",
    "fasim: design different GPU execution design or scope acceptance",
    "current_checkpoint:",
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md",
    "current stronger task-frontier runtime is not allowed as-is",
    "current proof-search export must not reduce runtime",
    "current proof acceptance audit found no accepted pre-D2H proof family",
    "first64 and reducing runtime are not allowed from this proof-search export",
    "do not promote a broad_replacement row before a first64 broad gate passes",
    "do not close from top5-only or archive-only evidence",
    "do not count output drift as speedup",
    "do not rebrand v4/v5 host-visible replay as the post-v5.3 design",
    "do not make GASAL2/GPU endpoint/CIGAR/traceback/output/digest authority",
    "## Phase Index",
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Contract",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
    "### Gate v5.0: Descriptor-Emission Design",
    "### Gate v5.1: True Pre-ScoreInfo Descriptor Source",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =",
    "gate_v5_1_pass_first1",
    "### Gate v5.2: CPU-Authority Replay First1",
    "Use v5.1 descriptors as the attempt source",
    "make check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "candidate_align_attempts < reference_align_attempts",
    "gate_v5_2_pass = 1",
    "### Gate v5.3: First64 Broad Gate",
    "phase7_broad_restart_v5_cpu_authority_replay_first64_status =",
    "first64_correctness_clean_performance_no_go",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo/preAlign work reduced or replaced",
    "Align-side work reduced or replaced",
    "fallback_accounting_clean = true",
    "### Gate v5.4: Workload-Matrix Promotion",
    "add contract=broad_replacement only after a future broad gate passes",
    "### Gate v5.5: Post-v5.3 Long-Query-Safe Consumer Summary First1",
    "Prove a new Path B shape that reduces consumer work before host transfer",
    "docs/fasim_gasal2_phase7_post_v5_3_long_query_safe_consumer_summary_design.md",
    "gasal2_score_only_long_query_dependency = 0",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "gate_first1_pass = 1",
    "implementation_shape = first_descriptor_per_scoreinfo_gpu_summary",
    "baseline_lite_rows = 19",
    "candidate_lite_rows = 25",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go",
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md",
    "phase7_post_v5_3_stronger_consumer_summary_design = defined",
    "phase7_post_v5_3_stronger_consumer_summary_status = design_only",
    "required_next_design_property = prefix_boundary_or_equivalent_replay_proof",
    "next_required_gate = post_v5_3_stronger_consumer_summary_first1_smoke",
    "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md",
    "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded",
    "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
    "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
    "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0",
    "next_required_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "### Gate v5.6: Post-v5.3 Task-Frontier Certificate First1",
    "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md",
    "phase7_post_v5_3_task_frontier_certificate_design = defined",
    "phase7_post_v5_3_task_frontier_certificate_status = design_only",
    "next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke",
    "uses_task_frontier_certificate = 1",
    "uses_prefix_boundary_only = 0",
    "fixed_prefix_per_scoreinfo = 0",
    "current_stronger_task_frontier_first1_smoke_allowed = 0",
    "### Gate v5.7: Post-v5.3 First64 Broad Characterization",
    "### Gate v5.8: Post-v5.3 Workload-Matrix Promotion",
    "pre-D2H proof-search first1 export;",
    "proof acceptance audit; no reducing runtime until this passes",
    "reducing runtime first1 only after a pre-D2H proof passes",
    "## Immediate Execution Order",
    "## Minimal PR Units",
]

missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit("missing close-plan phrase(s):\n" + "\n".join(missing))

phase_order = [
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Contract",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
]
positions = [text.index(item) for item in phase_order]
if positions != sorted(positions):
    raise SystemExit("close-plan phase order is invalid")

gate_order = [
    "### Gate v5.0: Descriptor-Emission Design",
    "### Gate v5.1: True Pre-ScoreInfo Descriptor Source",
    "### Gate v5.2: CPU-Authority Replay First1",
    "### Gate v5.3: First64 Broad Gate",
    "### Gate v5.4: Workload-Matrix Promotion",
    "### Gate v5.5: Post-v5.3 Long-Query-Safe Consumer Summary First1",
    "### Gate v5.6: Post-v5.3 Task-Frontier Certificate First1",
    "### Gate v5.7: Post-v5.3 First64 Broad Characterization",
    "### Gate v5.8: Post-v5.3 Workload-Matrix Promotion",
]
gate_positions = [text.index(item) for item in gate_order]
if gate_positions != sorted(gate_positions):
    raise SystemExit("close-plan v5 gate order is invalid")

for forbidden in [
    "top5-only evidence may close the broad objective",
    "archive-only evidence may close the broad objective",
    "v4 host-visible scoreInfo replay may close the goal",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "may run first64 before v5.2 first1 passes",
]:
    if forbidden in flat:
        raise SystemExit(f"close-plan contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_close_plan.md"
for path in linked:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link {link}")

print("close_plan_document=present")
print("close_plan_current_phase=phase7")
print("close_plan_current_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("close_plan_path_a_requires_user_acceptance=1")
print("close_plan_path_b_requires_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
