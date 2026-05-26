#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
WORK="$ROOT/.tmp/check_fasim_current_base_prealign_telemetry"

rm -rf "$WORK"
mkdir -p "$WORK/on" "$WORK/repeat"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/on" \
  >"$WORK/on/stdout.log" \
  2>"$WORK/on/stderr.log"

FASIM_OUTPUT_MODE=lite \
FASIM_VERBOSE=0 \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=2 \
"$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 1 -O "$WORK/repeat" \
  >"$WORK/repeat/stdout.log" \
  2>"$WORK/repeat/stderr.log"

OUT_ON="$WORK/on/hg19-H19-testDNA-TFOsorted.lite"
OUT_REPEAT="$WORK/repeat/hg19-H19-testDNA-TFOsorted.lite"
test -s "$OUT_ON"
test -s "$OUT_REPEAT"
python3 - "$OUT_ON" "$OUT_REPEAT" <<'PY'
import sys
from pathlib import Path

def canonical(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    assert lines, path
    header = lines[0]
    rows = sorted(line for line in lines[1:] if line.strip())
    return header, rows

assert canonical(sys.argv[1]) == canonical(sys.argv[2])
PY

grep -Eq '^benchmark\.fasim_prealign_cuda_requested=1$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_active=[01]$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_device=-?[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_devices=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_tasks=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_batches=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_topk=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_max_tasks=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_peak_suppress_bp=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_h2d_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_kernel_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_d2h_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_total_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_threads=2$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_candidates=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_cutlength_attempts=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_align_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_align_cells=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_align_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_convert_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_convert_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_sort_unique_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_records_before_filter=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_records_emitted=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_extend_empty_scoreinfo=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_query_translate_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_ref_translate_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_ssw_total_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_forward_score_end_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_reverse_start_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_traceback_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_convert_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_cleanup_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_byte_forward_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_word_forward_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_reverse_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_traceback_calls=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_null_results=[0-9]+$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_reuse_shadow_enabled=0$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_build_calls=0$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_unique_keys=0$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_reusable_calls=0$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_build_seconds=0(\.0+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_profile_est_saved_seconds=0(\.0+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_query_unique_keys=0$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_align_query_reusable_calls=0$' "$WORK/on/stderr.log"
python3 - "$WORK/on/stderr.log" <<'PY'
import os
import re
import sys
from pathlib import Path

telemetry = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    match = re.match(r"^benchmark\.(fasim_[A-Za-z0-9_]+)=(.*)$", line.strip())
    if match:
        telemetry[match.group(1)] = match.group(2)

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
missing = [key for key in required if key not in telemetry]
assert not missing, missing

cache_enabled = os.environ.get("FASIM_ALIGN_PROFILE_CACHE", "") not in ("", "0")
validate_enabled = os.environ.get("FASIM_ALIGN_PROFILE_CACHE_VALIDATE", "") not in ("", "0")

if not cache_enabled:
    assert telemetry["fasim_align_profile_cache_requested"] == "0", telemetry
    assert telemetry["fasim_align_profile_cache_active"] == "0", telemetry
    assert telemetry["fasim_align_profile_cache_validate"] == "0", telemetry
    assert int(telemetry["fasim_align_profile_cache_calls"]) == 0, telemetry
    assert int(telemetry["fasim_align_profile_cache_hits"]) == 0, telemetry
    assert int(telemetry["fasim_align_profile_cache_misses"]) == 0, telemetry
    assert int(telemetry["fasim_align_profile_cache_unique_keys"]) == 0, telemetry
    assert float(telemetry["fasim_align_profile_cache_build_seconds"]) == 0.0, telemetry
    assert float(telemetry["fasim_align_profile_cache_saved_seconds"]) == 0.0, telemetry
    assert float(telemetry["fasim_align_profile_cache_validate_seconds"]) == 0.0, telemetry
else:
    calls = int(telemetry["fasim_align_profile_cache_calls"])
    hits = int(telemetry["fasim_align_profile_cache_hits"])
    misses = int(telemetry["fasim_align_profile_cache_misses"])
    unique_keys = int(telemetry["fasim_align_profile_cache_unique_keys"])
    assert telemetry["fasim_align_profile_cache_requested"] == "1", telemetry
    assert telemetry["fasim_align_profile_cache_active"] == "1", telemetry
    assert telemetry["fasim_align_profile_cache_validate"] == ("1" if validate_enabled else "0"), telemetry
    assert calls > 0, telemetry
    assert hits > 0, telemetry
    assert misses > 0, telemetry
    assert calls == hits + misses, telemetry
    assert 0 < unique_keys <= misses, telemetry
    assert float(telemetry["fasim_align_profile_cache_build_seconds"]) > 0.0, telemetry
    assert float(telemetry["fasim_align_profile_cache_saved_seconds"]) >= 0.0, telemetry
    if validate_enabled:
        assert float(telemetry["fasim_align_profile_cache_validate_seconds"]) > 0.0, telemetry
    else:
        assert float(telemetry["fasim_align_profile_cache_validate_seconds"]) == 0.0, telemetry

assert int(telemetry["fasim_align_profile_cache_score_mismatches"]) == 0, telemetry
assert int(telemetry["fasim_align_profile_cache_endpoint_mismatches"]) == 0, telemetry
assert int(telemetry["fasim_align_profile_cache_cigar_mismatches"]) == 0, telemetry
assert int(telemetry["fasim_align_profile_cache_digest_mismatches"]) == 0, telemetry
assert int(telemetry["fasim_align_profile_cache_fallbacks"]) == 0, telemetry
PY
grep -Eq '^benchmark\.fasim_output_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_fallbacks=[0-9]+$' "$WORK/on/stderr.log"

echo "ok"
