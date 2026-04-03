#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/benchmark_worker_telemetry"
OUTPUT_DIR="$WORK_DIR/output"
STDERR_LOG="$WORK_DIR/stderr.log"

mkdir -p "$WORK_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
rm -f "$STDERR_LOG"

cd "$ROOT_DIR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_CUDA_DEVICES=0 \
LONGTARGET_SIM_CUDA_WORKERS_PER_DEVICE=2 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$OUTPUT_DIR" >/dev/null 2>"$STDERR_LOG"

grep -Eq '^benchmark\.sim_cuda_worker_count=2$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_device_count=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_0_device=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_1_device=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_0_slot=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_1_slot=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_0_tasks=[0-9]+$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_1_tasks=[0-9]+$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_0_sim_seconds=[0-9]+(\.[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_worker_1_sim_seconds=[0-9]+(\.[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_device_0_workers=2$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_device_0_tasks=[0-9]+$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_cuda_device_0_sim_seconds=[0-9]+(\.[0-9]+)?$' "$STDERR_LOG"
