#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_worker_readiness_matrix"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_multicontig.fa" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

lines = src.read_text().splitlines()
header = lines[0]
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
if not header.startswith(">hg19|chr11|"):
    raise SystemExit(f"unexpected sample header: {header}")

range_text = header.rsplit("|", 1)[1]
start_text, end_text = range_text.split("-", 1)
start = int(start_text)

third = len(sequence) // 3
parts = [sequence[:third], sequence[third : 2 * third], sequence[2 * third :]]
records = []
offset = start
for idx, part in enumerate(parts, start=1):
    part_start = offset
    part_end = offset + len(part) - 1
    records.append(f">hg19|chr11_part{idx}|{part_start}-{part_end}\n{part}\n")
    offset = part_end + 1
dst.write_text("".join(records))
PY

python3 "$ROOT/scripts/benchmark_fasim_sharded_worker_workload_matrix.py" \
  --workload "readiness_fixture:$WORK/inputs/testDNA_multicontig.fa:$WORK/inputs/H19.fa:1" \
  --fasim-bin "$BIN" \
  --work-dir "$WORK/run" \
  --output-mode lite \
  --workers 1,2 \
  --gpu-ids 0,1 \
  --manifest \
  --auto-cpu-core-ranges \
  --cpu-pool 0-3 \
  --cpu-cores-per-worker 2 \
  >"$WORK/logs/readiness.stdout.log" \
  2>"$WORK/logs/readiness.stderr.log"

python3 - "$WORK/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
workload = report["workloads"][0]
assert workload["all_digest_match"] is True, workload
assert workload["readiness_mode"] is True, workload

runs = {run["worker_count"]: run for run in workload["runs"]}
assert sorted(runs) == [1, 2], runs
for worker_count, run in runs.items():
    assert run["run_manifest_path"], run
    assert Path(run["run_manifest_path"]).exists(), run
    assert run["resumed_shards"] == [], run
    assert run["failed_shards"] == [], run
    assert run["run_status"] == "completed", run
    assert run["taskset_enabled"] is True, run
    assert run["auto_cpu_core_ranges"] is True, run
    assert run["cpu_pool"] == "0-3", run
    assert run["cpu_cores_per_worker"] == 2, run
assert runs[1]["cpu_core_ranges"] == ["0-1"], runs[1]
assert runs[2]["cpu_core_ranges"] == ["0-1", "2-3"], runs[2]
PY

echo "ok"
