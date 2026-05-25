#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_sharded_runner_telemetry"

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"
cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_multicontig.fa" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = src.read_text(encoding="utf-8").splitlines()
header = lines[0]
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
mid = len(sequence) // 2
dst.write_text(
    f"{header.replace('chr11', 'chr11_left')}\n{sequence[:mid]}\n"
    f"{header.replace('chr11', 'chr11_right')}\n{sequence[mid:]}\n",
    encoding="utf-8",
)
PY

env -u FASIM_CUDA_DEVICES \
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/run" \
  --manifest "$WORK/run/run_manifest.json" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --gpu-ids 0,1 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=2 \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/run/report.json" "$WORK/run/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
required = {
    "fasim_prealign_cuda_requested",
    "fasim_prealign_cuda_active",
    "fasim_prealign_cuda_tasks",
    "fasim_prealign_cuda_batches",
    "fasim_prealign_cuda_kernel_seconds",
    "fasim_prealign_cuda_total_seconds",
    "fasim_extend_threads",
    "fasim_extend_seconds",
    "fasim_output_seconds",
}

assert report["single_vs_sharded_digest_match"] is True, report
assert report["sharded_telemetry"]["fasim_prealign_cuda_requested"] == 1, report["sharded_telemetry"]
assert report["sharded_telemetry"]["fasim_prealign_cuda_tasks"] > 0, report["sharded_telemetry"]
assert report["single_run"]["telemetry"]["fasim_prealign_cuda_requested"] == 1, report["single_run"]

for shard in report["per_shard"]:
    telemetry = shard["run"]["telemetry"]
    assert required.issubset(telemetry), telemetry
    assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry

for worker in report["per_worker"]:
    telemetry = worker["telemetry"]
    assert required.issubset(telemetry), telemetry
    assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry

for entry in manifest["per_shard"]:
    telemetry = entry["telemetry"]
    assert required.issubset(telemetry), telemetry
PY

echo "ok"
