#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_scoreinfo_prune_sweep"}"

rm -rf "$WORK"
mkdir -p "$WORK"

TARGET="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
PRUNE_VALUES="16 12" \
WORK="$WORK/sweep" \
bash "$ROOT/scripts/characterize_fasim_gasal2_scoreinfo_prune_sweep.sh" \
  >"$WORK/sweep.stdout.log" \
  2>"$WORK/sweep.stderr.log"

python3 - "$WORK/sweep/summary.tsv" "$WORK/sweep/decision.txt" "$WORK/sweep/top5_diff.tsv" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
decision_path = Path(sys.argv[2])
diff_path = Path(sys.argv[3])

rows = list(csv.DictReader(summary_path.open(encoding="utf-8"), delimiter="\t"))
labels = [row["label"] for row in rows]
assert labels == ["artifact", "prune16", "prune12"], labels

artifact, prune16, prune12 = rows
assert artifact["top5_all_equal"] == "true", artifact
for row in (prune16, prune12):
    assert row["top5_score_equal"] == "true", row
    assert int(row["traceback_requests"]) > 0, row
    assert int(row["scoreinfo_pruned_groups"]) > 0, row
    assert float(row["gasal2_total_seconds"]) > 0.0, row
    assert "exact_column_wall_seconds" in row, row
    assert "exact_column_h2d_seconds" in row, row
    assert "exact_column_d2h_seconds" in row, row
    assert "exact_scoreinfo_gpu_wall_seconds" in row, row
    assert "exact_scoreinfo_gpu_kernel_seconds" in row, row
    assert "exact_scoreinfo_gpu_h2d_seconds" in row, row
    assert "exact_scoreinfo_gpu_d2h_seconds" in row, row
    assert "exact_scoreinfo_gpu_enabled_shards" in row, row
    assert "runner_exact_scoreinfo_gpu_max_per_task" in row, row
    assert float(row["exact_column_kernel_seconds"]) >= 0.0, row
    assert float(row["exact_column_wall_seconds"]) >= 0.0, row
    assert float(row["exact_scoreinfo_gpu_kernel_seconds"]) >= 0.0, row
    assert float(row["exact_scoreinfo_gpu_wall_seconds"]) >= 0.0, row

assert prune16["top5_stability_equal"] == "true", prune16
assert prune16["top5_nt_score_equal"] == "true", prune16
assert prune16["top5_all_equal"] == "true", prune16
assert prune12["top5_all_equal"] == "false", prune12
assert (
    prune12["top5_stability_equal"] == "false"
    or prune12["top5_nt_score_equal"] == "false"
), prune12

decision = {}
for line in decision_path.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        decision[key] = value

assert decision["best_top5_clean_label"] == "prune16", decision
assert decision["best_top5_clean_max_per_task"] == "16", decision
assert float(decision["best_top5_clean_wall_seconds"]) > 0.0, decision
assert float(decision["best_top5_clean_speedup_vs_baseline"]) > 0.0, decision

diff_rows = list(csv.DictReader(diff_path.open(encoding="utf-8"), delimiter="\t"))
assert diff_rows, diff_rows
assert any(row["label"] == "prune12" and row["kind"] == "missing" for row in diff_rows), diff_rows
assert any(row["label"] == "prune12" and row["kind"] == "extra" for row in diff_rows), diff_rows
PY

if TOPK=3 \
  WORK="$WORK/topk_not_5" \
  bash "$ROOT/scripts/characterize_fasim_gasal2_scoreinfo_prune_sweep.sh" \
  >"$WORK/topk_not_5.stdout.log" \
  2>"$WORK/topk_not_5.stderr.log"; then
  echo "expected TOPK!=5 sweep to fail" >&2
  exit 1
fi
grep -q 'scoreInfo-prune sweep requires TOPK=5' "$WORK/topk_not_5.stderr.log"

echo "ok"
