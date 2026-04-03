#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_x86}"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-sample_exactness}"
RULE="${RULE:-0}"
STRAND="${STRAND:-}"
WORK_DIR="$ROOT_DIR/.tmp/$OUTPUT_SUBDIR"
OUTPUT_DIR="$WORK_DIR/output"
EXPECTED_DIR="${EXPECTED_DIR:-$ROOT_DIR/tests/oracle}"
GENERATE_ORACLE=0

if [ "${1:-}" = "--generate-oracle" ]; then
  GENERATE_ORACLE=1
fi

mkdir -p "$WORK_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$ROOT_DIR"

RUN_PREFIX=""
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  RUN_PREFIX="arch -x86_64"
fi

if [ ! -x "$TARGET" ]; then
  echo "missing binary: $TARGET" >&2
  exit 1
fi

set -- -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$OUTPUT_DIR"
if [ -n "$STRAND" ]; then
  set -- "$@" -t "$STRAND"
fi

$RUN_PREFIX "$TARGET" "$@"

if [ "$GENERATE_ORACLE" -eq 1 ]; then
  rm -rf "$EXPECTED_DIR"
  mkdir -p "$EXPECTED_DIR"
  cp "$OUTPUT_DIR"/* "$EXPECTED_DIR"/
  echo "oracle updated in $EXPECTED_DIR"
  exit 0
fi

if [ ! -d "$EXPECTED_DIR" ]; then
  echo "missing oracle directory: $EXPECTED_DIR" >&2
  exit 1
fi

diff -ru "$EXPECTED_DIR" "$OUTPUT_DIR"
