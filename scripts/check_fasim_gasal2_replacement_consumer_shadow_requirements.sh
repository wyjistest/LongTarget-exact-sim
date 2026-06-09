#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
NEAT1_REQUIREMENTS_DOC="$ROOT/docs/fasim_gasal2_neat1_next_architecture_requirements.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$NEAT1_REQUIREMENTS_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing replacement-consumer shadow dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$NEAT1_REQUIREMENTS_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
neat1_requirements = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Replacement Consumer Shadow Requirements",
    "This is a requirements checkpoint, not runtime code",
    "The active objective remains open",
    "MALAT1 no-probe two-contract path is a scoped milestone",
    "NEAT1 first64 is the blocking broad-replacement case",
    "candidate_wall_seconds = 121.948",
    "baseline_wall_seconds = 86.0335",
    "gpu_total_seconds = 49.9507",
    "realpath_extend_seconds = 52.0682",
    "realpath_extend_align_attempts = 140,087",
    "replacement consumer shadow",
    "CPU fastSIM_extend_from_scoreinfo remains authority",
    "Do not use GPU endpoint",
    "Do not use GPU CIGAR",
    "Do not use GPU traceback",
    "Do not use replacement-consumer output",
    "digest remains external authority",
    "collect per-scoreInfo align attempts",
    "preserve scoreInfo-level single-emission semantics",
    "compare task triplex lists against CPU authority",
    "selected-only replay is not sufficient",
    "grouped selected-prefix replay restores correctness but not align-attempt reduction",
    "full replay is correctness reference, not performance candidate",
    "legacy `fastSIM_extend_from_scoreinfo()` state machine",
    "alignment.sw_score >= scoreInfo.score",
    "ref_end == cutlength - 1",
    "emit at most one best/last alignment for that scoreInfo",
    "replays only selected attempts",
    "scoreInfo-local break/best-end state",
    "expands selected scoreInfo groups back to the legacy prefix",
    "telemetry must include",
    "replacement_consumer_shadow_requested",
    "replacement_consumer_shadow_active",
    "replacement_consumer_shadow_tasks",
    "replacement_consumer_shadow_scoreinfo_groups",
    "replacement_consumer_shadow_align_attempts",
    "replacement_consumer_shadow_selected_attempts",
    "replacement_consumer_shadow_triplex_mismatches",
    "replacement_consumer_shadow_segmented_triplex_mismatches",
    "replacement_consumer_shadow_selected_only_triplex_mismatches",
    "replacement_consumer_shadow_grouped_selected_triplex_mismatches",
    "replacement_consumer_shadow_full_triplex_mismatches",
    "replacement_consumer_shadow_oracle_triplex_mismatches",
    "replacement_consumer_shadow_first_mismatch",
    "replacement_consumer_shadow_first_mismatch_source",
    "replacement_consumer_shadow_first_mismatch_kind",
    "replacement_consumer_shadow_seconds",
    "replacement_consumer_shadow_fallbacks",
    "NEAT1 first1 replacement-consumer shadow smoke",
    "selected-only replay mismatch remains visible",
    "replacement_consumer_shadow_first_mismatch_source = selected_only",
    "replacement_consumer_shadow_first_mismatch_kind = legacy_empty",
    "Hard go gate",
    "triplex_mismatches = 0",
    "candidate_wall_seconds < 86.0335",
    "replacement consumer plus GPU scoreInfo total beats CPU fallback",
    "MALAT1 scoped positive remains clean",
    "Stop gate",
    "If selected-attempt reduction changes triplex output, do not promote",
    "If prefix replay is required and align attempts are not reduced, do not promote",
    "If NEAT1 remains slower than CPU fallback, do not promote",
    "If a consumer cannot preserve the scoreInfo-local break/best-end state machine, do not promote",
    "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "make check-fasim-gasal2-replacement-consumer-shadow-env",
    "make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "replacement-consumer shadow requirements doc missing phrases: "
        + ", ".join(missing)
    )

for phrase in (
    "avoid current CPU realpath extend/align replay or replace it with an equivalent batched consumer",
    "preserve scoreInfo-level single-emission semantics",
    "GPU scoreInfo plus replacement-consumer total must beat CPU fallback",
):
    if phrase not in neat1_requirements:
        raise SystemExit(f"NEAT1 requirements doc missing prerequisite phrase: {phrase}")

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
        "make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke",
        "replacement consumer shadow",
        "selected-only replay is not sufficient",
        "scoreInfo-local break/best-end state",
        "legacy prefix",
        "If NEAT1 remains slower than CPU fallback, do not promote",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing replacement-consumer phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-replacement-consumer-shadow-requirements:\n"
    r"\tbash \./scripts/check_fasim_gasal2_replacement_consumer_shadow_requirements\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing replacement-consumer shadow requirements target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
deps = current_target.group("deps").split()
if "check-fasim-gasal2-replacement-consumer-shadow-requirements" not in deps:
    raise SystemExit("current-state target missing replacement-consumer shadow requirements dependency")
if "check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke" not in deps:
    raise SystemExit("current-state target missing replacement-consumer shadow runtime-smoke dependency")

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
if "check-fasim-gasal2-replacement-consumer-shadow-requirements" not in phony_targets:
    raise SystemExit("replacement-consumer shadow target missing from .PHONY")
if "check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke" not in phony_targets:
    raise SystemExit("replacement-consumer shadow runtime-smoke target missing from .PHONY")
PY

echo "ok"
