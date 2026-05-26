#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_forward_score_gpu_shadow"

rm -rf "$WORK"
mkdir -p "$WORK/off" "$WORK/shadow"

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
FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/shadow" \
  >"$WORK/shadow/stdout.log" \
  2>"$WORK/shadow/stderr.log"

OUT_OFF="$WORK/off/hg19-H19-testDNA-TFOsorted.lite"
OUT_SHADOW="$WORK/shadow/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_OFF"
test -s "$OUT_SHADOW"

python3 - "$OUT_OFF" "$OUT_SHADOW" "$WORK/off/stderr.log" "$WORK/shadow/stderr.log" <<'PY'
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
shadow = telemetry(sys.argv[4])

required = [
    "fasim_align_forward_score_gpu_shadow_enabled",
    "fasim_align_forward_score_gpu_requests",
    "fasim_align_forward_score_gpu_cells",
    "fasim_align_forward_score_gpu_cpu_seconds",
    "fasim_align_forward_score_gpu_pack_seconds",
    "fasim_align_forward_score_gpu_h2d_seconds",
    "fasim_align_forward_score_gpu_kernel_seconds",
    "fasim_align_forward_score_gpu_d2h_seconds",
    "fasim_align_forward_score_gpu_unpack_seconds",
    "fasim_align_forward_score_gpu_total_seconds",
    "fasim_align_forward_score_gpu_score_mismatches",
    "fasim_align_forward_score_gpu_endpoint_mismatches",
    "fasim_align_forward_score_gpu_unsupported_requests",
]
for name, values in [("off", off), ("shadow", shadow)]:
    missing = [key for key in required if key not in values]
    assert not missing, (name, missing)

assert off["fasim_align_forward_score_gpu_shadow_enabled"] == "0", off
assert int(off["fasim_align_forward_score_gpu_requests"]) == 0, off
assert int(off["fasim_align_forward_score_gpu_cells"]) == 0, off
assert float(off["fasim_align_forward_score_gpu_total_seconds"]) == 0.0, off

assert shadow["fasim_align_forward_score_gpu_shadow_enabled"] == "1", shadow
requests = int(shadow["fasim_align_forward_score_gpu_requests"])
cells = int(shadow["fasim_align_forward_score_gpu_cells"])
unsupported = int(shadow["fasim_align_forward_score_gpu_unsupported_requests"])
assert requests > 0, shadow
assert cells > 0, shadow
assert unsupported >= 0, shadow
assert unsupported <= requests, shadow
assert float(shadow["fasim_align_forward_score_gpu_cpu_seconds"]) > 0.0, shadow
assert float(shadow["fasim_align_forward_score_gpu_total_seconds"]) >= 0.0, shadow
assert int(shadow["fasim_align_forward_score_gpu_score_mismatches"]) == 0, shadow
assert int(shadow["fasim_align_forward_score_gpu_endpoint_mismatches"]) >= 0, shadow
PY

echo "ok"
