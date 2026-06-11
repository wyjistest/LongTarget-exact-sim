#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_cpu_authority_candidate_coverage_plan.md"
MAKEFILE="$ROOT/Makefile"
BRIDGE="$ROOT/fasim/gasal2_align_bridge.cpp"
FASTSIM="$ROOT/fasim/Fasim-LongTarget.cpp"

if [[ ! -s "$DOC" ]]; then
  echo "missing CPU-authority candidate coverage plan doc: $DOC" >&2
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
    "Fasim GASAL2 CPU-Authority Candidate Coverage Plan",
    "This is the next broad-path probe toward the active objective",
    "not a runtime path",
    "not a completion claim",
    "CPU `aligner.Align()` remains the only authority",
    "GASAL2 may only propose candidate attempts",
    "candidate coverage",
    "legacy selected attempt is present in the GASAL2 candidate set",
    "false_negative_scoreinfos = 0",
    "triplex_mismatches = 0",
    "missing_triplexes = 0",
    "extra_triplexes = 0",
    "cpu_align_attempts < realpath_reference_align_attempts",
    "total_seconds < realpath_reference_seconds",
    "score_margin sweep",
    "include threshold candidates",
    "include fallback candidates",
    "include last_nonzero candidates",
    "deduplicate attempts by scoreinfo/start/cutlength",
    "Do not use GASAL2 endpoint as terminal authority",
    "Do not use segmented score as accept/reject authority without CPU validation",
    "Do not use GASAL2 CIGAR or traceback",
    "NEAT1 first1",
    "NEAT1 first64",
    "task49",
    "task117",
    "Decision",
    "If false_negative_scoreinfos is nonzero, stop this candidate reducer",
    "If coverage is clean but CPU align attempts are not reduced, stop this candidate reducer",
    "If coverage and speed are clean, next PR may implement a default-off shadow",
]
for needle in required_doc:
    if needle not in doc:
        raise SystemExit(f"candidate coverage plan missing phrase: {needle}")

for needle in (
    "check-fasim-gasal2-cpu-authority-candidate-coverage-plan:",
    "bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_plan.sh",
):
    if needle not in makefile:
        raise SystemExit(f"Makefile missing candidate coverage plan marker: {needle}")

for needle in (
    "select_cpu_traceback_candidates_from_scores",
    "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_SCORE_MARGIN",
    "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST",
    "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST",
):
    if needle not in bridge:
        raise SystemExit(f"bridge missing CPU-authority candidate selector marker: {needle}")

for needle in (
    "score_prepass_state_machine_shadow_requested",
    "score_prepass_state_machine_shadow_cpu_align_attempts",
    "score_prepass_state_machine_shadow_triplex_mismatches",
):
    if needle not in fastsim:
        raise SystemExit(f"Fasim runtime missing state-machine coverage marker: {needle}")

print("ok")
PY
