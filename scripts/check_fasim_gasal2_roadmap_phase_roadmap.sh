#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_phase_roadmap.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CHECKLIST="$ROOT/docs/fasim_gasal2_goal_completion_phase_checklist.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
RUNBOOK="$ROOT/docs/fasim_gasal2_goal_completion_runbook.md"

python3 - "$DOC" "$ROADMAP" "$CHECKLIST" "$PHASE_PLAN" "$RUNBOOK" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
checklist = Path(sys.argv[3])
phase_plan = Path(sys.argv[4])
runbook = Path(sys.argv[5])

for path in [doc, roadmap, checklist, phase_plan, runbook]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
linked_text = "\n".join(
    path.read_text(encoding="utf-8")
    for path in [roadmap, checklist, phase_plan, runbook]
)

required = [
    "# Fasim GASAL2 Goal Completion Phase Roadmap",
    "This document defines the phase-by-phase route for completing the active",
    "It is a close plan, not a success claim.",
    "There are only two valid ways to complete the goal.",
    "Path A: scoped completion",
    "Path B: broad completion",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "## Phase Cursor",
    "Current path:",
    "Path B is active unless the user explicitly accepts Path A scoped completion.",
    "Current phase:",
    "Phase 7, broad replacement restart.",
    "Current executable subphase:",
    "Gate v5.3 first64 broad characterization completed as no-go.",
    "Current implementation target:",
    "v5.3 first64 no-go, fixed-prefix no-go, and first task-frontier certificate no-go checkpoints are recorded.",
    "The stronger task-frontier certificate feasibility checkpoint is also no-go.",
    "The selected proof-family or scope decision checkpoint is defined.",
    "The next Path B step is a new pre-D2H proof-family first1 smoke, unless Path A scoped completion is accepted.",
    "Current validation target:",
    "different_gpu_execution_design_or_path_a_scope_acceptance.",
    "Current forbidden shortcut:",
    "Do not close the goal from top5-only, archive-only, v4 host-visible scoreInfo replay, output-drift, or fallback-heavy evidence.",
    "Phase 0:",
    "Phase 1:",
    "Phase 2:",
    "Phase 3:",
    "Phase 4:",
    "Phase 5:",
    "Phase 6:",
    "Phase 7:",
    "Phase 8:",
    "## Phase Summary",
    "## Phase 0: Reproducibility",
    "## Phase 1: Scoped Product Contract",
    "## Phase 2: Full-Output Equivalence Baseline",
    "## Phase 3: Pre-Convert CPU Reduction",
    "## Phase 4: Sort/Top-N Optimization",
    "## Phase 5: Archive Artifact",
    "## Phase 6: Workload Matrix",
    "## Phase 7: Broad Replacement Restart",
    "## Phase 8: Completion Decision",
    "### Gate v5.0: Design Checkpoint",
    "### Gate v5.1: True Pre-ScoreInfo Descriptor Source",
    "### Gate v5.2: CPU-Authority Replay",
    "### Gate v5.3: First64 Broad Gate",
    "### Gate v5.4: Workload-Matrix Promotion",
    "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design",
    "make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke",
    "source_is_pre_scoreinfo = 1",
    "scoreinfo_prealign_reduced = 1",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "gate_v5_1_pass = 1",
    "full_rows_equal = true",
    "digest_match = true",
    "triplex_mismatches = 0",
    "candidate_align_attempts < reference_align_attempts",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo/preAlign work reduced or replaced",
    "Align-side work reduced or replaced",
    "fallback_accounting_clean = true",
    "claimed_broad_replacement_rows > 0",
    "## Minimal PR Units",
    "PR unit for Phase 7 v5.1:",
    "PR unit for Phase 7 v5.2:",
    "PR unit for Phase 7 v5.3:",
    "PR unit for Phase 7 v5.4:",
    "## Active Next PR",
    "Title:",
    "fasim: design different GPU execution design or scope acceptance",
    "Phase:",
    "Phase 7 post-v5.3 proof-family first1 or scope acceptance follow-up",
    "Goal:",
    "Either design a new pre-D2H proof family that could pass false-negative audit before runtime reduction, or return to the explicit Path A scoped decision.",
    "stronger task-frontier feasibility gate are already recorded as no-go.",
    "Must not do:",
    "no current stronger task-frontier runtime without a new proof",
    "no runtime reduction in the proof-search export",
    "do not write a reducing runtime from the current proof-search export",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback",
    "no GPU output or digest authority",
    "no default runtime change",
    "no broad_replacement matrix promotion from the v5.3 no-go result",
    "Expected decision after this PR:",
    "If a new Path B architecture is chosen:",
    "If Path A scoped completion is accepted:",
]

missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit(
        "missing required phase roadmap phrase(s):\n" + "\n".join(missing)
    )

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
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("phase roadmap headings are out of order")

gate_order = [
    "### Gate v5.0: Design Checkpoint",
    "### Gate v5.1: True Pre-ScoreInfo Descriptor Source",
    "### Gate v5.2: CPU-Authority Replay",
    "### Gate v5.3: First64 Broad Gate",
    "### Gate v5.4: Workload-Matrix Promotion",
]
gate_positions = [text.index(heading) for heading in gate_order]
if gate_positions != sorted(gate_positions):
    raise SystemExit("phase roadmap v5 gates are out of order")

for stale in [
    "v4 host-visible scoreInfo replay may close the goal",
    "top5-only evidence may close the broad objective",
    "archive-only evidence may close the broad objective",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "run first64 before first1 strict smoke passes",
]:
    if stale in flat:
        raise SystemExit(f"phase roadmap contains forbidden phrase: {stale}")

link = "docs/fasim_gasal2_goal_completion_phase_roadmap.md"
for path in [roadmap, checklist, phase_plan, runbook]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link {link}")

print("phase_roadmap_document=present")
print("phase_roadmap_current_phase=phase7")
print("phase_roadmap_current_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("phase_roadmap_path_a_requires_user_acceptance=1")
print("phase_roadmap_path_b_requires_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
