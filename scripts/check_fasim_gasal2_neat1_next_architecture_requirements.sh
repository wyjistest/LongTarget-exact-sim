#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_neat1_next_architecture_requirements.md"
SPEED_DOC="$ROOT/docs/fasim_gasal2_neat1_speed_ceiling.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$SPEED_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing NEAT1 next-architecture requirement dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$SPEED_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
speed_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 NEAT1 Next Architecture Requirements",
    "This is a requirements checkpoint, not runtime code",
    "Derived from the NEAT1 speed ceiling",
    "baseline_wall_seconds = 86.0335",
    "candidate_wall_seconds = 121.948",
    "candidate_vs_baseline = 0.705493x",
    "ideal_zero_gpu_call_speedup = 0.9747x",
    "ideal_zero_gpu_total_speedup = 1.1950x",
    "ideal_zero_realpath_extend_speedup = 1.2312x",
    "not enough to optimize only the CUDA kernel",
    "not enough to optimize only scoreInfo orchestration",
    "not enough to optimize only CPU realpath extend",
    "Required prototype shape",
    "produce legacy-byte-compatible scoreInfo",
    "avoid CPU preAlign replay",
    "avoid current CPU realpath extend/align replay or replace it with an equivalent batched consumer",
    "preserve scoreInfo-level single-emission semantics",
    "prove selected-attempt output equivalence before using reduced attempts",
    "external digest gate remains authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "NEAT1 first64 hard gate",
    "digest clean",
    "scoreinfo_gasal2_active = 1",
    "fallback = 0",
    "scoreInfo mismatches = 0",
    "candidate_wall_seconds < 86.0335",
    "GPU scoreInfo plus replacement-consumer total must beat CPU fallback",
    "kernel-only win is not sufficient",
    "MALAT1 scoped positive must remain clean",
    "If the prototype cannot reduce both GPU scoreInfo and realpath extend/align, stop the NEAT1 broad path",
    "full objective remains open",
    "make check-fasim-gasal2-neat1-next-architecture-requirements",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "NEAT1 next-architecture requirements doc missing phrases: "
        + ", ".join(missing)
    )

for phrase in (
    "ideal_zero_gpu_call_speedup = 0.9747x",
    "next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work",
):
    if phrase not in speed_doc:
        raise SystemExit(f"speed-ceiling doc missing prerequisite phrase: {phrase}")

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "make check-fasim-gasal2-neat1-next-architecture-requirements",
        "NEAT1 next architecture requirements",
        "kernel-only win is not sufficient",
        "If the prototype cannot reduce both GPU scoreInfo and realpath extend/align, stop the NEAT1 broad path",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing NEAT1 next-architecture phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-neat1-next-architecture-requirements:\n"
    r"\tbash \./scripts/check_fasim_gasal2_neat1_next_architecture_requirements\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-neat1-next-architecture-requirements target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
deps = current_target.group("deps").split()
if "check-fasim-gasal2-neat1-next-architecture-requirements" not in deps:
    raise SystemExit("current-state target missing NEAT1 next-architecture requirements dependency")
if "check-fasim-gasal2-neat1-speed-ceiling" not in deps:
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
if "check-fasim-gasal2-neat1-next-architecture-requirements" not in phony_targets:
    raise SystemExit("NEAT1 next-architecture requirements target missing from .PHONY")
if "check-fasim-gasal2-neat1-speed-ceiling" not in phony_targets:
    raise SystemExit("NEAT1 speed-ceiling target missing from .PHONY")
PY

echo "ok"
