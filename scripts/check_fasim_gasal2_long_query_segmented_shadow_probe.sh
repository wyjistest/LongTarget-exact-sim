#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_shadow_probe"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing segmented shadow summary: $summary" >&2
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
if row.get("tile_len") != "2812":
    raise SystemExit(f"unexpected tile_len: {row}")
if row.get("tile_overlap") != "512":
    raise SystemExit(f"unexpected tile_overlap: {row}")
if row.get("max_segments") != "4":
    raise SystemExit(f"unexpected max_segments: {row}")
segments = int(row.get("segments", "0"))
if segments != 4:
    raise SystemExit(f"expected four bounded segments: {row}")
if row.get("requested") != "1":
    raise SystemExit(f"expected requested segmented shadow: {row}")
decision = row.get("decision")
active = row.get("active")
if active != "1":
    raise SystemExit(f"expected active segmented execution shadow: {row}")
if decision not in {"top5_artifact_go", "top5_artifact_no_go"}:
    raise SystemExit(f"unexpected active decision: {row}")
if int(row.get("gasal2_requests", "0")) <= 0:
    raise SystemExit(f"expected segmented GASAL2 requests: {row}")
if int(row.get("traceback_requests", "0")) <= 0:
    raise SystemExit(f"expected segmented GASAL2 traceback requests: {row}")
if row.get("fallbacks") is None:
    raise SystemExit(f"missing fallback count: {row}")
try:
    float(row.get("shadow_total_seconds", "nan"))
except ValueError as exc:
    raise SystemExit(f"invalid shadow_total_seconds: {row}") from exc
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) not in {"true", "false"}:
        raise SystemExit(f"missing {key}: {row}")
print(f"decision={decision}")
PY
