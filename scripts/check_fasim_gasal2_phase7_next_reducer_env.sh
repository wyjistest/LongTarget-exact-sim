#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
STATS="$ROOT/fasim/gasal2_align_bridge.h"
MAKEFILE="$ROOT/Makefile"

python3 - "$FASTSIM" "$STATS" "$MAKEFILE" <<'PY'
from pathlib import Path
import re
import sys

fastsim = Path(sys.argv[1]).read_text(encoding="utf-8")
stats = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_fastsim = [
    "FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW",
    "fasim_gasal2_phase7_next_reducer_shadow_runtime",
]
for needle in required_fastsim:
    if needle not in fastsim:
        raise SystemExit(f"missing fastsim marker: {needle}")

required_stats = [
    "phase7_next_reducer_requested",
    "phase7_next_reducer_active",
    "phase7_next_reducer_tasks",
    "phase7_next_reducer_scoreinfos",
    "phase7_next_reducer_reference_attempts",
    "phase7_next_reducer_candidate_attempts",
    "phase7_next_reducer_candidate_align_attempts",
    "phase7_next_reducer_reference_align_attempts",
    "phase7_next_reducer_false_negative_scoreinfos",
    "phase7_next_reducer_triplex_mismatches",
    "phase7_next_reducer_missing_triplexes",
    "phase7_next_reducer_extra_triplexes",
    "phase7_next_reducer_digest_match",
    "phase7_next_reducer_full_rows_equal",
    "phase7_next_reducer_baseline_wall_seconds",
    "phase7_next_reducer_candidate_wall_seconds",
    "phase7_next_reducer_candidate_vs_baseline",
]
for needle in required_stats:
    if needle not in stats:
        raise SystemExit(f"missing stats marker: {needle}")

target = re.search(
    r"^check-fasim-gasal2-phase7-next-reducer-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_phase7_next_reducer_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("missing Makefile env target")

print("ok")
PY
