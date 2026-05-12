#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_best_path}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"

if [ ! -f "$STDERR_LOG" ]; then
  echo "missing stderr log: $STDERR_LOG" >&2
  exit 1
fi

OUTPUT_SUBDIR="$OUTPUT_SUBDIR" sh ./scripts/check_initial_safe_store_gpu_precombine_prune.sh

grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_requested=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_active=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_real_requested=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_real_active=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_requested=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_active=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_fallbacks=0$' "$STDERR_LOG"
