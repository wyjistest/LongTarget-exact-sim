#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_record_limit"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-3}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  MALAT1_RECORD_LIMIT="$MALAT1_RECORD_LIMIT" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK=37 \
  SCOREINFO_PRUNE_MODE=score_position_edges \
  SEGMENTED_MAX_TASKS=64 \
  CPU_TRACEBACK_REPLAY=1 \
  CPU_TRACEBACK_NO_LAST=1 \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing record-limit summary: $summary" >&2
  exit 1
fi

python3 - "$summary" "$MALAT1_RECORD_LIMIT" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
record_limit = int(sys.argv[2])
expected_label = f"malat1_first{record_limit}"
if row.get("label") != expected_label:
    raise SystemExit(f"expected label {expected_label}, got {row.get('label')}: {row}")
if int(row.get("target_record_limit", "0")) != record_limit:
    raise SystemExit(f"expected target_record_limit={record_limit}: {row}")
if row.get("requested") != "1" or row.get("active") != "1":
    raise SystemExit(f"expected active segmented replay candidate: {row}")
if row.get("cpu_traceback_no_last") != "1":
    raise SystemExit(f"expected no-last mode: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) not in {"true", "false"}:
        raise SystemExit(f"missing {key}: {row}")
print(f"label={row.get('label')} decision={row.get('decision')}")
PY
