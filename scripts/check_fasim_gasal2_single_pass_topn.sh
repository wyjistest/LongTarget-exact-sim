#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_single_pass_topn"}"

rm -rf "$WORK"
mkdir -p "$WORK"

WORK="$WORK/characterization" \
bash "$ROOT/scripts/characterize_fasim_gasal2_single_pass_topn.sh" \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/characterization/summary.tsv" "$WORK/characterization/decision.txt" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
decision_path = Path(sys.argv[2])

rows = list(csv.DictReader(summary_path.open(), delimiter="\t"))
assert len(rows) == 2, rows
exact, single = rows
assert exact["runner_exact_scoreinfo_gpu_pruned_output"] == "1", exact
assert exact["runner_gasal2_single_pass_topn"] == "0", exact
assert int(exact["legacy_score_gpu_requests"]) > 0, exact
assert int(exact["exact_scoreinfo_gpu_batches"]) > 0, exact
assert single["runner_gasal2_single_pass_topn"] == "1", single
assert single["runner_exact_scoreinfo_gpu_pruned_output"] == "0", single
assert int(single["single_pass_topn_batches"]) > 0, single
assert int(single["single_pass_topn_tasks"]) > 0, single
assert int(single["legacy_score_gpu_requests"]) == 0, single
assert int(single["exact_scoreinfo_gpu_batches"]) == 0, single
assert single["top5_score_equal"] in {"true", "false"}, single
assert single["top5_stability_equal"] in {"true", "false"}, single
assert single["top5_nt_score_equal"] in {"true", "false"}, single
assert decision_path.read_text(encoding="utf-8").strip(), decision_path
PY

echo "ok"
