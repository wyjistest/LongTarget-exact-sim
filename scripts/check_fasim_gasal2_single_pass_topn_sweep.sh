#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_single_pass_topn_sweep"}"

rm -rf "$WORK"
mkdir -p "$WORK"

WORK="$WORK/characterization" \
TOPN_VALUES="${TOPN_VALUES:-64 128 256}" \
bash "$ROOT/scripts/characterize_fasim_gasal2_single_pass_topn_sweep.sh" \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/characterization/summary.tsv" "$WORK/characterization/decision.txt" "$WORK/characterization/top5_diff.tsv" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
decision_path = Path(sys.argv[2])
diff_path = Path(sys.argv[3])

rows = list(csv.DictReader(summary_path.open(), delimiter="\t"))
assert len(rows) >= 2, rows
exact = rows[0]
assert exact["label"] == "exact_pruned_output", exact
assert int(exact["legacy_score_gpu_requests"]) > 0, exact
assert int(exact["exact_scoreinfo_gpu_batches"]) > 0, exact
for row in rows[1:]:
    assert row["label"].startswith("single_pass_topn"), row
    assert int(row["single_pass_topn_batches"]) > 0, row
    assert int(row["single_pass_topn_tasks"]) > 0, row
    assert int(row["legacy_score_gpu_requests"]) == 0, row
    assert int(row["exact_scoreinfo_gpu_batches"]) == 0, row
    assert row["top5_all_equal"] in {"true", "false"}, row
decision = decision_path.read_text(encoding="utf-8")
assert decision.strip(), decision_path
diff_rows = list(csv.DictReader(diff_path.open(), delimiter="\t"))
if "single_pass_top5_clean_labels=\n" in decision:
    assert diff_rows, diff_path
PY

echo "ok"
