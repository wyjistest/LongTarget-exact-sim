#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_next_reducer_runtime_smoke"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"
mkdir -p "$WORK/out"
rna_input="$WORK/inputs/phase7_short_query.fa"
dna_input="$WORK/inputs/phase7_short_target.fa"
cat >"$rna_input" <<'EOF'
>phase7_short_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$dna_input" <<'EOF'
>phase7_short_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

env \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW=1 \
  "$BIN" \
  -f1 "$dna_input" \
  -f2 "$rna_input" \
  -r 0 \
  -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

python3 - "$WORK/stderr.log" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
required = [
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_requested=1",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_active=1",
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"missing runtime metric: {needle}")
print("ok")
PY
