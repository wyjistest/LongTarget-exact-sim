#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_score_prepass_reduction"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
MAX_PER_TASK="${MAX_PER_TASK:-8}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK="$MAX_PER_TASK" \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing score-prepass reduction summary: $summary" >&2
  exit 1
fi

python3 - "$summary" "$MAX_PER_TASK" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
max_per_task = int(sys.argv[2])
if row.get("label") != "malat1_first8":
    raise SystemExit(f"unexpected label: {row}")
if row.get("query_len") != "8708" or row.get("segments") != "4":
    raise SystemExit(f"unexpected query/segment telemetry: {row}")
if row.get("requested") != "1" or row.get("active") != "1":
    raise SystemExit(f"expected active segmented score-prepass reduction shadow: {row}")
if row.get("scoreinfo_max_per_task") != str(max_per_task):
    raise SystemExit(f"unexpected scoreinfo_max_per_task: {row}")
if int(row.get("traceback_requests", "0")) != 0:
    raise SystemExit(f"reduction score-prepass shadow must not run traceback: {row}")
if int(row.get("fallbacks", "0")) != 0:
    raise SystemExit(f"reduction shadow must be fallback clean: {row}")
requests = int(row.get("gasal2_requests", "0"))
if requests <= 0:
    raise SystemExit(f"expected reduced GASAL2 requests: {row}")
if requests >= 500352:
    raise SystemExit(f"expected request reduction below unpruned 500352: {row}")
if int(row.get("scoreinfo_pruned_groups", "0")) <= 0:
    raise SystemExit(f"expected scoreInfo groups to be pruned: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) != "true":
        raise SystemExit(f"reduction shadow changed {key}: {row}")
print(f"decision={row.get('decision')}")
PY
