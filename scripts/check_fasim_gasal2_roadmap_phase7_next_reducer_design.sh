#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_next_reducer_design.md"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase7_next_reducer_design"}"

if [[ ! -s "$DOC" ]]; then
  echo "missing Phase 7 next reducer design doc: $DOC" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

python3 - "$DOC" >"$WORK/summary.txt" <<'PY'
from pathlib import Path
import sys

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())

required = [
    "Fasim GASAL2 Phase 7 Next Reducer Design",
    "not runtime code",
    "not a completion claim",
    "not a permission to use GASAL2 output as authority",
    "current_reducer_no_go",
    "no_cpu_align_attempt_reduction",
    "task-local frontier reducer",
    "scoreInfo-local state preservation",
    "legacy single-emission semantics",
    "CPU aligner.Align() remains authority",
    "GASAL2 proposes attempts only",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback",
    "candidate_align_attempts < reference_align_attempts",
    "false_negative_scoreinfos = 0",
    "triplex_mismatches = 0",
    "digest_match = 1 or full_rows_equal = 1",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0x",
    "prefix coverage reducer",
    "selected-only coverage reducer",
    "current broad replacement-consumer replay",
    "current score-prepass state-machine trust",
    "GASAL2 endpoint as terminal authority",
    "GASAL2 score as accept/reject authority without CPU validation",
    "phase7_next_reducer_requested",
    "phase7_next_reducer_candidate_align_attempts",
    "phase7_next_reducer_reference_align_attempts",
    "phase7_next_reducer_false_negative_scoreinfos",
    "phase7_next_reducer_candidate_vs_baseline",
    "NEAT1 first64 remains the broad gate",
    "Initial bounded smoke may use NEAT1 first1",
    "If candidate_align_attempts are not reduced:",
    "If false_negative_scoreinfos is nonzero:",
    "If NEAT1 first64 passes correctness and runtime gates:",
]
missing = [needle for needle in required if needle not in doc]
if missing:
    raise SystemExit("next reducer design missing phrases: " + ", ".join(missing))

print("phase7_next_reducer_design_gate=defined")
print("current_candidate_reducer_status=current_reducer_no_go")
print("required_next_reducer=task_local_frontier_or_scoreinfo_local_state")
print("cpu_aligner_align_authority=1")
print("gasal2_output_authority=0")
print("requires_align_attempt_reduction=1")
print("requires_false_negative_scoreinfos_zero=1")
print("requires_neat1_first64_broad_gate=1")
print("must_not_call_update_goal_complete=1")
print("ok")
PY

cat "$WORK/summary.txt"
