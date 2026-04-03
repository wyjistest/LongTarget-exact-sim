#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_initial_proposal_v2_exactness"
BASE_OUT_DIR="$WORK_DIR/base_out"
V2_OUT_DIR="$WORK_DIR/v2_out"
BASE_STDERR="$WORK_DIR/base.stderr"
V2_STDERR="$WORK_DIR/v2.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$BASE_OUT_DIR" "$V2_OUT_DIR"
mkdir -p "$BASE_OUT_DIR" "$V2_OUT_DIR"
rm -f "$BASE_STDERR" "$V2_STDERR"

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
LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2=1 \
LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND=cpu \
LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r 0 -O "$V2_OUT_DIR" >/dev/null 2>"$V2_STDERR"

grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_backend=cuda$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_proposal_backend=cuda$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_batches=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_requests=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_batches=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_logical_candidate_states=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_materialized_candidate_states=0$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_gpu_seconds=0(\.0+)?$' "$BASE_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_batches=[1-9][0-9]*$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_v2_requests=[1-9][0-9]*$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_batches=[1-9][0-9]*$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_logical_candidate_states=[1-9][0-9]*$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_materialized_candidate_states=0$' "$V2_STDERR"
grep -Eq '^benchmark\.sim_initial_proposal_direct_topk_gpu_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.sim_initial_proposal_direct_topk_gpu_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$V2_STDERR"

BASE_LITE="$BASE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
V2_LITE="$V2_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$BASE_LITE" ] || [ ! -s "$V2_LITE" ]; then
  echo "missing lite outputs for initial proposal V2 exactness check" >&2
  exit 1
fi

BASE_SORTED="$WORK_DIR/base.sorted"
V2_SORTED="$WORK_DIR/v2.sorted"
sort "$BASE_LITE" >"$BASE_SORTED"
sort "$V2_LITE" >"$V2_SORTED"
cmp -s "$BASE_SORTED" "$V2_SORTED"
