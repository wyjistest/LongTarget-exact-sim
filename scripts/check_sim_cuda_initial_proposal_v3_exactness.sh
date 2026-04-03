#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_initial_proposal_v3_exactness"
BASE_OUT_DIR="$WORK_DIR/base_out"
V3_OUT_DIR="$WORK_DIR/v3_out"
BASE_STDERR="$WORK_DIR/base.stderr"
V3_STDERR="$WORK_DIR/v3.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$BASE_OUT_DIR" "$V3_OUT_DIR"
mkdir -p "$BASE_OUT_DIR" "$V3_OUT_DIR"
rm -f "$BASE_STDERR" "$V3_STDERR"

cd "$ROOT_DIR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$BASE_OUT_DIR" >/dev/null 2>"$BASE_STDERR"

LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP=1 \
LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$V3_OUT_DIR" >/dev/null 2>"$V3_STDERR"

grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_batches=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_requests=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_batches=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_requests=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_selected_candidate_states=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_gpu_seconds=0(\.0+)?$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_select_d2h_seconds=0(\.0+)?$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_scan_tail_seconds=[0-9]+(\.[0-9]+)?$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_batches=0$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_requests=0$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_batches=[1-9][0-9]*$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_requests=[1-9][0-9]*$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_selected_candidate_states=[1-9][0-9]*$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v3_gpu_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.sim_initial_proposal_v3_gpu_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_select_d2h_seconds=[0-9]+(\.[0-9]+)?$' "$V3_STDERR"
grep -Eq '^benchmark\.sim_initial_scan_tail_seconds=[0-9]+(\.[0-9]+)?$' "$V3_STDERR"

BASE_LITE="$BASE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
V3_LITE="$V3_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$BASE_LITE" ] || [ ! -s "$V3_LITE" ]; then
  echo "missing lite outputs for initial proposal V3 exactness check" >&2
  exit 1
fi

BASE_SORTED="$WORK_DIR/base.sorted"
V3_SORTED="$WORK_DIR/v3.sorted"
sort "$BASE_LITE" >"$BASE_SORTED"
sort "$V3_LITE" >"$V3_SORTED"
cmp -s "$BASE_SORTED" "$V3_SORTED"
