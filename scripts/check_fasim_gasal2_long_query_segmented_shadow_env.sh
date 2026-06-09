#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_segmented_shadow.md"

if [[ ! -s "$DOC" ]]; then
  echo "missing segmented shadow doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" <<'PY'
import sys
from pathlib import Path

text = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
required = [
    "FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512",
    "FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0",
    "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested",
    "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active",
    "active` must remain `0`",
    "CPU fallback remains authority",
    "not production output",
    "top5_score_equal = true",
    "top5_stability_equal = true",
    "top5_nt_score_equal = true",
    "GPU total < CPU fallback",
    "make check-fasim-gasal2-long-query-segmented-shadow-default-off",
]
missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit("segmented shadow doc missing phrases: " + ", ".join(missing))
PY

echo "ok"
