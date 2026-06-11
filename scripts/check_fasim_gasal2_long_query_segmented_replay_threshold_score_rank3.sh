#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_threshold_score_rank3"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  WORKLOAD_NAME=NEAT1 \
  RECORD_LIMIT=1 \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS=0 \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK=37 \
  SCOREINFO_PRUNE_MODE=score_position_edges \
  SEGMENTED_MAX_TASKS=4 \
  CPU_TRACEBACK_REPLAY=1 \
  CPU_TRACEBACK_NO_LAST=1 \
  CPU_TRACEBACK_ORDER=threshold_score \
  CPU_TRACEBACK_MAX_RANK=3 \
  >"$WORK.stdout.log"

summary="$WORK/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing threshold-score rank3 replay summary: $summary" >&2
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
expected = {
    "label": "neat1_first1",
    "max_segments": "0",
    "cpu_traceback_no_last": "1",
    "cpu_traceback_order": "threshold_score",
    "cpu_traceback_max_rank": "3",
    "scoreinfo_max_per_task": "37",
    "scoreinfo_prune_mode": "score_position_edges",
    "fallbacks": "0",
}
for key, value in expected.items():
    if row.get(key) != value:
        raise SystemExit(f"{key}={row.get(key)!r}, expected {value!r}: {row}")
if int(row.get("cpu_replay_align_calls", "0")) <= 0:
    raise SystemExit(f"expected positive cpu_replay_align_calls: {row}")
if int(row.get("cpu_traceback_rank_cutoff_skipped", "0")) < 0:
    raise SystemExit(f"missing rank-cutoff skip telemetry: {row}")
PY

echo "ok"
