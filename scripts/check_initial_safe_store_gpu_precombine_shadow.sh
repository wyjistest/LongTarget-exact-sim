#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_precombine_shadow}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"

if [ ! -f "$STDERR_LOG" ]; then
  echo "missing stderr log: $STDERR_LOG" >&2
  exit 1
fi

grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_enabled=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_calls=[1-9][0-9]*$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_input_summaries=44777038$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_unique_states=8831091$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_est_saved_upserts=35945947$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_h2d_bytes=1432865216$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_d2h_bytes=317919276$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_size_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_order_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_shadow_digest_mismatches=0$' "$STDERR_LOG"
