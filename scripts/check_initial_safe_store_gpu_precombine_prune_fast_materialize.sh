#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_precombine_prune_fast_materialize}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"
EXPECTED_VALIDATE=${EXPECTED_VALIDATE:-0}

if [ ! -f "$STDERR_LOG" ]; then
  echo "missing stderr log: $STDERR_LOG" >&2
  exit 1
fi

grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_requested=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_active=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_calls=[1-9][0-9]*$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_input_states=8831091$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_kept_states=3311201$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_d2h_bytes=119203236$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_input_source=device_resident$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_h2d_bytes=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_d2h_bytes=119203236$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_fallbacks=0$' "$STDERR_LOG"

grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_requested=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_active=1$' "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_fast_materialize_validate_enabled=${EXPECTED_VALIDATE}$" "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_index_build_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_capacity_reuse_hits=[0-9]+$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_size_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_order_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_digest_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_fallbacks=0$' "$STDERR_LOG"

if [ "$EXPECTED_VALIDATE" = "1" ]; then
  grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_validate_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
else
  grep -Eq '^benchmark\.sim_initial_safe_store_fast_materialize_validate_seconds=0$' "$STDERR_LOG"
fi
