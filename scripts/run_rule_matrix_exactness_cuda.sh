#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-rule_matrix_exactness_cuda}"
EXPECTED_BACKEND="${EXPECTED_BACKEND:-cuda}"
EXPECTED_SIM_INITIAL_BACKEND="${EXPECTED_SIM_INITIAL_BACKEND:-}"
EXPECTED_SIM_REGION_BACKEND="${EXPECTED_SIM_REGION_BACKEND:-}"

if [ ! -x "$TARGET" ]; then
  echo "missing binary: $TARGET" >&2
  exit 1
fi

STDERR_LOG="$ROOT_DIR/.tmp/rule_matrix_exactness_cuda.stderr.log"
mkdir -p "$ROOT_DIR/.tmp"
rm -f "$STDERR_LOG"

LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 TARGET="$TARGET" OUTPUT_SUBDIR="$OUTPUT_SUBDIR" ./scripts/run_rule_matrix_exactness.sh 2>"$STDERR_LOG"

if [ -n "$EXPECTED_BACKEND" ]; then
  grep -q "benchmark.calc_score_backend=$EXPECTED_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_INITIAL_BACKEND" ]; then
  grep -q "benchmark.sim_initial_backend=$EXPECTED_SIM_INITIAL_BACKEND" "$STDERR_LOG"
fi

if [ -n "$EXPECTED_SIM_REGION_BACKEND" ]; then
  grep -q "benchmark.sim_region_backend=$EXPECTED_SIM_REGION_BACKEND" "$STDERR_LOG"
fi
