#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_characterization.md"
CONSUMER_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_consumer.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"
CHAR_SCRIPT="$ROOT/scripts/characterize_fasim_gasal2_score_prepass_state_machine_consumer.sh"

for path in "$DOC" "$CONSUMER_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" "$CHAR_SCRIPT"; do
  if [[ ! -s "$path" ]]; then
    echo "missing score-prepass state-machine characterization dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CONSUMER_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" "$CHAR_SCRIPT" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
consumer_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")
script = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Score-Prepass State-Machine Characterization",
    "default-off segmented score-prepass state-machine shadow",
    "It does not add a production path",
    "CPU Fasim output remains the authority",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
    "uses segmented GASAL2 score-prepass over bounded query segments",
    "expands selected attempts to the per-scoreInfo legacy prefix",
    "runs the legacy threshold / best-end / last state machine",
    "CPU-aligns only selected/fallback attempts",
    "never writes GPU/GASAL2 output into candidate state, output, or digest",
    "NEAT1 first1:",
    "candidate_vs_baseline = 0.530629x",
    "NEAT1 first4:",
    "candidate_vs_baseline = 0.568306x",
    "NEAT1 first16:",
    "state-machine CPU align attempts = 13,474",
    "candidate_vs_baseline = 0.522888x",
    "MALAT1 first8:",
    "state-machine CPU align attempts = 6,188",
    "candidate_vs_baseline = 0.702397x",
    "scoreinfo_mismatches = 0",
    "realpath_fallbacks = 0",
    "length_guard_fallbacks = 0",
    "state_machine_fallbacks = 0",
    "state_machine_triplex_mismatches = 0",
    "Correctness/shape:",
    "go as default-off shadow scaffold",
    "Performance:",
    "no-go for current shadow implementation",
    "Real path:",
    "no",
    "Do not promote:",
    "real opt-in",
    "GPU endpoint authority",
    "GPU CIGAR/traceback authority",
    "GPU/GASAL2 output authority",
    "selected-only replay",
    "whole-query GASAL2 selector for long queries",
    "Only continue if the next implementation removes the duplicate CPU realpath work",
    "bash scripts/characterize_fasim_gasal2_score_prepass_state_machine_consumer.sh",
    "bash scripts/check_fasim_gasal2_score_prepass_state_machine_characterization.sh",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "score-prepass state-machine characterization doc missing phrases: "
        + ", ".join(missing)
    )

for name, text in (
    ("consumer-doc", consumer_doc),
    ("current-state", current_state),
):
    for phrase in (
        "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
        "score-prepass state-machine",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} missing score-prepass state-machine phrase: {phrase}")

for phrase in (
    "NEAT1_RECORD_LIMITS",
    "MALAT1_RECORD_LIMITS",
    "score_prepass_state_machine_shadow_triplex_mismatches",
    "candidate_vs_baseline",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1",
):
    if phrase not in script:
        raise SystemExit(f"characterization script missing phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-characterization:\n"
    r"\tbash \./scripts/check_fasim_gasal2_score_prepass_state_machine_characterization\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing score-prepass state-machine characterization target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-score-prepass-state-machine-characterization" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass state-machine characterization dependency")

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
if "check-fasim-gasal2-score-prepass-state-machine-characterization" not in phony_targets:
    raise SystemExit("score-prepass state-machine characterization target missing from .PHONY")
PY

echo "ok"
