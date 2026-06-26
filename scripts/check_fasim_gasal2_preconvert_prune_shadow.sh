#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_preconvert_prune_shadow"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK/run"

env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
  FASIM_ALIGN_GASAL2_BATCH=20000 \
  FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
  FASIM_GASAL2_EQUIVALENCE_FIRST_CONVERT=1 \
  FASIM_ALIGN_GASAL2_PRECONVERT_PRUNE_SHADOW=1 \
  "$BIN" -f1 "$TARGET" -f2 "$RNA" -r 0 -O "$WORK/run" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$WORK/stderr.log"
}

requested="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_preconvert_prune_shadow_requested)"
active="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_preconvert_prune_shadow_active)"
prune_active="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_nt_sum_span_prune_active)"
attempts="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_preconvert_prune_shadow_attempts)"
false_negatives="$(metric benchmark.fasim_top5_gasal2_phase_gasal2_preconvert_prune_shadow_false_negatives)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "preconvert prune shadow did not activate: requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$prune_active" != "0" ]]; then
  echo "shadow gate must not enable real nt sum span pruning: prune_active=$prune_active" >&2
  exit 1
fi
if [[ "$attempts" == "0" ]]; then
  echo "expected shadow attempts > 0" >&2
  exit 1
fi
if [[ "$false_negatives" != "0" ]]; then
  echo "shadow candidate has false negatives: $false_negatives" >&2
  exit 1
fi

python3 "$ROOT/scripts/parse_fasim_gasal2_convert_funnel.py" \
  --stderr "$WORK/stderr.log" \
  --label preconvert_shadow \
  >"$WORK/convert_funnel.txt"

grep -Fxq "preconvert_prune_shadow_requested=1" "$WORK/convert_funnel.txt"
grep -Fxq "preconvert_prune_shadow_active=1" "$WORK/convert_funnel.txt"
grep -Fxq "preconvert_prune_shadow_attempts=$attempts" "$WORK/convert_funnel.txt"
grep -Fxq "preconvert_prune_shadow_false_negatives=0" "$WORK/convert_funnel.txt"

cat "$WORK/convert_funnel.txt"
echo "ok"
