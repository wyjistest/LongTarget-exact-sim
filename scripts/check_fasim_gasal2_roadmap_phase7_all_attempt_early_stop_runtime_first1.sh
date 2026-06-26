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

texts = [Path(path).read_text(encoding="utf-8") for path in sys.argv[1:]]
flat = " ".join("\n".join(texts).split())

required = [
    "phase7_all_attempt_early_stop_runtime_first1 =",
    "make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime",
    "make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result",
    "FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1",
    "all-attempt mode keeps candidate coverage before candidate reduction",
    "CPU aligner.Align() remains authority",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "decision = phase7_all_attempt_early_stop_runtime_first1_",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_all_attempt_early_stop_runtime_first1=recorded")
print("phase7_all_attempt_early_stop_runtime_first1_broad_gate_pass=0")
print("next_gate=phase7_all_attempt_or_new_architecture")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
