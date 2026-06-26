#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
PLAN="$ROOT/docs/superpowers/plans/2026-06-12-fasim-gasal2-phase7-broad-restart-v2.md"

for path in "$DOC" "$PLAN"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 7 broad restart v2 dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$PLAN" <<'PY'
from pathlib import Path
import sys

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
plan = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())

required_doc = [
    "Fasim GASAL2 Phase 7 Broad Restart v2 Design",
    "not runtime code",
    "not a completion claim",
    "current Phase 7 next reducer is stopped as a broad path",
    "NEAT1 first1 correctness no-go",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "frontier log first",
    "exact replay proof before reduction",
    "task-local frontier identity",
    "scoreInfo-local single-emission state",
    "candidate reducer may only consume a proven frontier log",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "no output or digest authority from GASAL2",
    "NEAT1 first1 replay proof",
    "NEAT1 first64 broad gate",
    "full row-set equality or digest clean",
    "candidate_align_attempts < reference_align_attempts",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0x",
    "scoreInfo/preAlign work reduced",
    "Align-side attempts reduced or replaced",
]
missing = [needle for needle in required_doc if needle not in doc]
if missing:
    raise SystemExit("Phase 7 v2 design missing phrases: " + ", ".join(missing))

required_plan = [
    "Fasim GASAL2 Phase 7 Broad Restart v2 Implementation Plan",
    "REQUIRED SUB-SKILL",
    "Build a default-off Phase 7 v2 frontier-log and replay-proof scaffold",
    "frontier log schema",
    "write the failing checker",
    "NEAT1 first1",
    "NEAT1 first64",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "false_negative_scoreinfos = 0",
    "CPU aligner.Align() remains authority",
    "must_not_call_update_goal_complete = 1",
]
missing_plan = [needle for needle in required_plan if needle not in plan]
if missing_plan:
    raise SystemExit("Phase 7 v2 plan missing phrases: " + ", ".join(missing_plan))

print("phase7_broad_restart_v2_design_gate=defined")
print("phase7_broad_restart_v2_current_status=design_only")
print("phase7_broad_restart_v2_required_first_gate=frontier_log_replay_proof")
print("phase7_broad_restart_v2_requires_neat1_first64=1")
print("cpu_aligner_align_authority=1")
print("gasal2_output_authority=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
