#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_precombine}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"
EXPECTED_VALIDATE=${EXPECTED_VALIDATE:-0}
EXPECTED_INPUT_SOURCE=${EXPECTED_INPUT_SOURCE:-host_h2d}
EXPECTED_H2D_BYTES=${EXPECTED_H2D_BYTES:-1432865216}
EXPECTED_RESIDENT_REQUESTED=${EXPECTED_RESIDENT_REQUESTED:-0}
EXPECTED_RESIDENT_ACTIVE=${EXPECTED_RESIDENT_ACTIVE:-0}
EXPECTED_RESIDENT_SUPPORTED=${EXPECTED_RESIDENT_SUPPORTED:-0}
EXPECTED_RESIDENT_DISABLED_REASON=${EXPECTED_RESIDENT_DISABLED_REASON:-not_requested}
EXPECTED_SUMMARY_H2D_ELIDED=${EXPECTED_SUMMARY_H2D_ELIDED:-0}
EXPECTED_SUMMARY_H2D_BYTES_SAVED=${EXPECTED_SUMMARY_H2D_BYTES_SAVED:-0}

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
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_h2d_bytes=${EXPECTED_H2D_BYTES}$" "$STDERR_LOG"
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

grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_resident_source_requested=${EXPECTED_RESIDENT_REQUESTED}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_resident_source_active=${EXPECTED_RESIDENT_ACTIVE}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_resident_source_supported=${EXPECTED_RESIDENT_SUPPORTED}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_resident_source_disabled_reason=${EXPECTED_RESIDENT_DISABLED_REASON}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_summary_h2d_elided=${EXPECTED_SUMMARY_H2D_ELIDED}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_summary_h2d_bytes_saved=${EXPECTED_SUMMARY_H2D_BYTES_SAVED}$" "$STDERR_LOG"
grep -Eq "^benchmark\\.sim_initial_safe_store_gpu_precombine_input_source=${EXPECTED_INPUT_SOURCE}$" "$STDERR_LOG"
