#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_cpu_affinity"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs" "$WORK/errors"

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

mid = len(sequence) // 2
left = sequence[:mid]
right = sequence[mid:]
left_end = start + len(left) - 1
right_start = left_end + 1
right_end = right_start + len(right) - 1

dst.write_text(
    f">hg19|chr11_left|{start}-{left_end}\n{left}\n"
    f">hg19|chr11_right|{right_start}-{right_end}\n{right}\n"
)
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/default/run" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  >"$WORK/logs/default.stdout.log" \
  2>"$WORK/logs/default.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/auto/run" \
  --manifest "$WORK/auto/run_manifest.json" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-3 \
  --cpu-cores-per-worker 2 \
  >"$WORK/logs/auto.stdout.log" \
  2>"$WORK/logs/auto.stderr.log"

python3 - "$WORK/default/run/report.json" "$WORK/auto/run/report.json" "$WORK/auto/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

default = json.loads(Path(sys.argv[1]).read_text())
auto = json.loads(Path(sys.argv[2]).read_text())
manifest = json.loads(Path(sys.argv[3]).read_text())

assert default["single_vs_sharded_digest_match"] is True, default
assert auto["single_vs_sharded_digest_match"] is True, auto
assert default["cpu_core_ranges"] == [], default
assert default["auto_cpu_core_ranges"] is False, default
assert default["taskset_enabled"] is False, default
assert auto["cpu_pool"] == "0-3", auto
assert auto["cpu_cores_per_worker"] == 2, auto
assert auto["auto_cpu_core_ranges"] is True, auto
assert auto["cpu_core_ranges"] == ["0-1", "2-3"], auto
assert auto["taskset_enabled"] is True, auto
assert [w["cpu_core_range"] for w in auto["per_worker"]] == ["0-1", "2-3"], auto
assert auto["merged_digest"] == default["merged_digest"], auto
assert manifest["cpu_pool"] == "0-3", manifest
assert manifest["cpu_cores_per_worker"] == 2, manifest
assert manifest["auto_cpu_core_ranges"] is True, manifest
assert manifest["cpu_core_ranges"] == ["0-1", "2-3"], manifest
assert manifest["taskset_enabled"] is True, manifest
PY

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/conflict/run" \
  --output-mode lite \
  --workers 2 \
  --cpu-core-ranges 0-1,2-3 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-3 \
  --cpu-cores-per-worker 2 \
  >"$WORK/errors/conflict.stdout.log" \
  2>"$WORK/errors/conflict.stderr.log"; then
  echo "expected explicit --cpu-core-ranges plus --auto-cpu-core-ranges to fail" >&2
  exit 1
fi
grep -q -- "--cpu-core-ranges and --auto-cpu-core-ranges cannot be used together" "$WORK/errors/conflict.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/missing_pool/run" \
  --output-mode lite \
  --workers 2 \
  --auto-cpu-core-ranges \
  --cpu-cores-per-worker 2 \
  >"$WORK/errors/missing_pool.stdout.log" \
  2>"$WORK/errors/missing_pool.stderr.log"; then
  echo "expected missing --cpu-pool to fail" >&2
  exit 1
fi
grep -q -- "--auto-cpu-core-ranges requires --cpu-pool" "$WORK/errors/missing_pool.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/insufficient/run" \
  --output-mode lite \
  --workers 2 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-2 \
  --cpu-cores-per-worker 2 \
  >"$WORK/errors/insufficient.stdout.log" \
  2>"$WORK/errors/insufficient.stderr.log"; then
  echo "expected insufficient CPU pool to fail" >&2
  exit 1
fi
grep -q -- "insufficient --cpu-pool cores" "$WORK/errors/insufficient.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/explicit/run" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --cpu-core-ranges 0-1,2-3 \
  >"$WORK/logs/explicit.stdout.log" \
  2>"$WORK/logs/explicit.stderr.log"

python3 - "$WORK/explicit/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
assert report["cpu_core_ranges"] == ["0-1", "2-3"], report
assert report["auto_cpu_core_ranges"] is False, report
assert report["taskset_enabled"] is True, report
assert [w["cpu_core_range"] for w in report["per_worker"]] == ["0-1", "2-3"], report
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/resume_changed/run" \
  --manifest "$WORK/resume_changed/run_manifest.json" \
  --output-mode lite \
  --workers 2 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-3 \
  --cpu-cores-per-worker 2 \
  >"$WORK/logs/resume_fresh.stdout.log" \
  2>"$WORK/logs/resume_fresh.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/resume_changed/run" \
  --manifest "$WORK/resume_changed/run_manifest.json" \
  --output-mode lite \
  --workers 2 \
  --resume \
  --auto-cpu-core-ranges \
  --cpu-pool 4-7 \
  --cpu-cores-per-worker 2 \
  >"$WORK/logs/resume_changed.stdout.log" \
  2>"$WORK/logs/resume_changed.stderr.log"

python3 - "$WORK/resume_changed/run/report.json" "$WORK/resume_changed/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())
assert report["resumed_shards"] == [], report
assert report["cpu_core_ranges"] == ["4-5", "6-7"], report
assert manifest["cpu_core_ranges"] == ["4-5", "6-7"], manifest
assert all(shard["status"] == "completed" for shard in manifest["per_shard"]), manifest
PY

echo "ok"
