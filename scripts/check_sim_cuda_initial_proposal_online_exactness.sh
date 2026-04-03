#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_initial_proposal_online_exactness"
BASE_OUT_DIR="$WORK_DIR/base_out"
ONLINE_OUT_DIR="$WORK_DIR/online_out"
BASE_STDERR="$WORK_DIR/base.stderr"
ONLINE_STDERR="$WORK_DIR/online.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$BASE_OUT_DIR" "$ONLINE_OUT_DIR"
mkdir -p "$BASE_OUT_DIR" "$ONLINE_OUT_DIR"
rm -f "$BASE_STDERR" "$ONLINE_STDERR"

cd "$ROOT_DIR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$BASE_OUT_DIR" >/dev/null 2>"$BASE_STDERR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$ONLINE_OUT_DIR" >/dev/null 2>"$ONLINE_STDERR"

grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$ONLINE_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$ONLINE_STDERR"
grep -Eq '^benchmark\.sim_initial_scan_diag_seconds=0(\.0+)?$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_scan_diag_seconds=[1-9][0-9]*(\.[0-9]+)?|^benchmark\.sim_initial_scan_diag_seconds=0\.[0-9]*[1-9][0-9]*$' "$ONLINE_STDERR"
grep -Eq '^benchmark\.sim_initial_scan_online_reduce_seconds=[1-9][0-9]*(\.[0-9]+)?|^benchmark\.sim_initial_scan_online_reduce_seconds=0\.[0-9]*[1-9][0-9]*$' "$ONLINE_STDERR"

BASE_LITE="$BASE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
ONLINE_LITE="$ONLINE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$BASE_LITE" ] || [ ! -s "$ONLINE_LITE" ]; then
  echo "missing lite outputs for initial proposal online exactness check" >&2
  exit 1
fi

BASE_SORTED="$WORK_DIR/base.sorted"
ONLINE_SORTED="$WORK_DIR/online.sorted"
sort "$BASE_LITE" >"$BASE_SORTED"
sort "$ONLINE_LITE" >"$ONLINE_SORTED"
cmp -s "$BASE_SORTED" "$ONLINE_SORTED"
