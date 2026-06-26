#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_next_reducer_after_early_stop_no_go_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"

if [[ ! -s "$DOC" ]]; then
  echo "missing next Phase 7 reducer design doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1]).read_text(encoding="utf-8")
roadmap = Path(sys.argv[2]).read_text(encoding="utf-8")
phase_plan = Path(sys.argv[3]).read_text(encoding="utf-8")
flat_doc = " ".join(doc.split())
flat_all = " ".join("\n".join([doc, roadmap, phase_plan]).split())

required_doc = [
    "phase7_next_reducer_after_early_stop_no_go_design = defined",
    "early_stop_runtime_first1 = correctness_no_go",
    "Do not continue the measured early-stop candidate to NEAT1 first64",
    "coverage-first all-attempt CPU replay",
    "candidate coverage before candidate reduction",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "Gate A: all-attempt early-stop runtime first1",
    "Gate B: all-attempt early-stop runtime first64",
    "Gate C: coverage-preserving GPU candidate generator",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "candidate_align_attempts < reference_align_attempts",
    "scoreInfo/preAlign work must be reduced before broad completion",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required_doc:
    if phrase not in flat_doc:
        raise SystemExit(f"design doc missing required phrase: {phrase}")

required_cross_doc = [
    "fasim: prototype Phase 7 all-attempt early-stop runtime",
    "next gate = new reducer or architecture",
]
for phrase in required_cross_doc:
    if phrase not in flat_all:
        raise SystemExit(f"roadmap/phase plan missing required phrase: {phrase}")

print("phase7_next_reducer_after_early_stop_no_go_design=defined")
print("phase7_failed_candidate=early_stop_runtime_first1_correctness_no_go")
print("phase7_next_design_gate=coverage_first_all_attempt_replay")
print("phase7_next_first_gate=all_attempt_early_stop_runtime_first1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
