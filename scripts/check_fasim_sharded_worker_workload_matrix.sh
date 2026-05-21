#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_worker_workload_matrix"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"

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
end = int(end_text)
if start + len(sequence) - 1 != end:
    raise SystemExit("sample length does not match header range")

mid = len(sequence) // 2
left = sequence[:mid]
right = sequence[mid:]
left_start = start
left_end = start + len(left) - 1
right_start = left_end + 1
right_end = end

dst.write_text(
    f">hg19|chr11_left|{left_start}-{left_end}\n"
    f"{left}\n"
    f">hg19|chr11_right|{right_start}-{right_end}\n"
    f"{right}\n"
)
PY

python3 "$ROOT/scripts/benchmark_fasim_sharded_worker_workload_matrix.py" \
  --workload "fixture_two_contig:$WORK/inputs/testDNA_multicontig.fa:$WORK/inputs/H19.fa:1" \
  --fasim-bin "$BIN" \
  --work-dir "$WORK/run" \
  --output-mode lite \
  --workers 1,2,4 \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())

assert report["schema_version"] == 1, report
assert report["mode"] == "fasim_sharded_worker_workload_matrix", report
assert report["worker_counts"] == [1, 2, 4], report
assert len(report["workloads"]) == 1, report
assert report["summary"]["workloads"] == 1, report
assert report["summary"]["all_digest_match"] is True, report

workload = report["workloads"][0]
assert workload["name"] == "fixture_two_contig", workload
assert workload["shard_count"] == 2, workload
assert workload["all_digest_match"] is True, workload
assert len(workload["runs"]) == 3, workload
assert workload["baseline"]["single_vs_sharded_digest_match"] is True, workload

baseline_digest = workload["baseline"]["merged_digest"]
for run in workload["runs"]:
    assert run["worker_count"] in {1, 2, 4}, run
    assert run["single_vs_sharded_digest_match"] is True, run
    assert run["merged_digest"] == baseline_digest, run
    assert run["speedup_vs_single_worker"] > 0, run
    assert run["speedup_vs_single_whole_run"] > 0, run
    assert run["wall_seconds"] > 0, run
    assert len(run["per_worker_seconds"]) == run["worker_count"], run
    assert len(run["per_worker_records"]) == run["worker_count"], run
    assert len(run["per_shard_seconds"]) == 2, run
    assert len(run["per_shard_records"]) == 2, run
    assert len(run["per_shard_digest"]) == 2, run
PY

echo "ok"
