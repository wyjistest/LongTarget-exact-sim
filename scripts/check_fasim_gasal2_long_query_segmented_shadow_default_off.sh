#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_shadow_default_off"}"

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/default_off"

awk -v limit=8 '
  /^>/ {
    ++records
  }
  records <= limit {
    print
  }
' "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
  >"$WORK/inputs/malat1_first8.fa"

env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  "$BIN" \
  -f1 "$WORK/inputs/malat1_first8.fa" \
  -f2 "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  -r 0 \
  -O "$WORK/default_off" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

grep -Eq '^benchmark\.fasim_top5_gasal2_long_query_segmented_shadow_requested=0$' "$WORK/stderr.log"
grep -Eq '^benchmark\.fasim_top5_gasal2_long_query_segmented_shadow_active=0$' "$WORK/stderr.log"

echo "ok"
