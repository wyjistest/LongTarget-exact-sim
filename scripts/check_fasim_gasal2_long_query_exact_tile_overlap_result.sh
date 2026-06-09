#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_exact_tile_overlap_probe.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing exact-tile overlap result dependency: $path" >&2
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
    "Fasim GASAL2 Long-Query Exact-Tile Overlap Probe",
    "decision = exact_tile_overlap_candidate_equivalence_no_go",
    "FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_OVERLAP",
    "CPU fallback remains authority",
    "output digest unchanged",
    "overlap = 1406",
    "tiles = 6",
    "tile_descriptor_digest = 8144326404929707858",
    "cpu_oracle_candidates = 31272",
    "tile_candidates = 33862",
    "candidate_missing = 1",
    "candidate_extra = 2591",
    "position_missing = 1",
    "position_extra = 2397",
    "position_score_mismatches = 0",
    "overlap = 2048",
    "tiles = 9",
    "tile_descriptor_digest = 11322515831205853531",
    "tile_candidates = 34232",
    "candidate_extra = 2961",
    "position_extra = 2644",
    "larger overlap reduces missing candidates but increases extra candidates",
    "position_score_mismatches = 0 means this is not a score remapping problem",
    "tile-local DP creates positions absent from full-query CPU oracle",
    "do not promote overlap exact tiling to a real path",
    "make check-fasim-gasal2-long-query-exact-tile-overlap-probe",
    "make check-fasim-gasal2-long-query-exact-tile-overlap-result",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "exact-tile overlap result doc missing phrases: " + ", ".join(missing)
    )

probe_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-overlap-probe:\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct bash "
    r"\./scripts/check_fasim_gasal2_long_query_exact_tile_overlap_probe\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not probe_target:
    raise SystemExit("Makefile missing exact-tile overlap probe target")

result_target = re.search(
    r"^check-fasim-gasal2-long-query-exact-tile-overlap-result:\n"
    r"\tbash \./scripts/check_fasim_gasal2_long_query_exact_tile_overlap_result\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not result_target:
    raise SystemExit("Makefile missing exact-tile overlap result target")
PY

echo "ok"
