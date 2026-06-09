#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_exact_scoreinfo_gpu_pruned_output"}"

rm -rf "$WORK"
mkdir -p "$WORK"

WORK="$WORK/characterization" \
bash "$ROOT/scripts/characterize_fasim_exact_scoreinfo_gpu_pruned_output.sh" \
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
baseline, pruned = rows
assert baseline["runner_exact_scoreinfo_gpu_pruned_output"] == "0", baseline
assert pruned["runner_exact_scoreinfo_gpu_pruned_output"] == "1", pruned
assert pruned["top5_all_equal"] == "true", pruned
assert int(pruned["exact_scoreinfo_gpu_overflow_batches"]) == 0, pruned
assert int(pruned["exact_scoreinfo_gpu_fallback_batches"]) == 0, pruned
assert int(pruned["exact_scoreinfo_gpu_pruned_output_batches"]) > 0, pruned
assert int(pruned["exact_scoreinfo_gpu_pruned_output_input_groups"]) > 0, pruned
assert int(pruned["exact_scoreinfo_gpu_pruned_output_kept_groups"]) > 0, pruned
assert int(pruned["exact_scoreinfo_gpu_pruned_output_pruned_groups"]) > 0, pruned
assert decision_path.read_text(encoding="utf-8").strip(), decision_path
PY

echo "ok"
