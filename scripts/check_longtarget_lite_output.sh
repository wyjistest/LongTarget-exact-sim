#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build)
fi

WORK="$ROOT/.tmp/check_longtarget_lite_output"
STDOUT_LOG="$WORK/stdout.log"
OUT_DIR="$WORK/out"

rm -rf "$WORK"
mkdir -p "$OUT_DIR"

(
  cd "$ROOT"
  LONGTARGET_OUTPUT_MODE=lite "$BIN" \
    -f1 testDNA.fa -f2 H19.fa -r 1 -O "$OUT_DIR" >"$STDOUT_LOG"
)

OUT_FILE="$OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
if [[ ! -s "$OUT_FILE" ]]; then
  echo "expected lite output missing: $OUT_FILE" >&2
  ls -la "$OUT_DIR" >&2 || true
  exit 1
fi

if [[ -e "$OUT_DIR/hg19-H19-testDNA-TFOsorted" ]]; then
  echo "unexpected full TFOsorted produced in lite mode" >&2
  exit 1
fi

if [[ -e "$OUT_DIR/hg19-H19-testDNA-TFOclass1-15-50" || -e "$OUT_DIR/hg19-H19-testDNA-TFOclass2-15-50" ]]; then
  echo "unexpected clustering outputs produced in lite mode" >&2
  ls -la "$OUT_DIR" >&2 || true
  exit 1
fi

if [[ -s "$STDOUT_LOG" ]]; then
  echo "expected stdout to stay quiet in lite mode" >&2
  cat "$STDOUT_LOG" >&2
  exit 1
fi

HEADER="$(head -n 1 "$OUT_FILE" | tr -d '\r')"
if [[ "$HEADER" != $'Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\tMeanStability' ]]; then
  echo "unexpected lite header:" >&2
  echo "$HEADER" >&2
  exit 1
fi

echo "ok"
