#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_prealign_max_tasks_probe"}"

rm -rf "$WORK"
mkdir -p "$WORK"

PREALIGN_CUDA_MAX_TASKS_VALUES="${PREALIGN_CUDA_MAX_TASKS_VALUES:-4096 8192 32768}" \
WORK="$WORK/probe" \
bash "$ROOT/scripts/characterize_fasim_gasal2_prealign_max_tasks_probe.sh" \
  >"$WORK/probe.stdout.log" \
  2>"$WORK/probe.stderr.log"

python3 - "$WORK/probe/summary.tsv" "$WORK/probe/decision.txt" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
decision_path = Path(sys.argv[2])

rows = list(csv.DictReader(summary_path.open(encoding="utf-8"), delimiter="\t"))
labels = [row["label"] for row in rows]
assert labels == ["formal_default", "max4096", "max8192", "max32768"], labels

for row in rows:
    assert row["topk_payload_equal_vs_formal"] == "true", row
    assert row["topk_rows_payload_equal_vs_formal"] == "true", row
    assert row["topk_lite_equal_vs_formal"] == "true", row
    assert row["scoreinfo_rank_observe_enabled_shards"] == row["shard_count"], row
    assert int(row["scoreinfo_rank_observe_rows"]) > 0, row
    assert int(row["scoreinfo_rank_observe_unknown_rows"]) == 0, row
    assert int(row["scoreinfo_rank_observe_max_rank"]) > 0, row
    assert int(row["gasal2_requests"]) > 0, row
    assert int(row["gasal2_traceback_requests"]) > 0, row
    assert int(row["exact_scoreinfo_gpu_tasks"]) > 0, row
    assert int(row["exact_scoreinfo_gpu_overflow_batches"]) == 0, row
    assert int(row["exact_scoreinfo_gpu_fallback_batches"]) == 0, row
    assert float(row["wall_seconds"]) > 0.0, row

assert rows[0]["result_contract"] == "gasal2_top5_column_pruned_scoreinfo_artifact_v1", rows[0]
assert rows[0]["prealign_cuda_max_tasks"] == "16384", rows[0]
assert rows[1]["result_contract"] == "gasal2_top5_scoreinfo_artifact_v1", rows[1]
assert rows[1]["prealign_cuda_max_tasks"] == "4096", rows[1]
assert rows[2]["result_contract"] == "gasal2_top5_scoreinfo_artifact_v1", rows[2]
assert rows[2]["prealign_cuda_max_tasks"] == "8192", rows[2]
assert rows[3]["result_contract"] == "gasal2_top5_scoreinfo_artifact_v1", rows[3]
assert rows[3]["prealign_cuda_max_tasks"] == "32768", rows[3]

decision = {}
for line in decision_path.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        decision[key] = value

assert decision["best_top5_clean_label"] in labels, decision
assert float(decision["best_top5_clean_wall_seconds"]) > 0.0, decision
assert float(decision["best_top5_clean_speedup_vs_formal"]) > 0.0, decision
PY

echo "ok"
