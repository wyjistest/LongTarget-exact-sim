#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_score_bridge_shadow"

rm -rf "$WORK"
mkdir -p "$WORK/off" "$WORK/bridge"

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
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/bridge" \
  >"$WORK/bridge/stdout.log" \
  2>"$WORK/bridge/stderr.log"

OUT_OFF="$WORK/off/hg19-H19-testDNA-TFOsorted.lite"
OUT_BRIDGE="$WORK/bridge/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_OFF"
test -s "$OUT_BRIDGE"

python3 - "$OUT_OFF" "$OUT_BRIDGE" "$WORK/off/stderr.log" "$WORK/bridge/stderr.log" <<'PY'
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
bridge = telemetry(sys.argv[4])

required = [
    "fasim_score_bridge_shadow_enabled",
    "fasim_score_bridge_requests",
    "fasim_score_bridge_cells",
    "fasim_score_bridge_groups",
    "fasim_score_bridge_descriptor_count",
    "fasim_score_bridge_descriptor_bytes",
    "fasim_score_bridge_query_buffer_bytes",
    "fasim_score_bridge_target_buffer_bytes",
    "fasim_score_bridge_pack_seconds",
    "fasim_score_bridge_h2d_seconds",
    "fasim_score_bridge_kernel_seconds",
    "fasim_score_bridge_d2h_seconds",
    "fasim_score_bridge_unpack_seconds",
    "fasim_score_bridge_total_seconds",
    "fasim_score_bridge_cpu_reference_seconds",
    "fasim_score_bridge_score_mismatches",
    "fasim_score_bridge_endpoint_mismatches",
    "fasim_score_bridge_unsupported_requests",
]
for name, values in [("off", off), ("bridge", bridge)]:
    missing = [key for key in required if key not in values]
    assert not missing, (name, missing)

assert off["fasim_score_bridge_shadow_enabled"] == "0", off
assert int(off["fasim_score_bridge_requests"]) == 0, off
assert int(off["fasim_score_bridge_cells"]) == 0, off
assert int(off["fasim_score_bridge_descriptor_count"]) == 0, off
assert int(off["fasim_score_bridge_query_buffer_bytes"]) == 0, off
assert int(off["fasim_score_bridge_target_buffer_bytes"]) == 0, off
assert float(off["fasim_score_bridge_total_seconds"]) == 0.0, off

assert bridge["fasim_score_bridge_shadow_enabled"] == "1", bridge
requests = int(bridge["fasim_score_bridge_requests"])
cells = int(bridge["fasim_score_bridge_cells"])
groups = int(bridge["fasim_score_bridge_groups"])
descriptor_count = int(bridge["fasim_score_bridge_descriptor_count"])
descriptor_bytes = int(bridge["fasim_score_bridge_descriptor_bytes"])
query_bytes = int(bridge["fasim_score_bridge_query_buffer_bytes"])
target_bytes = int(bridge["fasim_score_bridge_target_buffer_bytes"])
unsupported = int(bridge["fasim_score_bridge_unsupported_requests"])
assert requests > 0, bridge
assert cells > 0, bridge
assert groups > 0, bridge
assert descriptor_count == requests, bridge
assert descriptor_bytes >= descriptor_count * 32, bridge
assert query_bytes > 0, bridge
assert target_bytes > 0, bridge
assert target_bytes < cells, bridge
assert unsupported >= 0, bridge
assert unsupported <= requests, bridge
assert float(bridge["fasim_score_bridge_cpu_reference_seconds"]) > 0.0, bridge
assert float(bridge["fasim_score_bridge_total_seconds"]) >= 0.0, bridge
assert int(bridge["fasim_score_bridge_score_mismatches"]) == 0, bridge
assert int(bridge["fasim_score_bridge_endpoint_mismatches"]) >= 0, bridge
PY

echo "ok"
