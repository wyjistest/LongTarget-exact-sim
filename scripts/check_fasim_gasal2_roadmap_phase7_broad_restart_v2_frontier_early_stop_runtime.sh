#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1]).read_text(encoding="utf-8")
roadmap = Path(sys.argv[2]).read_text(encoding="utf-8")
phase_plan = Path(sys.argv[3]).read_text(encoding="utf-8")
combined = "\n".join([doc, roadmap, phase_plan])
flat_doc = " ".join(doc.split())
flat_combined = " ".join(combined.split())

required_doc = [
    "phase7_broad_restart_v2_frontier_early_stop_runtime = runtime_smoke_clean_needs_neat1_first1",
    "make check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke",
    "FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1",
    "default_off = 1",
    "reference_align_attempts = 192",
    "candidate_align_attempts = 48",
    "skipped_attempts = 144",
    "output digest unchanged",
    "CPU aligner.Align() remains authority",
    "next gate = measured runtime NEAT1 first1 correctness gate",
    "broad_gate_pass = 0",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required_doc:
    if phrase not in flat_doc:
        raise SystemExit(f"design doc missing required phrase: {phrase}")

required_cross_docs = [
    "Phase 7.1: Measured Early-Stop Runtime Smoke",
    "Phase 7.2: NEAT1 first1 Runtime Correctness Gate",
    "Phase 7.3: NEAT1 first64 Broad Gate",
]
for phrase in required_cross_docs:
    if phrase not in flat_combined:
        raise SystemExit(f"roadmap/phase plan missing required phrase: {phrase}")

print("phase7_broad_restart_v2_frontier_early_stop_runtime=runtime_smoke_clean_needs_neat1_first1")
print("phase7_frontier_early_stop_runtime_default_off=1")
print("phase7_frontier_early_stop_runtime_reference_align_attempts=192")
print("phase7_frontier_early_stop_runtime_candidate_align_attempts=48")
print("phase7_frontier_early_stop_runtime_skipped_attempts=144")
print("phase7_frontier_early_stop_runtime_broad_gate_pass=0")
print("next_gate=measured_runtime_neat1_first1_correctness")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
