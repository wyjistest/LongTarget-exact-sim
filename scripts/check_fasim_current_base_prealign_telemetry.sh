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
grep -Eq '^benchmark\.fasim_output_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' "$WORK/on/stderr.log"
grep -Eq '^benchmark\.fasim_prealign_cuda_fallbacks=[0-9]+$' "$WORK/on/stderr.log"

echo "ok"
