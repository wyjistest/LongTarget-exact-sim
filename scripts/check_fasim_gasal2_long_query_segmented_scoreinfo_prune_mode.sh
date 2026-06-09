#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_scoreinfo_prune_mode"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
MAX_PER_TASK="${MAX_PER_TASK:-37}"
SEGMENTED_MAX_TASKS="${SEGMENTED_MAX_TASKS:-64}"
PRUNE_MODE="${PRUNE_MODE:-score_position_edges}"
REQUIRE_TOP5_CLEAN="${REQUIRE_TOP5_CLEAN:-1}"

rm -rf "$WORK"
mkdir -p "$WORK"

strings "$BIN" >"$WORK/strings.txt"
grep -q 'FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE' "$WORK/strings.txt"
grep -q 'FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE' \
  "$ROOT/docs/fasim_gasal2_long_query_segmented_shadow.md"

bash "$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh" \
  WORK="$WORK/run" \
  BIN="$BIN" \
  BUILD_BIN="${BUILD_BIN:-1}" \
  TILE_LEN="${TILE_LEN:-2812}" \
  TILE_OVERLAP="${TILE_OVERLAP:-512}" \
  MAX_SEGMENTS="${MAX_SEGMENTS:-4}" \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK="$MAX_PER_TASK" \
  SCOREINFO_PRUNE_MODE="$PRUNE_MODE" \
  SEGMENTED_MAX_TASKS="$SEGMENTED_MAX_TASKS" \
  CPU_TRACEBACK_REPLAY=1 \
  >"$WORK/stdout.log"

summary="$WORK/run/summary.tsv"
if [[ ! -s "$summary" ]]; then
  echo "missing prune-mode summary: $summary" >&2
  exit 1
fi

python3 - "$summary" "$MAX_PER_TASK" "$PRUNE_MODE" "$REQUIRE_TOP5_CLEAN" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(rows)}")
row = rows[0]
max_per_task = int(sys.argv[2])
prune_mode = sys.argv[3]

if row.get("label") != "malat1_first8":
    raise SystemExit(f"unexpected label: {row}")
if row.get("requested") != "1" or row.get("active") != "1":
    raise SystemExit(f"expected active segmented replay candidate: {row}")
if row.get("scoreinfo_max_per_task") != str(max_per_task):
    raise SystemExit(f"unexpected scoreinfo_max_per_task: {row}")
if row.get("scoreinfo_prune_mode") != prune_mode:
    raise SystemExit(f"unexpected scoreinfo_prune_mode: {row}")
if int(row.get("traceback_requests", "0")) != 0:
    raise SystemExit(f"prune-mode replay must not use GASAL2 traceback: {row}")
if int(row.get("fallbacks", "0")) != 0:
    raise SystemExit(f"prune-mode replay must be fallback clean: {row}")
if int(row.get("gasal2_requests", "0")) <= 0:
    raise SystemExit(f"expected GASAL2 score requests: {row}")
if int(row.get("gasal2_score_batches", "0")) <= 0:
    raise SystemExit(f"expected GASAL2 score batches: {row}")
if int(row.get("cpu_replay_align_calls", "0")) <= 0:
    raise SystemExit(f"expected CPU replay Align calls: {row}")
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if row.get(key) not in {"true", "false"}:
        raise SystemExit(f"missing {key}: {row}")
if len(sys.argv) > 4 and sys.argv[4] == "1":
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row.get(key) != "true":
            raise SystemExit(f"expected {key}=true for prune-mode gate: {row}")
print(f"decision={row.get('decision')} prune_mode={row.get('scoreinfo_prune_mode')}")
PY
