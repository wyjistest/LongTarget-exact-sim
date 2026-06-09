#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_next_architecture_decision.md"
PLAN="$ROOT/docs/plans/2026-06-06-fasim-long-query-gasal2-next-architecture.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
CANDIDATE_DOC="$ROOT/docs/fasim_gasal2_long_query_exact_tile_candidate_equivalence.md"
OVERLAP_DOC="$ROOT/docs/fasim_gasal2_long_query_exact_tile_overlap_probe.md"
EXACT_COLUMN_DOC="$ROOT/docs/fasim_long_query_exact_column_scoreinfo_shadow.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$DOC" \
  "$PLAN" \
  "$CURRENT_STATE_DOC" \
  "$FULL_GOAL_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$CANDIDATE_DOC" \
  "$OVERLAP_DOC" \
  "$EXACT_COLUMN_DOC" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing GASAL2 long-query next-architecture decision dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$PLAN" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$CANDIDATE_DOC" "$OVERLAP_DOC" "$EXACT_COLUMN_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
plan = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
candidate_doc = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
overlap_doc = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
exact_column_doc = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[9]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Long-Query Next Architecture Decision",
    "decision = next_architecture_no_go",
    "CPU fallback remains authority",
    "current segmented/no-last implementation remains stopped",
    "non-overlap exact-tile candidate equivalence failed",
    "candidate_missing = 1720",
    "candidate_extra = 2039",
    "overlap exact-tile candidate equivalence failed",
    "overlap = 1406",
    "candidate_missing = 1",
    "candidate_extra = 2591",
    "overlap = 2048",
    "candidate_extra = 2961",
    "exact-column non-opt-in cannot launch",
    "error = invalid argument",
    "shared-memory opt-in launches but is not scoreInfo-equivalent",
    "scoreinfo_mismatches = 1",
    "do not promote exact tiling",
    "do not promote overlap tiling",
    "do not promote smem opt-in",
    "do not mark the full objective complete",
    "different execution design",
    "make check-fasim-gasal2-long-query-next-architecture-decision",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "long-query next-architecture decision doc missing phrases: "
        + ", ".join(missing)
    )

for name, text, phrases in (
    ("plan", plan, ["Task 6: Decision Gate", "decision=next_architecture_no_go"]),
    ("candidate", candidate_doc, ["decision = exact_tile_candidate_equivalence_no_go"]),
    ("overlap", overlap_doc, ["decision = exact_tile_overlap_candidate_equivalence_no_go"]),
    ("exact-column", exact_column_doc, ["decision = smem_optin_scoreinfo_no_go"]),
):
    for phrase in phrases:
        if phrase not in text:
            raise SystemExit(f"{name} doc missing phrase: {phrase}")

for name, text in (
    ("current-state", current_state),
    ("full-goal", full_goal),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "make check-fasim-gasal2-long-query-next-architecture-decision",
        "decision = next_architecture_no_go",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing decision phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-long-query-next-architecture-decision:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_next_architecture_decision\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-long-query-next-architecture-decision target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-long-query-next-architecture-decision" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing long-query next-architecture decision dependency")
PY

echo "ok"
