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
tileB|1	tileB.tsv	taskD	3	ParaMinus	5000	1300	20	1.40
tileC|1	tileC.tsv	taskE	2	AntiPlus	900	200	0	0.20
EOF

python3 "$ROOT/scripts/analyze_two_stage_task_rerun_corpus_shapes.py" \
  --corpus-manifest "$WORK/corpus_manifest.tsv" \
  --output-dir "$WORK/shape" >/dev/null

cat >"$WORK/fake_replay_bin.py" <<'PY'
#!/usr/bin/env python3
import csv
import sys
import time
from pathlib import Path


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


args = sys.argv[1:]
manifest = None
output_dir = None
threads = 1
task_keys = set()
i = 0
while i < len(args):
    arg = args[i]
    if arg == "--corpus-manifest":
        manifest = Path(args[i + 1])
        i += 2
        continue
    if arg == "--output-dir":
        output_dir = Path(args[i + 1])
        i += 2
        continue
    if arg == "--threads":
        threads = int(args[i + 1])
        i += 2
        continue
    if arg == "--task-key":
        task_keys.add(args[i + 1])
        i += 2
        continue
    if arg == "--task-list-tsv":
        with Path(args[i + 1]).open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        for row in rows:
            task_keys.add(row["task_key"])
        i += 2
        continue
    if arg == "--tile":
        i += 2
        continue
    raise SystemExit(f"unknown arg: {arg}")

if manifest is None or output_dir is None:
    raise SystemExit("manifest/output-dir required")

rows = load_rows(manifest)
selected = [row for row in rows if row["task_key"] in task_keys] if task_keys else rows
output_dir.mkdir(parents=True, exist_ok=True)

grouped = {}
for row in selected:
    grouped.setdefault(row["tile_filename"], []).append(row)

for tile_name, tile_rows in grouped.items():
    with (output_dir / tile_name).open("w", encoding="utf-8") as handle:
        handle.write("task_key\tselected\teffective\tChr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\tMeanStability\n")
        for index, row in enumerate(tile_rows, 1):
            handle.write(
                f"{row['task_key']}\t1\t1\tchrSynthetic\t{index}\t{index + 10}\t{row['strand']}\t{row['rule']}\t1\t10\t1\t10\tR\t100\t{row['rerun_bp']}\t90\t2.0\n"
            )

time.sleep(0.01 + 0.02 * len(selected) / max(threads, 1))
PY
chmod +x "$WORK/fake_replay_bin.py"

python3 "$ROOT/scripts/benchmark_two_stage_task_rerun_cpu_buckets.py" \
  --corpus-manifest "$WORK/corpus_manifest.tsv" \
  --shape-summary "$WORK/shape/summary.json" \
  --replay-bin "$WORK/fake_replay_bin.py" \
  --output-dir "$WORK/out" \
  --thread-values 1,2 >/dev/null

python3 - "$WORK/out/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert summary["recommended_cpu_bucket_count"] >= 1
assert "continue_cpu_executor_prototype" in summary
assert summary["bucket_results"]

bucket = summary["bucket_results"][0]
assert bucket["isolated_serial_wall_seconds"] >= 0.0
assert bucket["bucket_serial_wall_seconds"] >= 0.0
assert bucket["best_parallel"]["bucket_parallel_wall_seconds"] >= 0.0
assert bucket["best_parallel"]["thread_count"] in {1, 2}

run_kinds = {item["run_kind"] for item in bucket["runs"]}
assert run_kinds == {"isolated_serial", "bucket_serial", "bucket_parallel"}
PY

echo "ok"
