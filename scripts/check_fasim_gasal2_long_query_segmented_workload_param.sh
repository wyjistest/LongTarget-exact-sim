#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_workload_param"}"

rm -rf "$WORK"
mkdir -p "$WORK"

if timeout 5s env \
  WORK="$WORK/bad_limit" \
  WORKLOAD_NAME=NEAT1 \
  RECORD_LIMIT=0 \
  BUILD_BIN=0 \
  BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
  bash "$SCRIPT" >"$WORK/bad_limit.stdout.log" 2>"$WORK/bad_limit.stderr.log"; then
  echo "expected RECORD_LIMIT=0 to fail" >&2
  exit 1
fi
grep -q 'RECORD_LIMIT must be positive' "$WORK/bad_limit.stderr.log"

if ! command -v timeout >/dev/null 2>&1; then
  echo "timeout command is required for workload-param smoke" >&2
  exit 1
fi

timeout 20s env \
  WORK="$WORK/neat1" \
  WORKLOAD_NAME=NEAT1 \
  RECORD_LIMIT=1 \
  RNA_INPUT="$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa" \
  DNA_INPUT="$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
  BUILD_BIN=0 \
  BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
  SCORE_PREPASS_SHADOW=1 \
  SCOREINFO_MAX_PER_TASK=1 \
  SEGMENTED_MAX_TASKS=1 \
  bash "$SCRIPT" >"$WORK/neat1.stdout.log" 2>"$WORK/neat1.stderr.log" || {
    status=$?
    if [[ "$status" == "124" ]]; then
      echo "NEAT1 workload-param smoke timed out before summary" >&2
    fi
    exit "$status"
  }

python3 - "$WORK/neat1/summary.tsv" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one row, got {len(rows)}")
row = rows[0]
if row.get("label") != "neat1_first1":
    raise SystemExit(f"unexpected label: {row}")
if row.get("target_record_limit") != "1":
    raise SystemExit(f"unexpected target_record_limit: {row}")
if int(row.get("query_len", "0")) <= 0:
    raise SystemExit(f"missing query_len: {row}")
if row.get("scoreinfo_max_per_task") != "1":
    raise SystemExit(f"unexpected scoreinfo_max_per_task: {row}")
PY

echo "ok"
