#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_current_stop.md"
BOUNDARY_DOC="$ROOT/docs/fasim_gasal2_long_query_boundary.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$BOUNDARY_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing GASAL2 long-query current stop dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$BOUNDARY_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
boundary_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap_doc = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
full_goal_doc = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Current Long-Query Implementation Stop Checkpoint",
    "current segmented no-last replay line: stopped for real path",
    "correctness clean through MALAT1 first128",
    "performance marginal through MALAT1 first128",
    "malat1_first8 speedup=1.009996x",
    "malat1_first16 speedup=1.029101x",
    "malat1_first32 speedup=1.031832x",
    "malat1_first64 speedup=1.034623x",
    "malat1_first128 speedup=1.038017x",
    "direct segmented traceback shadow: no-go",
    "pruned segmented traceback shadow: no-go",
    "score-prepass batched shadow: stage-only",
    "single-pass topN: not top5-safe",
    "max-query GASAL2 expansion: no-go",
    "do not promote segmented long-query no-last replay",
    "do not promote GASAL2 traceback for long-query output",
    "do not promote score-prepass stage-only output",
    "do not continue current segmented/no-last implementation as a real path",
    "Next universal-path work must be a different long-query architecture or full-output equivalence proof",
    "make check-fasim-gasal2-long-query-current-stop",
    "make check-fasim-gasal2-long-query-segmented-no-last-scaling-result",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("long-query current stop doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("boundary", boundary_doc),
    ("current-state", current_state_doc),
    ("completion-gap", completion_gap_doc),
    ("full-goal", full_goal_doc),
):
    for phrase in (
        "make check-fasim-gasal2-long-query-current-stop",
        "current segmented no-last replay line: stopped for real path",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing long-query stop phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-long-query-current-stop:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_current_stop\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-current-stop target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-long-query-current-stop" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing long-query current-stop dependency")
PY

echo "ok"
