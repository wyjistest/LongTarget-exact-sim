#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from pathlib import Path
import sys

required = [
    "phase7_broad_restart_v2_frontier_replay_gate = exact_no_reduction",
    "make characterize-fasim-gasal2-phase7-frontier-replay",
    "make check-fasim-gasal2-phase7-frontier-replay-result",
    "neat1_first1:",
    "digest_match = 1",
    "full_rows_equal = 1",
    "frontier_log_rows = 2,872",
    "frontier_selected_rows = 718",
    "frontier_positive_align_rows = 2,872",
    "candidate_align_attempts = reference_align_attempts = 2,872",
    "neat1_first64:",
    "frontier_log_rows = 211,976",
    "frontier_selected_rows = 52,994",
    "frontier_positive_align_rows = 211,976",
    "candidate_align_attempts = reference_align_attempts = 211,976",
    "reducer-ready frontier evidence is present",
    "next gate = reducer shadow after replay proof",
    "no measured CPU Align attempt reduction yet",
    "not broad completion",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

for name, path in [("design", Path(sys.argv[1])), ("roadmap", Path(sys.argv[2]))]:
    text = " ".join(path.read_text(encoding="utf-8").split())
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit(
            f"{name} missing Phase 7 v2 frontier replay phrases: "
            + ", ".join(missing)
        )

print("phase7_broad_restart_v2_frontier_replay_gate=exact_no_reduction")
print("phase7_frontier_replay_first1=exact")
print("phase7_frontier_replay_first64=exact")
print("phase7_frontier_replay_align_reduction=0")
print("cpu_aligner_align_authority=1")
print("gasal2_output_authority=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
