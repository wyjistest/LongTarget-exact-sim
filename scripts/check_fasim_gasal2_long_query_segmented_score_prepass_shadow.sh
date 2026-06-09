#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_score_prepass_shadow"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=1 \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing score-prepass segmented shadow summary: $summary" >&2
  exit 1
fi

python3 - "$summary" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
if row.get("label") != "malat1_first8":
    raise SystemExit(f"unexpected label: {row}")
if row.get("query_len") != "8708":
    raise SystemExit(f"unexpected query_len: {row}")
if row.get("segments") != "4":
    raise SystemExit(f"unexpected segments: {row}")
if row.get("requested") != "1" or row.get("active") != "1":
    raise SystemExit(f"expected active segmented score-prepass shadow: {row}")
if int(row.get("gasal2_requests", "0")) <= 0:
    raise SystemExit(f"expected score-prepass GASAL2 requests: {row}")
if int(row.get("traceback_requests", "0")) != 0:
    raise SystemExit(f"score-prepass shadow must not run traceback: {row}")
if int(row.get("fallbacks", "0")) != 0:
    raise SystemExit(f"score-prepass shadow must be fallback clean: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) != "true":
        raise SystemExit(f"score-prepass shadow changed {key}: {row}")
try:
    total = float(row.get("shadow_total_seconds", "nan"))
except ValueError as exc:
    raise SystemExit(f"invalid shadow_total_seconds: {row}") from exc
if not total > 0:
    raise SystemExit(f"expected positive shadow_total_seconds: {row}")
print(f"decision={row.get('decision')}")
PY
