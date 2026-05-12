#!/bin/sh
set -eu

OUTPUT_SUBDIR=${OUTPUT_SUBDIR:-sample_exactness_cuda_sim_region_locate_gpu_precombine_prune_packed_d2h}
STDERR_LOG=".tmp/${OUTPUT_SUBDIR}/stderr.log"

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
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_d2h_bytes_saved=198716040$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_order_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_digest_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_fallbacks=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_input_source=device_resident$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_h2d_bytes=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_fallbacks=0$' "$STDERR_LOG"

grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_requested=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_active=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_supported=1$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_disabled_reason=active$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes=[1-9][0-9]*$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_unpacked_d2h_bytes=119203236$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes_saved=[1-9][0-9]*$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_pack_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_unpack_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_fallbacks=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_size_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_candidate_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_order_mismatches=0$' "$STDERR_LOG"
grep -Eq '^benchmark\.sim_initial_safe_store_gpu_precombine_prune_packed_digest_mismatches=0$' "$STDERR_LOG"

python3 - "$STDERR_LOG" <<'PY'
import sys

values = {}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    for line in handle:
        if not line.startswith("benchmark."):
            continue
        key, _, value = line.strip().partition("=")
        values[key] = value

packed = int(values["benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes"])
unpacked = int(values["benchmark.sim_initial_safe_store_gpu_precombine_prune_unpacked_d2h_bytes"])
saved = int(values["benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes_saved"])
if not (0 < packed < unpacked):
    raise SystemExit(f"packed bytes must be positive and below unpacked bytes: {packed} >= {unpacked}")
if saved != unpacked - packed:
    raise SystemExit(f"packed bytes saved mismatch: {saved} != {unpacked - packed}")
PY
