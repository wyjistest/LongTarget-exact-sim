#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/plans/2026-06-09-fasim-gasal2-attempt-level-consumer-shadow.md"
BROAD_DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CURRENT_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$PLAN" "$BROAD_DOC" "$CURRENT_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing attempt-level consumer shadow dependency: $path" >&2
    exit 1
  fi
done

python3 - "$PLAN" "$BROAD_DOC" "$CURRENT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

plan = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
broad = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

required_plan = [
    "Fasim GASAL2 Attempt-Level Consumer Shadow Implementation Plan",
    "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1",
    "CPU `fastSIM_extend_from_scoreinfo()` output and digest authoritative",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_triplex_mismatches",
    "attempt_consumer_shadow_candidate_go",
    "Build legacy attempt descriptors",
    "Run GASAL2 score-only",
    "Preserve legacy scoreInfo-local state",
    "CPU-align only selected attempts",
    "Compare complete task triplexes against CPU authority",
    "selected_attempts << attempts",
    "cpu_align_attempts << broad_path_align_attempts",
    "triplex_mismatches = 0",
    "Do not use GPU endpoint",
    "Do not use GPU CIGAR",
    "Do not use GPU traceback",
]
missing = [phrase for phrase in required_plan if phrase not in plan]
if missing:
    raise SystemExit("attempt-level consumer shadow plan missing phrases: " + ", ".join(missing))

for forbidden in ("TBD", "TODO", "fill in details"):
    if forbidden in plan:
        raise SystemExit(f"attempt-level consumer shadow plan contains {forbidden!r}")

for phrase in (
    "prototype a materially different scoreInfo plus replacement consumer architecture",
    "reduce scoreInfo/align attempts before replaying CPU aligner state",
    "decision = broad_path_current_architecture_no_go",
):
    if phrase not in broad:
        raise SystemExit(f"broad architecture doc missing phrase: {phrase}")

for phrase in (
    "decision = broad_path_current_architecture_no_go",
    "current architecture should not proceed to a real path",
    "full objective remains open",
):
    if phrase not in current:
        raise SystemExit(f"current-state doc missing phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-plan:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_plan\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-attempt-consumer-shadow-plan target")
PY

echo "ok"
