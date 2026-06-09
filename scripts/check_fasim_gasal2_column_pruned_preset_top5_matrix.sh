#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_column_pruned_preset_top5_matrix"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

rm -rf "$WORK"
mkdir -p "$WORK"

TARGET_PRESETS="${TARGET_PRESETS:-small}" \
REPEATS="${REPEATS:-1}" \
BUILD_BIN=1 \
BIN="$BIN" \
WORK="$WORK/matrix" \
bash "$ROOT/scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh" \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/matrix/aggregate.tsv" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
assert rows, rows
for row in rows:
    runs = int(row["runs"])
    assert int(row["artifact_checked_runs"]) == runs, row
    assert int(row["top5_clean_runs"]) == runs, row
    assert int(row["active_path_runs"]) == runs, row
    assert int(row["zero_legacy_score_runs"]) == runs, row
    assert int(row["zero_overflow_runs"]) == runs, row
    assert int(row["zero_fallback_runs"]) == runs, row
    assert int(row["zero_gasal2_fallback_runs"]) == runs, row
    assert int(row["zero_length_guard_fallback_runs"]) == runs, row
    assert float(row["speedup_vs_cpu_worker_wall_sum_min"]) > 0.0, row
    assert float(row["speedup_vs_cpu_max_worker_wall_min"]) > 0.0, row
PY

cat "$WORK/matrix/decision.txt"
echo "ok"
