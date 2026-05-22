#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WORK="$ROOT/.tmp/check_fasim_shard_balance"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs" "$WORK/errors"

cat >"$WORK/inputs/synthetic_multicontig.fa" <<'FASTA'
>test|contig900|1-900
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>test|contig500|1-500
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
>test|contig400|1-400
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
>test|contig200|1-200
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
>test|contig100|1-100
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
FASTA

python3 "$ROOT/scripts/analyze_fasim_shard_balance.py" \
  --target "$WORK/inputs/synthetic_multicontig.fa" \
  --workload-name synthetic_balance \
  --workers 1,2,4,6,8 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-15 \
  --cpu-cores-per-worker 2 \
  --output "$WORK/report.json" \
  >"$WORK/logs/analyze.stdout.log" \
  2>"$WORK/logs/analyze.stderr.log"

python3 - "$WORK/report.json" <<'PY'
import json
import math
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
assert report["schema_version"] == 1, report
assert report["mode"] == "shard_balance_plan", report
assert report["fasim_execution"] is False, report
assert report["workload_name"] == "synthetic_balance", report
assert report["contig_count"] == 5, report
assert report["shard_count"] == 5, report
assert report["cost_metric"] == "estimated_length", report
assert report["estimated_cells_available"] is False, report
assert report["assignment_policy"] == "largest-first estimated_cells_or_length", report
assert report["worker_counts"] == [1, 2, 4, 6, 8], report

runs = {run["worker_count"]: run for run in report["runs"]}
assert sorted(runs) == [1, 2, 4, 6, 8], runs
assert runs[1]["cpu_core_ranges"] == ["0-1"], runs[1]
assert runs[8]["cpu_core_ranges"] == [
    "0-1",
    "2-3",
    "4-5",
    "6-7",
    "8-9",
    "10-11",
    "12-13",
    "14-15",
], runs[8]
assert runs[6]["workers_per_gpu"] == 3, runs[6]
assert runs[6]["effective_workers_per_gpu"] == 3.0, runs[6]
assert runs[6]["gpu_sharing_mode"] == "shared", runs[6]

two = runs[2]
assigned = {shard["target_name"]: shard["assigned_worker"] for shard in two["per_shard"]}
assert assigned == {
    "contig900": 0,
    "contig500": 1,
    "contig400": 1,
    "contig200": 0,
    "contig100": 1,
}, assigned
worker_work = {worker["worker_id"]: worker["estimated_work"] for worker in two["per_worker"]}
assert worker_work == {0: 1100, 1: 1000}, worker_work
assert two["predicted_makespan_work"] == 1100, two
assert two["straggler_worker"] == 0, two
assert [s["target_name"] for s in two["straggler_shards"]] == ["contig900", "contig200"], two
assert math.isclose(two["largest_shard_fraction"], 900 / 2100, rel_tol=1e-9), two
assert math.isclose(two["load_imbalance_ratio"], 1100 / 1050, rel_tol=1e-9), two
assert math.isclose(two["idle_fraction_estimate"], 1 - 2100 / 2200, rel_tol=1e-9), two

eight = runs[8]
assert eight["empty_worker_count"] == 3, eight
assert eight["load_imbalance_ratio"] > 3.0, eight
assert eight["idle_fraction_estimate"] > 0.7, eight
PY

if python3 "$ROOT/scripts/analyze_fasim_shard_balance.py" \
  --target "$WORK/inputs/synthetic_multicontig.fa" \
  --workers 8 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-7 \
  --cpu-cores-per-worker 2 \
  --output "$WORK/errors/insufficient.json" \
  >"$WORK/errors/insufficient.stdout.log" \
  2>"$WORK/errors/insufficient.stderr.log"; then
  echo "expected insufficient --cpu-pool to fail" >&2
  exit 1
fi
grep -q -- "insufficient --cpu-pool cores" "$WORK/errors/insufficient.stderr.log"

echo "ok"
