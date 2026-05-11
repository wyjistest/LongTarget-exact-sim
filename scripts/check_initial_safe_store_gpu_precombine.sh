#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_precombine}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"
EXPECTED_VALIDATE=${EXPECTED_VALIDATE:-0}

if [ ! -f "$STDERR_LOG" ]; then
  echo "missing stderr log: $STDERR_LOG" >&2
  exit 1
fi

grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_requested=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_active=1$' "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_validate_enabled=${EXPECTED_VALIDATE}$" "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_calls=[1-9][0-9]*$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_input_summaries=44777038$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_unique_states=8831091$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_est_saved_upserts=35945947$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_h2d_bytes=1432865216$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_d2h_bytes=317919276$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_size_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_order_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_digest_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_fallbacks=0$' "$STDERR_LOG"

if [ "$EXPECTED_VALIDATE" = "1" ]; then
  grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_validate_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
else
  grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_validate_seconds=0$' "$STDERR_LOG"
fi
