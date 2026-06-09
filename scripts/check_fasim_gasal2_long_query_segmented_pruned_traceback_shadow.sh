#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_pruned_traceback_shadow"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
MAX_PER_TASK="${MAX_PER_TASK:-37}"
PRUNE_MODE="${PRUNE_MODE:-score_position_edges}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  MALAT1_RECORD_LIMIT="$MALAT1_RECORD_LIMIT" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=0 \
  SCOREINFO_MAX_PER_TASK="$MAX_PER_TASK" \
  SCOREINFO_PRUNE_MODE="$PRUNE_MODE" \
  SEGMENTED_MAX_TASKS=64 \
  CPU_TRACEBACK_REPLAY=0 \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing pruned traceback summary: $summary" >&2
  exit 1
fi

python3 - "$summary" "$MALAT1_RECORD_LIMIT" "$MAX_PER_TASK" "$PRUNE_MODE" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
record_limit = int(sys.argv[2])
max_per_task = int(sys.argv[3])
prune_mode = sys.argv[4]

if row.get("label") != f"malat1_first{record_limit}":
    raise SystemExit(f"unexpected label: {row}")
if row.get("scoreinfo_max_per_task") != str(max_per_task):
    raise SystemExit(f"expected pruned traceback max_per_task={max_per_task}: {row}")
if row.get("scoreinfo_prune_mode") != prune_mode:
    raise SystemExit(f"unexpected prune mode: {row}")
if int(row.get("traceback_requests", "0")) <= 0:
    raise SystemExit(f"expected GASAL2 traceback requests: {row}")
if int(row.get("cpu_replay_attempts", "0")) != 0:
    raise SystemExit(f"pruned traceback shadow must not run CPU replay: {row}")
if int(row.get("fallbacks", "0")) != 0:
    raise SystemExit(f"pruned traceback shadow must be fallback clean: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) != "true":
        raise SystemExit(f"CPU-authority output should remain top5 clean for {key}: {row}")
print(
    "decision="
    f"{row.get('decision')} traceback_requests={row.get('traceback_requests')} "
    f"shadow_total={row.get('shadow_total_seconds')}"
)
PY
