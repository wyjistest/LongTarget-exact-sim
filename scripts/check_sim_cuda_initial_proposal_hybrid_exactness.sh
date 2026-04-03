#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_initial_proposal_hybrid_exactness"
CPU_OUT_DIR="$WORK_DIR/cpu_out"
HYBRID_OUT_DIR="$WORK_DIR/hybrid_out"
CPU_STDERR="$WORK_DIR/cpu.stderr"
HYBRID_STDERR="$WORK_DIR/hybrid.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$CPU_OUT_DIR" "$HYBRID_OUT_DIR"
mkdir -p "$CPU_OUT_DIR" "$HYBRID_OUT_DIR"
rm -f "$CPU_STDERR" "$HYBRID_STDERR"

cd "$ROOT_DIR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$CPU_OUT_DIR" >/dev/null 2>"$CPU_STDERR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 \
LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=hybrid \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$HYBRID_OUT_DIR" >/dev/null 2>"$HYBRID_STDERR"

grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$CPU_STDERR"
grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$HYBRID_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$CPU_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$HYBRID_STDERR"
grep -Eq '^benchmark\.sim_proposal_materialize_backend=cpu$' "$CPU_STDERR"
grep -Eq '^benchmark\.sim_proposal_materialize_backend=hybrid$' "$HYBRID_STDERR"

CPU_LITE="$CPU_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
HYBRID_LITE="$HYBRID_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$CPU_LITE" ] || [ ! -s "$HYBRID_LITE" ]; then
  echo "missing lite outputs for initial proposal hybrid exactness check" >&2
  exit 1
fi

CPU_SORTED="$WORK_DIR/cpu.sorted"
HYBRID_SORTED="$WORK_DIR/hybrid.sorted"
sort "$CPU_LITE" >"$CPU_SORTED"
sort "$HYBRID_LITE" >"$HYBRID_SORTED"
cmp -s "$CPU_SORTED" "$HYBRID_SORTED"
