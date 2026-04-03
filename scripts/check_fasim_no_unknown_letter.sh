#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_no_unknown_letter"
rm -rf "$WORK"
mkdir -p "$WORK/out" "$WORK/inputs"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

{
  echo ">hg19|chr1|1-5000"
  python3 - <<'PY'
print("a" * 5000)
PY
} >"$WORK/inputs/lower.fa"

set +e
(
  cd "$WORK/inputs"
  FASIM_VERBOSE=0 FASIM_OUTPUT_MODE=lite "$BIN" \
    -f1 lower.fa -f2 H19.fa -r 1 -O "$WORK/out" >"$WORK/stdout.log" 2>"$WORK/stderr.log"
)
status=$?
set -e

if [[ $status -ne 0 ]]; then
  echo "fasim failed (exit=$status). See: $WORK/stderr.log" >&2
  exit 1
fi

if rg -n "unknown letter" "$WORK/stdout.log" >/dev/null; then
  echo "unexpected 'unknown letter' in stdout. See: $WORK/stdout.log" >&2
  exit 1
fi

OUT_FILE="$WORK/out/hg19-H19-lower-TFOsorted.lite"
if [[ ! -s "$OUT_FILE" ]]; then
  echo "expected output missing: $OUT_FILE" >&2
  ls -la "$WORK/out" >&2 || true
  exit 1
fi

echo "ok"

