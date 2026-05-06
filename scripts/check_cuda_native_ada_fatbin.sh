#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
CUOBJDUMP="${CUOBJDUMP:-$CUDA_HOME/bin/cuobjdump}"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda_sm89}"
WORK_DIR="$ROOT_DIR/.tmp/cuda_native_ada_fatbin"

if [ ! -x "$CUOBJDUMP" ]; then
  echo "cuobjdump not found at $CUOBJDUMP" >&2
  exit 1
fi

mkdir -p "$WORK_DIR"

"$CUOBJDUMP" -lelf "$TARGET" >"$WORK_DIR/elf.txt"
"$CUOBJDUMP" -lptx "$TARGET" >"$WORK_DIR/ptx.txt"

grep -Eq 'sm_89\.cubin$' "$WORK_DIR/elf.txt"
grep -Eq 'sm_80\.ptx$' "$WORK_DIR/ptx.txt"

CUDA_FORCE_PTX_JIT=1 \
LONGTARGET_ENABLE_CUDA=1 \
RULE=1 \
EXPECTED_DIR="$ROOT_DIR/tests/oracle_rule1" \
OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sm89_ptx \
TARGET="$TARGET" \
"$ROOT_DIR/scripts/run_sample_exactness_cuda.sh"
