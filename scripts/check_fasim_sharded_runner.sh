#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_runner"
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

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/run" \
  --output-mode lite \
  --validate-single \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
report = json.loads(report_path.read_text())

assert report["shard_count"] == 2, report
assert report["single_vs_sharded_digest_match"] is True, report
assert report["single_records"] == report["merged_records"], report
assert report["sharded_records"] >= report["merged_records"], report
assert len(report["per_shard"]) == 2, report
for shard in report["per_shard"]:
    assert shard["target_name"] in {"chr11_left", "chr11_right"}, shard
    assert len(shard["digest"]) == 64, shard

merged = Path(report["merged_output"])
assert merged.exists() and merged.stat().st_size > 0, report
assert len(report["merged_digest"]) == 64, report
assert len(report["single_digest"]) == 64, report
PY

echo "ok"
