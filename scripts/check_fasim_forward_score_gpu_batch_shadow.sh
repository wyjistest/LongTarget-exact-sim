#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_forward_score_gpu_batch_shadow"

rm -rf "$WORK"
mkdir -p "$WORK/off" "$WORK/batch"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
FASIM_ALIGN_PROFILE_CACHE=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/off" \
  >"$WORK/off/stdout.log" \
  2>"$WORK/off/stderr.log"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/batch" \
  >"$WORK/batch/stdout.log" \
  2>"$WORK/batch/stderr.log"

OUT_OFF="$WORK/off/hg19-H19-testDNA-TFOsorted.lite"
OUT_BATCH="$WORK/batch/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_OFF"
test -s "$OUT_BATCH"

python3 - "$OUT_OFF" "$OUT_BATCH" "$WORK/off/stderr.log" "$WORK/batch/stderr.log" <<'PY'
import re
import sys
from pathlib import Path


def canonical(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    assert lines, path
    header = lines[0]
    rows = sorted(line for line in lines[1:] if line.strip())
    return header, rows


def telemetry(path):
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.match(r"^benchmark\.(fasim_[A-Za-z0-9_]+)=(.*)$", line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


assert canonical(sys.argv[1]) == canonical(sys.argv[2])

off = telemetry(sys.argv[3])
batch = telemetry(sys.argv[4])

required = [
    "fasim_forward_score_batch_shadow_enabled",
    "fasim_forward_score_batch_requests",
    "fasim_forward_score_batch_cells",
    "fasim_forward_score_batch_pack_seconds",
    "fasim_forward_score_batch_h2d_seconds",
    "fasim_forward_score_batch_kernel_seconds",
    "fasim_forward_score_batch_d2h_seconds",
    "fasim_forward_score_batch_unpack_seconds",
    "fasim_forward_score_batch_total_seconds",
    "fasim_forward_score_batch_cpu_reference_seconds",
    "fasim_forward_score_batch_score_mismatches",
    "fasim_forward_score_batch_endpoint_mismatches",
    "fasim_forward_score_batch_unsupported_requests",
]
for name, values in [("off", off), ("batch", batch)]:
    missing = [key for key in required if key not in values]
    assert not missing, (name, missing)

assert off["fasim_forward_score_batch_shadow_enabled"] == "0", off
assert int(off["fasim_forward_score_batch_requests"]) == 0, off
assert int(off["fasim_forward_score_batch_cells"]) == 0, off
assert float(off["fasim_forward_score_batch_total_seconds"]) == 0.0, off

assert batch["fasim_forward_score_batch_shadow_enabled"] == "1", batch
requests = int(batch["fasim_forward_score_batch_requests"])
cells = int(batch["fasim_forward_score_batch_cells"])
unsupported = int(batch["fasim_forward_score_batch_unsupported_requests"])
assert requests > 0, batch
assert cells > 0, batch
assert unsupported >= 0, batch
assert unsupported <= requests, batch
assert float(batch["fasim_forward_score_batch_cpu_reference_seconds"]) > 0.0, batch
assert float(batch["fasim_forward_score_batch_total_seconds"]) >= 0.0, batch
assert int(batch["fasim_forward_score_batch_score_mismatches"]) == 0, batch
assert int(batch["fasim_forward_score_batch_endpoint_mismatches"]) >= 0, batch
PY

echo "ok"
