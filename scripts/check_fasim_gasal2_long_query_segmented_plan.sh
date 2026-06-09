#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/plans/2026-06-05-fasim-long-query-gasal2-segmented-shadow.md"

if [[ ! -s "$PLAN" ]]; then
  echo "missing long-query segmented GASAL2 plan: $PLAN" >&2
  exit 1
fi

python3 - "$PLAN" <<'PY'
import sys
from pathlib import Path

text = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
required = [
    "Fasim Long-Query GASAL2 Segmented Shadow Implementation Plan",
    "CPU fallback remains authority",
    "GASAL2_MAX_QUERY_LEN=2812",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812",
    "GASAL2_MAX_QUERY_LEN=8708",
    "top5_stability_equal=false",
    "FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512",
    "FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0",
    "not production output",
    "not feed results into production output",
    "top5_score_equal=true",
    "top5_stability_equal=true",
    "top5_nt_score_equal=true",
    "GPU total < CPU fallback",
    "decision=not_implemented",
    "decision=top5_artifact_go",
    "decision=top5_artifact_no_go",
    "make check-fasim-gasal2-long-query-segmented-shadow-default-off",
    "make check-fasim-gasal2-top5-formal-gate",
    "no production opt-in step",
    "no endpoint/CIGAR authority step",
]
missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit(
        "long-query segmented GASAL2 plan missing phrases: " + ", ".join(missing)
    )

for forbidden in ("TBD", "TODO", "implement later", "fill in details"):
    if forbidden in text:
        raise SystemExit(f"long-query segmented GASAL2 plan contains {forbidden!r}")
PY

echo "ok"
