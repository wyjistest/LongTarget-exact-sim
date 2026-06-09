#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_neat1_speed_ceiling.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing NEAT1 speed-ceiling dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 NEAT1 Speed Ceiling",
    "NEAT1 first64 fresh runtime attribution",
    "baseline_wall_seconds = 86.0335",
    "candidate_wall_seconds = 121.948",
    "candidate_vs_baseline = 0.705493x",
    "gpu_total_seconds = 49.9507",
    "realpath_extend_seconds = 52.0682",
    "unattributed_overhead_seconds ~= 19.9291",
    "candidate_minus_baseline_seconds = 35.9145",
    "ideal_zero_gpu_total_wall_seconds = 71.9973",
    "ideal_zero_gpu_total_speedup = 1.1950x",
    "ideal_zero_gpu_call_wall_seconds = 88.2656",
    "ideal_zero_gpu_call_speedup = 0.9747x",
    "ideal_zero_realpath_extend_wall_seconds = 69.8798",
    "ideal_zero_realpath_extend_speedup = 1.2312x",
    "scoreInfo-only optimization cannot justify broad replacement unless it removes almost all GPU total",
    "kernel-only optimization is insufficient",
    "realpath_extend remains a co-equal bottleneck",
    "next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work",
    "not H2D/D2H, validation, compare, or CPU fallback",
    "not a completion claim",
    "full objective remains open",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("NEAT1 speed-ceiling doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "make check-fasim-gasal2-neat1-speed-ceiling",
        "NEAT1 speed ceiling",
        "next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing NEAT1 speed-ceiling phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-neat1-speed-ceiling:\n"
    r"\tbash \./scripts/check_fasim_gasal2_neat1_speed_ceiling\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-neat1-speed-ceiling target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-neat1-speed-ceiling" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing NEAT1 speed-ceiling dependency")

phony_targets = []
lines = makefile.splitlines()
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith(".PHONY:"):
        text = line.split(":", 1)[1].strip()
        while text.endswith("\\") and index + 1 < len(lines):
            text = text[:-1] + " " + lines[index + 1].strip()
            index += 1
        phony_targets.extend(text.split())
    index += 1
if not phony_targets:
    raise SystemExit("Makefile missing .PHONY block")
phony_targets = set(phony_targets)
if "check-fasim-gasal2-neat1-speed-ceiling" not in phony_targets:
    raise SystemExit("NEAT1 speed-ceiling target missing from .PHONY")
PY

echo "ok"
