#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
CHARACTERIZE="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_trust.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$CHARACTERIZE" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing NEAT1 runtime boundary dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$CHARACTERIZE" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
characterize = Path(sys.argv[5]).read_text(encoding="utf-8")
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_script = [
    "baseline_wall_seconds",
    "candidate_wall_seconds",
    "candidate_vs_baseline",
    "benchmark.total_wall_seconds",
    "Running time is",
]
missing = [phrase for phrase in required_script if phrase not in characterize]
if missing:
    raise SystemExit("NEAT1 trust characterization missing phrases: " + ", ".join(missing))

required_doc = [
    "NEAT1 Runtime Boundary",
    "Runtime characterization is distinct from audited replay",
    "audited replay wall time includes segmented/full/oracle replay probes",
    "do not use audited replay wall time as real runtime speedup evidence",
    "NEAT1 first64 runtime trust:",
    "baseline Running time = 86.0335s",
    "candidate Running time = 121.948s",
    "candidate/baseline speedup = 0.705493x",
    "NEAT1 first128 audited replay:",
    "baseline_runner_wall_seconds = 173.527502s",
    "candidate_runner_wall_seconds = 577.125576s",
    "replay diagnostic overhead is expected",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("streaming design doc missing NEAT1 runtime boundary phrases: " + ", ".join(missing))

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "NEAT1 runtime boundary",
        "do not use audited replay wall time as real runtime speedup evidence",
        "candidate/baseline speedup = 0.705493x",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing NEAT1 runtime boundary phrase: {phrase}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_neat1_runtime_boundary\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing NEAT1 runtime boundary dependency")

phony_targets = []
lines = makefile.splitlines()
for index, line in enumerate(lines):
    if not line.startswith(".PHONY:"):
        continue
    text = line[len(".PHONY:"):]
    cursor = index
    while text.rstrip().endswith("\\") and cursor + 1 < len(lines):
        text = text.rstrip()[:-1] + " " + lines[cursor + 1]
        cursor += 1
    phony_targets.extend(text.split())
if "check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary" not in phony_targets:
    raise SystemExit("NEAT1 runtime boundary target missing from .PHONY")
PY

echo "ok"
