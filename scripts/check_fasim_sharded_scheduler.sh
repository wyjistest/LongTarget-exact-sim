#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_scheduler"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/scheduled"

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

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/baseline/run" \
  --output-mode lite \
  --validate-single \
  >"$WORK/baseline/stdout.log" \
  2>"$WORK/baseline/stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/scheduled/run" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/scheduled/stdout.log" \
  2>"$WORK/scheduled/stderr.log"

python3 - "$WORK/baseline/run/report.json" "$WORK/scheduled/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text())
scheduled = json.loads(Path(sys.argv[2]).read_text())

assert baseline["single_vs_sharded_digest_match"] is True, baseline
assert scheduled["single_vs_sharded_digest_match"] is True, scheduled
assert scheduled["worker_count"] == 2, scheduled
assert scheduled["gpu_ids"] == ["0", "1"], scheduled
assert len(scheduled["per_worker"]) == 2, scheduled
assert sorted(w["gpu_id"] for w in scheduled["per_worker"]) == ["0", "1"], scheduled
assert baseline["merged_digest"] == scheduled["merged_digest"], scheduled
assert baseline["merged_records"] == scheduled["merged_records"], scheduled
assert baseline["duplicate_records_removed"] == scheduled["duplicate_records_removed"], scheduled
assert sorted(baseline["shard_ids"]) == sorted(scheduled["shard_ids"]), scheduled
assert sum(len(w["shard_ids"]) for w in scheduled["per_worker"]) == scheduled["shard_count"], scheduled
PY

echo "ok"
