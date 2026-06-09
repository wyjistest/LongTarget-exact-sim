#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_score_order"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
MAX_PER_TASK="${MAX_PER_TASK:-37}"
SEGMENTED_MAX_TASKS="${SEGMENTED_MAX_TASKS:-64}"
PRUNE_MODE="${PRUNE_MODE:-score_position_edges}"
CPU_TRACEBACK_ORDER="${CPU_TRACEBACK_ORDER:-threshold_score}"
MAX_ALIGN_CALLS="${MAX_ALIGN_CALLS:-70000}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  MALAT1_RECORD_LIMIT="$MALAT1_RECORD_LIMIT" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK="$MAX_PER_TASK" \
  SCOREINFO_PRUNE_MODE="$PRUNE_MODE" \
  SEGMENTED_MAX_TASKS="$SEGMENTED_MAX_TASKS" \
  CPU_TRACEBACK_REPLAY=1 \
  CPU_TRACEBACK_NO_LAST=1 \
  CPU_TRACEBACK_ORDER="$CPU_TRACEBACK_ORDER" \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing score-order replay summary: $summary" >&2
  exit 1
fi

python3 - "$summary" "$MALAT1_RECORD_LIMIT" "$MAX_ALIGN_CALLS" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
record_limit = int(sys.argv[2])
max_align_calls = int(sys.argv[3])

if row.get("label") != f"malat1_first{record_limit}":
    raise SystemExit(f"unexpected label: {row}")
if row.get("cpu_traceback_no_last") != "1":
    raise SystemExit(f"expected no-last mode: {row}")
if row.get("cpu_traceback_order") != "threshold_score":
    raise SystemExit(f"expected threshold_score replay order: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) != "true":
        raise SystemExit(f"expected {key}=true for score-order gate: {row}")
align_calls = int(row.get("cpu_replay_align_calls", "0"))
if align_calls <= 0 or align_calls > max_align_calls:
    raise SystemExit(f"expected replay align calls <= {max_align_calls}, got {align_calls}: {row}")
print(f"decision={row.get('decision')} align_calls={align_calls} order={row.get('cpu_traceback_order')}")
PY
