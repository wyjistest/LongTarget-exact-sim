#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/corpus_manifest.tsv" <<'EOF'
tile_key	tile_filename	task_key	rule	strand	target_length	rerun_bp	task_output_row_count	rerun_total_seconds
tileA|1	tileA.tsv	taskA	1	ParaPlus	3000	800	2	0.50
tileA|1	tileA.tsv	taskB	1	ParaPlus	3200	900	4	0.60
tileB|1	tileB.tsv	taskC	1	ParaPlus	3400	1000	8	0.70
tileB|1	tileB.tsv	taskD	1	ParaPlus	3600	1100	16	0.80
tileC|1	tileC.tsv	taskE	2	AntiPlus	900	200	0	0.20
EOF

python3 "$ROOT/scripts/analyze_two_stage_task_rerun_corpus_shapes.py" \
  --corpus-manifest "$WORK/corpus_manifest.tsv" \
  --output-dir "$WORK/out" >/dev/null

python3 - "$WORK/out/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
aggregate = summary["aggregate"]
assert aggregate["task_count"] == 5
assert math.isclose(aggregate["rerun_seconds_total"], 2.8, rel_tol=1e-9)
assert aggregate["gpu_batching_candidate"] is True

bp_bins = {item["label"]: item for item in summary["rerun_bp_bins"]}
assert bp_bins["513-1024"]["task_count"] == 3
assert bp_bins[">2048"]["task_count"] == 0

target_bins = {item["label"]: item for item in summary["target_length_bins"]}
assert target_bins["2049-4096"]["task_count"] == 4

output_bins = {item["label"]: item for item in summary["output_row_bins"]}
assert output_bins["1-4"]["task_count"] == 2
assert output_bins[">16"]["task_count"] == 0

rule_strand = {f"{item['rule']}|{item['strand']}": item for item in summary["rule_strand_buckets"]}
assert rule_strand["1|ParaPlus"]["task_count"] == 4

top_seconds = summary["top_rerun_seconds_tasks"][0]
assert top_seconds["task_key"] == "taskD"
assert top_seconds["rerun_total_seconds"] == 0.8
PY

echo "ok"
