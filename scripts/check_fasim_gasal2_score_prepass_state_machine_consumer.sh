#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_consumer.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing score-prepass state-machine dependency: $path" >&2
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
    "Fasim GASAL2 Score-Prepass State-Machine Consumer",
    "This is a default-off runtime shadow checkpoint",
    "Selected-only replay is no-go",
    "fastSIM_extend_from_scoreinfo",
    "per scoreInfo:",
    "sw_score >= scoreInfo.score",
    "best ref_end == cutlength - 1 fallback",
    "emit at most one alignment for this scoreInfo",
    "Grouped selected-prefix replay is clean only because it expands selected scoreInfo groups back to the legacy prefix attempts",
    "ScoreOnlyResult:",
    "sw_score",
    "query_end",
    "ref_end",
    "FasimGasal2Attempt:",
    "scoreinfo_index",
    "prealign_score",
    "target_end_required_for_fallback",
    "select_attempts_from_scores()",
    "threshold / best-end / last selector",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
    "Run segmented GASAL2 score-prepass for those attempts",
    "Expand segmented selected attempts to the required per-scoreInfo legacy prefix",
    "Apply the legacy per-scoreInfo state machine over those prefix attempts",
    "CPU-align only the selected/fallback attempt per scoreInfo",
    "Do not use shadow output for candidate state, output, or digest",
    "score_prepass_state_machine_shadow_requested",
    "score_prepass_state_machine_shadow_active",
    "score_prepass_state_machine_shadow_tasks",
    "score_prepass_state_machine_shadow_scoreinfos",
    "score_prepass_state_machine_shadow_attempts",
    "score_prepass_state_machine_shadow_selected_attempts",
    "score_prepass_state_machine_shadow_cpu_align_attempts",
    "score_prepass_state_machine_shadow_triplex_mismatches",
    "score_prepass_state_machine_shadow_first_mismatch_source",
    "score_prepass_state_machine_shadow_first_mismatch_kind",
    "score_prepass_state_machine_shadow_score_seconds",
    "score_prepass_state_machine_shadow_select_seconds",
    "score_prepass_state_machine_shadow_cpu_align_seconds",
    "score_prepass_state_machine_shadow_convert_seconds",
    "score_prepass_state_machine_shadow_total_seconds",
    "score_prepass_state_machine_shadow_fallbacks",
    "NEAT1 first64",
    "digest clean",
    "triplex_mismatches = 0",
    "selected_attempts << attempts",
    "cpu_align_attempts << legacy realpath_extend_align_attempts",
    "GPU score-prepass + state-machine consumer total < CPU fallback wall",
    "Current NEAT1 first1 runtime smoke:",
    "score_prepass_state_machine_shadow_selected_attempts = 9,995",
    "score_prepass_state_machine_shadow_cpu_align_attempts = 51",
    "MALAT1 scoped positive remains clean",
    "If score-only state-machine selected attempts do not reproduce CPU triplexes",
    "If selected attempts are clean but CPU align attempts are not materially lower",
    "If score-prepass total plus CPU traceback is still slower than CPU fallback",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no output/digest authority",
    "no production opt-in",
    "no selected-only consumer promotion",
    "make check-fasim-gasal2-score-prepass-state-machine-consumer",
    "make check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke",
    "make check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "score-prepass state-machine doc missing phrases: " + ", ".join(missing)
    )

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("full-goal", full_goal),
):
    for phrase in (
        "score-prepass state-machine consumer",
        "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
        "select_attempts_from_scores()",
        "CPU-align only the selected",
        "make check-fasim-gasal2-score-prepass-state-machine-consumer",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing score-prepass state-machine phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-consumer:\n"
    r"\tbash \./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing score-prepass state-machine consumer target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-score-prepass-state-machine-consumer" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass state-machine consumer dependency")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing segmented score-prepass state-machine runtime dependency")

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
if "check-fasim-gasal2-score-prepass-state-machine-consumer" not in phony_targets:
    raise SystemExit("score-prepass state-machine consumer target missing from .PHONY")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke" not in phony_targets:
    raise SystemExit("segmented score-prepass state-machine runtime target missing from .PHONY")
PY

echo "ok"
