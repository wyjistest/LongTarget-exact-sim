#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/plans/2026-06-06-fasim-long-query-gasal2-next-architecture.md"
CURRENT_STOP_DOC="$ROOT/docs/fasim_gasal2_long_query_current_stop.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$PLAN" "$CURRENT_STOP_DOC" "$FULL_GOAL_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing GASAL2 long-query next-architecture dependency: $path" >&2
    exit 1
  fi
done

python3 - "$PLAN" "$CURRENT_STOP_DOC" "$FULL_GOAL_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

plan = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_stop = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_plan = [
    "Fasim Long-Query GASAL2 Next Architecture Implementation Plan",
    "Goal: Prototype a different long-query architecture",
    "current segmented/no-last implementation remains stopped",
    "do not continue current segmented/no-last implementation as a real path",
    "CPU fallback remains authority",
    "no production opt-in step",
    "no endpoint/CIGAR authority step",
    "no GASAL2 traceback output authority",
    "FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1",
    "query tiling with exact candidate equivalence",
    "CPU oracle candidate export",
    "tile descriptor generator",
    "exact candidate equivalence shadow",
    "full-output equivalence proof remains separate",
    "scoreinfo_gasal2_active = 1",
    "fallback = 0",
    "top5 score/stability/nt_score clean",
    "GPU/GASAL2 total < CPU fallback by a meaningful margin",
    "decision=next_architecture_not_implemented",
    "decision=next_architecture_go",
    "decision=next_architecture_no_go",
    "make check-fasim-gasal2-long-query-next-architecture-plan",
    "make check-fasim-gasal2-long-query-current-stop",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "make check-fasim-gasal2-long-query-exact-tile-oracle-export",
    "make check-fasim-gasal2-long-query-exact-tile-descriptors",
    "make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result",
    "make check-fasim-gasal2-long-query-exact-tile-overlap-result",
]
missing = [phrase for phrase in required_plan if phrase not in plan]
if missing:
    raise SystemExit(
        "long-query next-architecture plan missing phrases: " + ", ".join(missing)
    )

for forbidden in ("TBD", "TODO", "implement later", "fill in details"):
    if forbidden in plan:
        raise SystemExit(f"long-query next-architecture plan contains {forbidden!r}")

for name, text in (
    ("current-stop", current_stop),
    ("full-goal", full_goal),
    ("current-state", current_state),
):
    if "make check-fasim-gasal2-long-query-next-architecture-plan" not in text:
        raise SystemExit(f"{name} doc missing next-architecture plan gate")

target = re.search(
    r"^check-fasim-gasal2-long-query-next-architecture-plan:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_next_architecture_plan\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-next-architecture-plan target")

oracle_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-oracle-export:\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct bash "
    r"\./scripts/check_fasim_gasal2_long_query_exact_tile_oracle_export\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not oracle_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-exact-tile-oracle-export target")

descriptor_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-descriptors:\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct bash "
    r"\./scripts/check_fasim_gasal2_long_query_exact_tile_descriptors\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not descriptor_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-exact-tile-descriptors target")

candidate_result_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence_result\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not candidate_result_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result target")

overlap_result_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-overlap-result:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_exact_tile_overlap_result\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not overlap_result_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-exact-tile-overlap-result target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-long-query-next-architecture-plan" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing long-query next-architecture dependency")
PY

echo "ok"
