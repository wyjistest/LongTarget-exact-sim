#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_align_profile_cache"

rm -rf "$WORK"
mkdir -p "$WORK/off" "$WORK/cache" "$WORK/validate"

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
FASIM_ALIGN_PROFILE_CACHE=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/cache" \
  >"$WORK/cache/stdout.log" \
  2>"$WORK/cache/stderr.log"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/validate" \
  >"$WORK/validate/stdout.log" \
  2>"$WORK/validate/stderr.log"

OUT_OFF="$WORK/off/hg19-H19-testDNA-TFOsorted.lite"
OUT_CACHE="$WORK/cache/hg19-H19-testDNA-TFOsorted.lite"
OUT_VALIDATE="$WORK/validate/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_OFF"
test -s "$OUT_CACHE"
test -s "$OUT_VALIDATE"

python3 - "$OUT_OFF" "$OUT_CACHE" "$OUT_VALIDATE" \
  "$WORK/off/stderr.log" "$WORK/cache/stderr.log" "$WORK/validate/stderr.log" <<'PY'
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
assert canonical(sys.argv[1]) == canonical(sys.argv[3])

off = telemetry(sys.argv[4])
cache = telemetry(sys.argv[5])
validate = telemetry(sys.argv[6])

required = [
    "fasim_align_profile_cache_requested",
    "fasim_align_profile_cache_active",
    "fasim_align_profile_cache_validate",
    "fasim_align_profile_cache_calls",
    "fasim_align_profile_cache_hits",
    "fasim_align_profile_cache_misses",
    "fasim_align_profile_cache_unique_keys",
    "fasim_align_profile_cache_build_seconds",
    "fasim_align_profile_cache_saved_seconds",
    "fasim_align_profile_cache_validate_seconds",
    "fasim_align_profile_cache_score_mismatches",
    "fasim_align_profile_cache_endpoint_mismatches",
    "fasim_align_profile_cache_cigar_mismatches",
    "fasim_align_profile_cache_digest_mismatches",
    "fasim_align_profile_cache_fallbacks",
]
for name, values in [("off", off), ("cache", cache), ("validate", validate)]:
    missing = [key for key in required if key not in values]
    assert not missing, (name, missing)

assert off["fasim_align_profile_cache_requested"] == "0", off
assert off["fasim_align_profile_cache_active"] == "0", off
assert off["fasim_align_profile_cache_validate"] == "0", off
assert int(off["fasim_align_profile_cache_calls"]) == 0, off
assert int(off["fasim_align_profile_cache_hits"]) == 0, off
assert int(off["fasim_align_profile_cache_misses"]) == 0, off
assert int(off["fasim_align_profile_cache_unique_keys"]) == 0, off
assert int(off["fasim_align_profile_cache_fallbacks"]) == 0, off

for name, values, expect_validate in [
    ("cache", cache, "0"),
    ("validate", validate, "1"),
]:
    calls = int(values["fasim_align_profile_cache_calls"])
    hits = int(values["fasim_align_profile_cache_hits"])
    misses = int(values["fasim_align_profile_cache_misses"])
    unique_keys = int(values["fasim_align_profile_cache_unique_keys"])
    build_seconds = float(values["fasim_align_profile_cache_build_seconds"])
    saved_seconds = float(values["fasim_align_profile_cache_saved_seconds"])
    validate_seconds = float(values["fasim_align_profile_cache_validate_seconds"])
    assert values["fasim_align_profile_cache_requested"] == "1", (name, values)
    assert values["fasim_align_profile_cache_active"] == "1", (name, values)
    assert values["fasim_align_profile_cache_validate"] == expect_validate, (name, values)
    assert calls > 0, (name, values)
    assert hits > 0, (name, values)
    assert misses > 0, (name, values)
    assert calls == hits + misses, (name, values)
    assert 0 < unique_keys <= misses, (name, values)
    assert build_seconds > 0.0, (name, values)
    assert saved_seconds >= 0.0, (name, values)
    assert validate_seconds >= 0.0, (name, values)
    assert int(values["fasim_align_profile_cache_score_mismatches"]) == 0, (name, values)
    assert int(values["fasim_align_profile_cache_endpoint_mismatches"]) == 0, (name, values)
    assert int(values["fasim_align_profile_cache_cigar_mismatches"]) == 0, (name, values)
    assert int(values["fasim_align_profile_cache_digest_mismatches"]) == 0, (name, values)
    assert int(values["fasim_align_profile_cache_fallbacks"]) == 0, (name, values)

assert float(validate["fasim_align_profile_cache_validate_seconds"]) > 0.0, validate
PY

echo "ok"
