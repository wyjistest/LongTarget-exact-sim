#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-sample_exactness_cuda}"
RULE="${RULE:-0}"
STRAND="${STRAND:-}"
WORK_DIR="$ROOT_DIR/.tmp/$OUTPUT_SUBDIR"
OUTPUT_DIR="$WORK_DIR/output"
EXPECTED_DIR="${EXPECTED_DIR:-$ROOT_DIR/tests/oracle}"
EXPECTED_BACKEND="${EXPECTED_BACKEND:-cuda}"
EXPECTED_SIM_INITIAL_BACKEND="${EXPECTED_SIM_INITIAL_BACKEND:-}"
EXPECTED_SIM_REGION_BACKEND="${EXPECTED_SIM_REGION_BACKEND:-}"
EXPECTED_SIM_LOCATE_MODE="${EXPECTED_SIM_LOCATE_MODE:-}"
EXPECTED_SIM_TRACEBACK_BACKEND="${EXPECTED_SIM_TRACEBACK_BACKEND:-}"
EXPECTED_SIM_SOLVER_BACKEND="${EXPECTED_SIM_SOLVER_BACKEND:-}"

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

STDERR_LOG="$WORK_DIR/stderr.log"
rm -f "$STDERR_LOG"

set -- -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$OUTPUT_DIR"
if [ -n "$STRAND" ]; then
  set -- "$@" -t "$STRAND"
fi

LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 $RUN_PREFIX "$TARGET" "$@" 2>"$STDERR_LOG"

if [ ! -d "$EXPECTED_DIR" ]; then
  echo "missing oracle directory: $EXPECTED_DIR" >&2
  exit 1
fi

diff -ru "$EXPECTED_DIR" "$OUTPUT_DIR"

if [ -n "$EXPECTED_BACKEND" ]; then
  grep -q "benchmark.calc_score_backend=$EXPECTED_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_INITIAL_BACKEND" ]; then
  grep -q "benchmark.sim_initial_backend=$EXPECTED_SIM_INITIAL_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_REGION_BACKEND" ]; then
  grep -q "benchmark.sim_region_backend=$EXPECTED_SIM_REGION_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_LOCATE_MODE" ]; then
  grep -q "benchmark.sim_locate_mode=$EXPECTED_SIM_LOCATE_MODE" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_TRACEBACK_BACKEND" ]; then
  grep -q "benchmark.sim_traceback_backend=$EXPECTED_SIM_TRACEBACK_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_SOLVER_BACKEND" ]; then
  grep -q "benchmark.sim_solver_backend=$EXPECTED_SIM_SOLVER_BACKEND" "$STDERR_LOG"
fi
