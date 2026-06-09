#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_exact_scoreinfo_gpu_column_pruned_output"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"

rm -rf "$WORK"
mkdir -p "$WORK"

BUILD_BIN=1 \
BIN="$BIN" \
TARGET="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
RNA="$ROOT/H19.fa" \
RULE=0 \
TOPK=5 \
PRUNE_MAX_PER_TASK=16 \
EXACT_SCOREINFO_GPU_MAX_PER_TASK=512 \
WORKERS=2 \
GPU_IDS=0,1 \
WORK="$WORK/characterization" \
bash "$ROOT/scripts/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output.sh" \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/characterization" <<'PY'
import csv
import sys
from pathlib import Path

work = Path(sys.argv[1])


rows = list(csv.DictReader((work / "summary.tsv").open(newline="", encoding="utf-8"), delimiter="\t"))
assert len(rows) == 2, rows
exact, column = rows
assert exact["runner_exact_scoreinfo_gpu_column_pruned_output"] == "0", exact
assert column["runner_exact_scoreinfo_gpu_column_pruned_output"] == "1", column
assert int(exact["legacy_score_gpu_requests"]) > 0, exact
assert int(column["legacy_score_gpu_requests"]) == 0, column
assert int(column["exact_scoreinfo_gpu_batches"]) > 0, column
assert int(column["exact_scoreinfo_gpu_overflow_batches"]) == 0, column
assert int(column["exact_scoreinfo_gpu_fallback_batches"]) == 0, column
assert column["top5_all_equal"] == "true", column
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY

echo "ok"
