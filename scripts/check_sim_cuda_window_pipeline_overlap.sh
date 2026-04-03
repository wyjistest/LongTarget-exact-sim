#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_window_pipeline_overlap"
BASE_OUT_DIR="$WORK_DIR/base_out"
PIPE_OUT_DIR="$WORK_DIR/pipeline_out"
OVERLAP_OUT_DIR="$WORK_DIR/overlap_out"
PIPE_STDERR="$WORK_DIR/pipeline.stderr"
OVERLAP_STDERR="$WORK_DIR/overlap.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$BASE_OUT_DIR" "$PIPE_OUT_DIR" "$OVERLAP_OUT_DIR"
mkdir -p "$BASE_OUT_DIR" "$PIPE_OUT_DIR" "$OVERLAP_OUT_DIR"
rm -f "$PIPE_STDERR" "$OVERLAP_STDERR"

cd "$ROOT_DIR"

RULE="${RULE:-1}"

LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$BASE_OUT_DIR" >/dev/null

LONGTARGET_BENCHMARK=1 \
LONGTARGET_OUTPUT_MODE=lite \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 \
LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_SIM_CUDA_WINDOW_PIPELINE_BATCH_SIZE=2 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$PIPE_OUT_DIR" >/dev/null 2>"$PIPE_STDERR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_OUTPUT_MODE=lite \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 \
LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE_OVERLAP=1 \
LONGTARGET_SIM_CUDA_WINDOW_PIPELINE_BATCH_SIZE=2 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$OVERLAP_OUT_DIR" >/dev/null 2>"$OVERLAP_STDERR"

grep -Eq '^benchmark\.sim_solver_backend=cuda_window_pipeline$' "$PIPE_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_batches=[1-9][0-9]*$' "$PIPE_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_overlap_enabled=0$' "$PIPE_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_overlap_batches=0$' "$PIPE_STDERR"

grep -Eq '^benchmark\.sim_solver_backend=cuda_window_pipeline$' "$OVERLAP_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_batches=[1-9][0-9]*$' "$OVERLAP_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_overlap_enabled=1$' "$OVERLAP_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_overlap_batches=[1-9][0-9]*$' "$OVERLAP_STDERR"

BASE_LITE="$BASE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
PIPE_LITE="$PIPE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
OVERLAP_LITE="$OVERLAP_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$BASE_LITE" ] || [ ! -s "$PIPE_LITE" ] || [ ! -s "$OVERLAP_LITE" ]; then
  echo "missing lite outputs for window pipeline overlap check" >&2
  exit 1
fi

cmp -s "$BASE_LITE" "$PIPE_LITE"
cmp -s "$BASE_LITE" "$OVERLAP_LITE"
cmp -s "$PIPE_LITE" "$OVERLAP_LITE"
