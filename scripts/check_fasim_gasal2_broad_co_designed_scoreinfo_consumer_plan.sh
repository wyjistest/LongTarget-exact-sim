#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/plans/2026-06-09-fasim-gasal2-broad-co-designed-scoreinfo-consumer.md"
BROAD_GATE_DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CONSUMER_REQ_DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
NEAT1_REQ_DOC="$ROOT/docs/fasim_gasal2_neat1_next_architecture_requirements.md"
SPEED_DOC="$ROOT/docs/fasim_gasal2_neat1_speed_ceiling.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
ROLLUP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone_rollup.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$PLAN" \
  "$BROAD_GATE_DOC" \
  "$CONSUMER_REQ_DOC" \
  "$NEAT1_REQ_DOC" \
  "$SPEED_DOC" \
  "$CURRENT_STATE_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$FULL_GOAL_DOC" \
  "$ROLLUP_DOC" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing broad co-designed scoreInfo/consumer plan dependency: $path" >&2
    exit 1
  fi
done

python3 - "$PLAN" "$BROAD_GATE_DOC" "$CONSUMER_REQ_DOC" "$NEAT1_REQ_DOC" "$SPEED_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$ROLLUP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

plan = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
broad_gate = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
consumer_req = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
neat1_req = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
speed_doc = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())
rollup = " ".join(Path(sys.argv[9]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[10]).read_text(encoding="utf-8")

required_plan = [
    "Fasim GASAL2 Broad Co-Designed ScoreInfo Consumer Implementation Plan",
    "Goal: Prototype a co-designed scoreInfo plus replacement-consumer shadow",
    "Architecture: Keep CPU output and digest authoritative",
    "Tech Stack: C++11 Fasim runtime, GASAL2/CUDA scoreInfo bridge",
    "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1",
    "broad_path_requested",
    "broad_path_active",
    "broad_path_scoreinfo_seconds",
    "broad_path_consumer_seconds",
    "broad_path_triplex_mismatches",
    "broad_path_candidate_vs_baseline",
    "scoreInfo-level single-emission semantics",
    "legacy break/best-end state",
    "complete task triplex lists",
    "CPU fastSIM_extend_from_scoreinfo remains authority",
    "GPU endpoint/CIGAR/traceback remain non-authoritative",
    "NEAT1 first64 hard gate",
    "candidate_wall_seconds < 86.0335",
    "candidate_vs_baseline > 1.0x",
    "reduce both GPU scoreInfo work and CPU realpath extend/align work",
    "MALAT1 scoped product-readiness remains clean",
    "Stop if selected-only replay is required",
    "Stop if prefix replay is required and align attempts are not reduced",
    "Stop if NEAT1 remains slower than CPU fallback",
    "Task 1: Add the plan gate",
    "Task 2: Add default-off broad shadow telemetry",
    "Task 3: Export CPU authority triplex stream",
    "Task 4: Implement co-designed scoreInfo attempt planner",
    "Task 5: Implement replacement-consumer state shadow",
    "Task 6: Add NEAT1 first64 characterization gate",
    "Task 7: Update decision docs from measured evidence",
    "make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan",
    "make check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export",
    "make check-fasim-gasal2-broad-scoreinfo-attempt-planner",
    "make check-fasim-gasal2-broad-replacement-consumer-shadow",
    "make check-fasim-gasal2-broad-neat1-first64-result",
    "make check-fasim-gasal2-broad-path-architecture-gate",
    "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "make check-fasim-gasal2-neat1-next-architecture-requirements",
    "FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1",
    "replacement_consumer_shadow_active",
    "broad_path_triplex_mismatches = 0",
    "broad_path_missing_triplexes = 0",
    "broad_path_extra_triplexes = 0",
    "decision = broad_path_current_architecture_no_go",
    "broad_path_active = 1",
    "baseline_wall_seconds = 86.932816",
    "candidate_wall_seconds = 288.4177",
    "candidate_vs_baseline = 0.301413x",
    "broad_path_scoreinfo_seconds = 19.1704",
    "broad_path_consumer_seconds = 52.0465",
    "baseline_cpu_reference_seconds = 52.0833",
    "broad_path_align_attempts = 264,970",
    "realpath_extend_align_attempts = 140,087",
    "candidate_wall_not_below_neat1_baseline_ceiling",
    "candidate_vs_baseline_not_above_1",
    "broad_scoreinfo_consumer_not_below_cpu_reference",
    "align_attempts_not_reduced",
]
missing = [phrase for phrase in required_plan if phrase not in plan]
if missing:
    raise SystemExit(
        "broad co-designed scoreInfo/consumer plan missing phrases: "
        + ", ".join(missing)
    )

for forbidden in ("TBD", "TODO", "implement later", "fill in details"):
    if forbidden in plan:
        raise SystemExit(f"broad co-designed plan contains {forbidden!r}")

for name, text, phrases in (
    (
        "broad gate",
        broad_gate,
        [
            "previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer",
            "decision = broad_path_current_architecture_no_go",
            "current co-designed broad replacement-consumer shadow is also a measured performance no-go",
            "prototype a materially different scoreInfo plus replacement consumer architecture",
            "make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan",
        ],
    ),
    (
        "replacement consumer requirements",
        consumer_req,
        [
            "preserve scoreInfo-level single-emission semantics",
            "CPU fastSIM_extend_from_scoreinfo remains authority",
            "make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan",
        ],
    ),
    (
        "NEAT1 requirements",
        neat1_req,
        [
            "kernel-only win is not sufficient",
            "avoid current CPU realpath extend/align replay or replace it with an equivalent batched consumer",
            "make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan",
        ],
    ),
    (
        "speed ceiling",
        speed_doc,
        [
            "ideal_zero_gpu_call_speedup = 0.9747x",
            "next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work",
        ],
    ),
    (
        "rollup",
        rollup,
        [
            "Milestone status: yes, scoped milestone",
            "Full objective status: not complete",
            "full objective remains open",
        ],
    ),
):
    missing_cross = [phrase for phrase in phrases if phrase not in text]
    if missing_cross:
        raise SystemExit(f"{name} missing broad co-designed plan phrase: " + ", ".join(missing_cross))

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan",
        "decision = broad_path_current_architecture_no_go",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing broad co-designed plan phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan:\n"
    r"\tbash \./scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad co-designed plan dependency")
if "check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad CPU triplex export dependency")
if "check-fasim-gasal2-broad-scoreinfo-attempt-planner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad scoreInfo attempt planner dependency")
if "check-fasim-gasal2-broad-replacement-consumer-shadow" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad replacement consumer shadow dependency")
if "check-fasim-gasal2-broad-neat1-first64-result" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad NEAT1 first64 result dependency")

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
if "check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan" not in set(phony_targets):
    raise SystemExit("broad co-designed plan target missing from .PHONY")
if "check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export" not in set(phony_targets):
    raise SystemExit("broad CPU triplex export target missing from .PHONY")
if "check-fasim-gasal2-broad-scoreinfo-attempt-planner" not in set(phony_targets):
    raise SystemExit("broad scoreInfo attempt planner target missing from .PHONY")
if "check-fasim-gasal2-broad-replacement-consumer-shadow" not in set(phony_targets):
    raise SystemExit("broad replacement consumer shadow target missing from .PHONY")
if "check-fasim-gasal2-broad-neat1-first64-result" not in set(phony_targets):
    raise SystemExit("broad NEAT1 first64 result target missing from .PHONY")
PY

echo "ok"
