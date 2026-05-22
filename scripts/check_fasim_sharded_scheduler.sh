#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_scheduler"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/scheduled" "$WORK/derived" "$WORK/errors"

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

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/derived/run" \
  --output-mode lite \
  --validate-single \
  --workers-per-gpu 1 \
  --gpu-ids 0,1 \
  >"$WORK/derived/stdout.log" \
  2>"$WORK/derived/stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/both/run" \
  --output-mode lite \
  --workers 2 \
  --workers-per-gpu 1 \
  --gpu-ids 0,1 \
  >"$WORK/errors/both.stdout.log" \
  2>"$WORK/errors/both.stderr.log"; then
  echo "expected --workers plus --workers-per-gpu to fail" >&2
  exit 1
fi
grep -q -- "--workers and --workers-per-gpu cannot be used together" "$WORK/errors/both.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/no_gpu_ids/run" \
  --output-mode lite \
  --workers-per-gpu 1 \
  >"$WORK/errors/no_gpu_ids.stdout.log" \
  2>"$WORK/errors/no_gpu_ids.stderr.log"; then
  echo "expected --workers-per-gpu without --gpu-ids to fail" >&2
  exit 1
fi
grep -q -- "--workers-per-gpu requires --gpu-ids" "$WORK/errors/no_gpu_ids.stderr.log"

python3 - "$WORK/baseline/run/report.json" "$WORK/scheduled/run/report.json" "$WORK/derived/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text())
scheduled = json.loads(Path(sys.argv[2]).read_text())
derived = json.loads(Path(sys.argv[3]).read_text())

assert baseline["single_vs_sharded_digest_match"] is True, baseline
assert scheduled["single_vs_sharded_digest_match"] is True, scheduled
assert derived["single_vs_sharded_digest_match"] is True, derived
assert scheduled["worker_count"] == 2, scheduled
assert scheduled["gpu_ids"] == ["0", "1"], scheduled
assert scheduled["workers_per_gpu"] is None, scheduled
assert scheduled["workers_derived_from_gpu_ids"] is False, scheduled
assert len(scheduled["per_worker"]) == 2, scheduled
assert sorted(w["gpu_id"] for w in scheduled["per_worker"]) == ["0", "1"], scheduled
assert derived["worker_count"] == 2, derived
assert derived["workers_per_gpu"] == 1, derived
assert derived["workers_derived_from_gpu_ids"] is True, derived
assert derived["gpu_sharing_mode"] == "exclusive", derived
assert len(derived["per_worker"]) == 2, derived
assert sorted(w["gpu_id"] for w in derived["per_worker"]) == ["0", "1"], derived
assert baseline["merged_digest"] == scheduled["merged_digest"], scheduled
assert scheduled["merged_digest"] == derived["merged_digest"], derived
assert baseline["merged_records"] == scheduled["merged_records"], scheduled
assert scheduled["merged_records"] == derived["merged_records"], derived
assert baseline["duplicate_records_removed"] == scheduled["duplicate_records_removed"], scheduled
assert scheduled["duplicate_records_removed"] == derived["duplicate_records_removed"], derived
assert sorted(baseline["shard_ids"]) == sorted(scheduled["shard_ids"]), scheduled
assert sorted(scheduled["shard_ids"]) == sorted(derived["shard_ids"]), derived
assert sum(len(w["shard_ids"]) for w in scheduled["per_worker"]) == scheduled["shard_count"], scheduled
assert sum(len(w["shard_ids"]) for w in derived["per_worker"]) == derived["shard_count"], derived
PY

echo "ok"
