#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_align_profile_reuse_shadow"

rm -rf "$WORK"
mkdir -p "$WORK/off" "$WORK/on"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/off" \
  >"$WORK/off/stdout.log" \
  2>"$WORK/off/stderr.log"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
FASIM_ALIGN_PROFILE_REUSE_SHADOW=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/on" \
  >"$WORK/on/stdout.log" \
  2>"$WORK/on/stderr.log"

OUT_OFF="$WORK/off/hg19-H19-testDNA-TFOsorted.lite"
OUT_ON="$WORK/on/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_OFF"
test -s "$OUT_ON"

python3 - "$OUT_OFF" "$OUT_ON" "$WORK/on/stderr.log" <<'PY'
import re
import sys
from pathlib import Path

def canonical(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    assert lines, path
    header = lines[0]
    rows = sorted(line for line in lines[1:] if line.strip())
    return header, rows

assert canonical(sys.argv[1]) == canonical(sys.argv[2])

telemetry = {}
for line in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines():
    match = re.match(r"^benchmark\.(fasim_[A-Za-z0-9_]+)=(.*)$", line.strip())
    if not match:
        continue
    telemetry[match.group(1)] = match.group(2)

required = [
    "fasim_align_profile_reuse_shadow_enabled",
    "fasim_align_profile_build_calls",
    "fasim_align_profile_unique_keys",
    "fasim_align_profile_reusable_calls",
    "fasim_align_profile_build_seconds",
    "fasim_align_profile_est_saved_seconds",
    "fasim_align_query_unique_keys",
    "fasim_align_query_reusable_calls",
]
missing = [key for key in required if key not in telemetry]
assert not missing, missing

assert telemetry["fasim_align_profile_reuse_shadow_enabled"] == "1", telemetry
build_calls = int(telemetry["fasim_align_profile_build_calls"])
unique_keys = int(telemetry["fasim_align_profile_unique_keys"])
reusable_calls = int(telemetry["fasim_align_profile_reusable_calls"])
query_unique_keys = int(telemetry["fasim_align_query_unique_keys"])
query_reusable_calls = int(telemetry["fasim_align_query_reusable_calls"])
build_seconds = float(telemetry["fasim_align_profile_build_seconds"])
saved_seconds = float(telemetry["fasim_align_profile_est_saved_seconds"])

assert build_calls > 0, telemetry
assert unique_keys > 0, telemetry
assert query_unique_keys > 0, telemetry
assert reusable_calls == build_calls - unique_keys, telemetry
assert query_reusable_calls == build_calls - query_unique_keys, telemetry
assert build_seconds > 0.0, telemetry
assert 0.0 <= saved_seconds <= build_seconds, telemetry
PY

grep -Eq '^benchmark\.fasim_align_profile_reuse_shadow_enabled=0$' "$WORK/off/stderr.log"

echo "ok"
