#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_emission_only_consumer_debug.md"
FASTSIM="$ROOT/fasim/fastsim.h"
BRIDGE="$ROOT/fasim/gasal2_align_bridge.cpp"

if [[ ! -s "$DOC" ]]; then
  echo "missing emission-only consumer debug doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" "$FASTSIM" "$BRIDGE" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
fastsim = Path(sys.argv[2]).read_text(encoding="utf-8")
bridge = Path(sys.argv[3]).read_text(encoding="utf-8")

required_doc = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1",
    "decision = emission_only_consumer_shadow_correctness_no_go",
    "candidate_vs_baseline = 0.157653x",
    "cpu_align_attempts = 52,994",
    "realpath_reference_align_attempts = 140,087",
    "align_attempt_reduction = 87,093",
    "triplex_mismatches = 4,404",
    "missing_triplexes = 2,096",
    "extra_triplexes = 1,460",
    "task_key=49 scoreinfo_index=6 attempt_index=26",
    "cpu_score = 137",
    "cpu_ref_end = 1574",
    "cpu_terminal = 0",
    "shadow_score = 137",
    "shadow_ref_end = 1575",
    "shadow_terminal = 1",
    "legacy_attempt_index = 27",
    "shadow_attempt_index = 26",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_NO_GPU_TERMINAL=1",
    "task_key=49 no_gpu_terminal summary mismatches = 3",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_VERIFY_TERMINAL=1",
    "task_key=49 verify_terminal summary mismatches = 0",
    "terminal -> terminal: 240",
    "last_nonzero -> terminal: 184",
    "last_nonzero -> threshold: 21",
    "terminal -> threshold: 14",
    "terminal -> last_nonzero: 12",
    "35 cases where shadow emits by threshold but legacy does not",
    "task_key=117",
    "scoreinfo_index=26",
    "attempt_index=104",
    "CPU score for the same attempt is only `68`",
    "segmented GASAL2 score can overestimate CPU score",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=16",
    "gap_open = 12: shadow_score = 138",
    "gap_open = 16: shadow_score = 104",
    "triplex_mismatches = 12",
    "missing_triplexes = 1",
    "extra_triplexes = 15",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=12",
    "triplex_mismatches = 0",
    "diagnostic A/B knob",
    "safe reject/accept authority",
    "GASAL2 endpoint as terminal authority",
    "current segmented max-score threshold",
    "real replacement path: no",
]
for needle in required_doc:
    if needle not in doc:
        raise SystemExit(f"missing emission-only debug doc marker: {needle}")

required_fastsim = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_TASK",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_SCOREINFO",
    "const bool debugTaskMatches",
    "if (debugTaskMatches)",
    "debugScoreInfoFilter >= 0",
    "debug.fasim_gasal2_emission_only_consumer_shadow_attempt",
    "debug.fasim_gasal2_emission_only_consumer_shadow",
]
for needle in required_fastsim:
    if needle not in fastsim:
        raise SystemExit(f"missing fastsim debug marker: {needle}")

for needle in (
    "FASIM_ALIGN_GASAL2_GAP_OPEN",
    "FASIM_ALIGN_GASAL2_GAP_EXTEND",
    "state->params->gapo = env_int_or_default",
):
    if needle not in bridge:
        raise SystemExit(f"missing bridge debug marker: {needle}")

print("ok")
PY
