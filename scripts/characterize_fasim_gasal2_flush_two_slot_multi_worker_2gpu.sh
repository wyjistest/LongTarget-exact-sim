#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v1"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
WORKERS="${WORKERS:-1,2,4,6}"
GPU_IDS="${GPU_IDS:-0,1}"
CPU_POOL="${CPU_POOL:-0-17}"
CPU_CORES_PER_WORKER="${CPU_CORES_PER_WORKER:-3}"
REPEATS="${REPEATS:-1}"
SMOKE="${SMOKE:-0}"
BUILD_BIN="${BUILD_BIN:-1}"
KEEP_GOING="${KEEP_GOING:-1}"

if [[ "$BUILD_BIN" == "1" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
elif [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

args=(
  --fasim-bin "$BIN"
  --work-dir "$WORK"
  --rna "$RNA"
  --rule "$RULE"
  --workers "$WORKERS"
  --gpu-ids "$GPU_IDS"
  --cpu-pool "$CPU_POOL"
  --cpu-cores-per-worker "$CPU_CORES_PER_WORKER"
  --repeats "$REPEATS"
)

if [[ "$SMOKE" == "1" ]]; then
  args+=(--smoke)
fi
if [[ "$KEEP_GOING" == "1" ]]; then
  args+=(--keep-going)
fi

python3 "$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu.py" "${args[@]}"
