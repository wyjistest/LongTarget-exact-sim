#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_worker_scaling"
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

third = len(sequence) // 3
parts = [
    ("chr11_a", sequence[:third]),
    ("chr11_b", sequence[third : 2 * third]),
    ("chr11_c", sequence[2 * third :]),
]

cursor = start
out = []
for name, part in parts:
    part_end = cursor + len(part) - 1
    out.append(f">hg19|{name}|{cursor}-{part_end}\n{part}\n")
    cursor = part_end + 1
if cursor - 1 != end:
    raise SystemExit("partitioned sample does not match header range")

dst.write_text("".join(out))
PY

python3 "$ROOT/scripts/benchmark_fasim_sharded_worker_scaling.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
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
assert report["mode"] == "fasim_sharded_worker_scaling", report
assert report["worker_counts"] == [1, 2, 4], report
assert report["baseline"]["single_vs_sharded_digest_match"] is True, report
assert len(report["runs"]) == 3, report

baseline_digest = report["baseline"]["merged_digest"]
for run in report["runs"]:
    assert run["worker_count"] in {1, 2, 4}, run
    assert run["single_vs_sharded_digest_match"] is True, run
    assert run["merged_digest"] == baseline_digest, run
    assert run["speedup_vs_single"] > 0, run
    assert run["speedup_vs_1_worker"] > 0, run
    assert run["wall_seconds"] > 0, run
    assert run["shard_count"] == 3, run
    assert len(run["per_worker"]) == run["worker_count"], run
    assert sum(len(w["shard_ids"]) for w in run["per_worker"]) == 3, run

summary = report["summary"]
assert summary["all_digest_match"] is True, summary
assert summary["best_worker_count"] in {1, 2, 4}, summary
assert summary["best_wall_seconds"] > 0, summary
PY

echo "ok"
