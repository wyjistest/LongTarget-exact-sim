#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_exact_scoreinfo_gpu_max_per_task_sweep"}"

rm -rf "$WORK"
mkdir -p "$WORK"

TARGET="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
MAX_PER_TASK_VALUES="512 2048" \
PRUNE_MAX_PER_TASK=16 \
WORK="$WORK/sweep" \
bash "$ROOT/scripts/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh" \
  >"$WORK/sweep.stdout.log" \
  2>"$WORK/sweep.stderr.log"

python3 - "$WORK/sweep/summary.tsv" "$WORK/sweep/decision.txt" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
decision_path = Path(sys.argv[2])

rows = list(csv.DictReader(summary_path.open(encoding="utf-8"), delimiter="\t"))
labels = [row["label"] for row in rows]
assert labels == ["default", "max512", "max2048"], labels

for row in rows:
    assert row["top5_score_equal"] == "true", row
    assert row["top5_stability_equal"] == "true", row
    assert row["top5_nt_score_equal"] == "true", row
    assert row["top5_all_equal"] == "true", row
    assert "runner_exact_scoreinfo_gpu_max_per_task" in row, row
    assert int(row["traceback_requests"]) > 0, row
    assert int(row["scoreinfo_groups"]) > 0, row
    assert int(row["exact_scoreinfo_gpu_enabled_shards"]) > 0, row
    assert int(row["exact_scoreinfo_gpu_tasks"]) > 0, row
    assert float(row["exact_scoreinfo_gpu_wall_seconds"]) > 0.0, row
    assert float(row["exact_scoreinfo_gpu_kernel_seconds"]) > 0.0, row
    assert float(row["exact_column_wall_seconds"]) == 0.0, row
    assert float(row["exact_column_kernel_seconds"]) == 0.0, row

assert rows[0]["exact_scoreinfo_gpu_max_per_task"] == "default", rows[0]
assert rows[0]["runner_exact_scoreinfo_gpu_max_per_task"] == "2048", rows[0]
assert rows[1]["exact_scoreinfo_gpu_max_per_task"] == "512", rows[1]
assert rows[1]["runner_exact_scoreinfo_gpu_max_per_task"] == "512", rows[1]
assert rows[2]["exact_scoreinfo_gpu_max_per_task"] == "2048", rows[2]
assert rows[2]["runner_exact_scoreinfo_gpu_max_per_task"] == "2048", rows[2]

decision = {}
for line in decision_path.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        decision[key] = value

assert decision["best_top5_clean_label"], decision
assert float(decision["best_top5_clean_wall_seconds"]) > 0.0, decision
assert float(decision["best_top5_clean_speedup_vs_baseline"]) > 0.0, decision
assert float(decision["best_top5_clean_exact_scoreinfo_gpu_wall_seconds"]) > 0.0, decision
PY

if TOPK=3 \
  WORK="$WORK/topk_not_5" \
  bash "$ROOT/scripts/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh" \
  >"$WORK/topk_not_5.stdout.log" \
  2>"$WORK/topk_not_5.stderr.log"; then
  echo "expected TOPK!=5 exact scoreInfo GPU sweep to fail" >&2
  exit 1
fi
grep -q 'exact scoreInfo GPU max-per-task sweep requires TOPK=5' \
  "$WORK/topk_not_5.stderr.log"

echo "ok"
