#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_exact_tile_candidate_equivalence.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing exact-tile candidate-equivalence result dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[2]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Long-Query Exact-Tile Candidate Equivalence",
    "decision = exact_tile_candidate_equivalence_no_go",
    "FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_CANDIDATE_EQUIVALENCE=1",
    "CPU fallback remains authority",
    "active = 1",
    "query_len = 8708",
    "tile_len = 2812",
    "tiles = 4",
    "cpu_oracle_candidates = 31272",
    "tile_candidates = 31591",
    "candidate_missing = 1720",
    "candidate_extra = 2039",
    "fallback = 0",
    "output digest unchanged",
    "non-overlap exact tiling is not candidate-equivalent",
    "do not promote this exact-tile shape to a real path",
    "make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence",
    "make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "exact-tile candidate-equivalence result doc missing phrases: "
        + ", ".join(missing)
    )

future_gate = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-candidate-equivalence:\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct bash "
    r"\./scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not future_gate:
    raise SystemExit("Makefile missing exact-tile candidate-equivalence future gate")

result_gate = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence_result\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not result_gate:
    raise SystemExit("Makefile missing exact-tile candidate-equivalence result gate")
PY

echo "ok"
