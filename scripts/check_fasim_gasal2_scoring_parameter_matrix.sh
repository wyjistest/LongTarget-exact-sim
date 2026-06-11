#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scoring_parameter_matrix.md"
MAKEFILE="$ROOT/Makefile"
BRIDGE="$ROOT/fasim/gasal2_align_bridge.cpp"
FASTSIM="$ROOT/fasim/fastsim.h"

if [[ ! -s "$DOC" ]]; then
  echo "missing GASAL2 scoring parameter matrix doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" "$MAKEFILE" "$BRIDGE" "$FASTSIM" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[2]).read_text(encoding="utf-8")
bridge = Path(sys.argv[3]).read_text(encoding="utf-8")
fastsim = Path(sys.argv[4]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Scoring Parameter Matrix",
    "This is a diagnostic checkpoint, not a runtime path.",
    "task_key=49 scoreinfo_index=6 attempt_index=26",
    "CPU score = 137",
    "GASAL2 score = 137",
    "CPU ref_end = 1574, terminal = 0",
    "GASAL2 ref_end = 1575, terminal = 1",
    "legacy selects attempt 27",
    "shadow selects attempt 26",
    "NO_GPU_TERMINAL",
    "summary mismatches = 3",
    "VERIFY_TERMINAL",
    "summary mismatches = 0",
    "task_key=117 scoreinfo_index=26 attempt_index=104",
    "prealign_score = 110",
    "CPU score = 68",
    "gap_open=12",
    "GASAL2 score = 138",
    "shadow emits threshold",
    "legacy emits last_nonzero",
    "gap_open=16",
    "GASAL2 score = 104",
    "below the prealign threshold",
    "NEAT1 first1",
    "gap_open=12",
    "triplex_mismatches = 0",
    "missing_triplexes = 0",
    "extra_triplexes = 0",
    "cpu_align_attempts = 718",
    "realpath_reference_align_attempts = 2008",
    "gap_open=16",
    "triplex_mismatches = 12",
    "missing_triplexes = 1",
    "extra_triplexes = 15",
    "Gap-open alignment is a diagnostic variable, not a default fix.",
    "endpoint/terminal mismatch",
    "segmented score/threshold mismatch",
    "parameter change trades one failure mode for another",
    "Do not promote GASAL2 endpoint, terminal, segmented max-score, or gap-open 16 as authority.",
    "Allowed continuation",
    "full-query-compatible score/end/tie-policy design",
    "CPU-authority validation that still reduces enough total work",
]
for needle in required_doc:
    if needle not in doc:
        raise SystemExit(f"matrix doc missing phrase: {needle}")

required_make = [
    "check-fasim-gasal2-scoring-parameter-matrix:",
    "bash ./scripts/check_fasim_gasal2_scoring_parameter_matrix.sh",
]
for needle in required_make:
    if needle not in makefile:
        raise SystemExit(f"Makefile missing scoring-parameter matrix marker: {needle}")

for needle in (
    "FASIM_ALIGN_GASAL2_GAP_OPEN",
    "FASIM_ALIGN_GASAL2_GAP_EXTEND",
    "state->params->gapo = env_int_or_default",
):
    if needle not in bridge:
        raise SystemExit(f"bridge missing diagnostic parameter marker: {needle}")

for needle in (
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_TASK",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_SCOREINFO",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_NO_GPU_TERMINAL",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_VERIFY_TERMINAL",
    "debug.fasim_gasal2_emission_only_consumer_shadow_attempt",
):
    if needle not in fastsim:
        raise SystemExit(f"fastsim missing matrix debug marker: {needle}")

print("ok")
PY
