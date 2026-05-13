# CUDA Safe-Window Large Geometry Digest Mismatch Taxonomy

Base branch:

```text
cuda-safe-window-large-geometry-exact-shadow
```

Base commit:

```text
b7367fd
```

This is a telemetry and documentation PR. It does not change safe-window planner
authority, region dispatch, safe-store/candidate replay semantics, runtime
defaults, the clean frontier gate, or any `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY` route.

## Goal

PR #43 made the selected-bucket exact shadow available, but the result was a
clear brake signal:

```text
selected_calls = 204
compared_calls = 204
result_mismatches = 0
count_mismatches = 0
digest_mismatches = 203
unsupported_calls = 0
fallbacks = 0
```

This PR classifies those digest mismatches to answer whether they are
order-only or semantic/canonical drift.

## Telemetry Added

The existing exact shadow now also emits:

```text
sim_safe_window_large_geometry_digest_mismatch_calls
sim_safe_window_large_geometry_order_only_mismatch_calls
sim_safe_window_large_geometry_value_mismatch_calls
sim_safe_window_large_geometry_set_mismatch_calls
sim_safe_window_large_geometry_first_mismatch_call
sim_safe_window_large_geometry_canonical_digest_mismatches
sim_safe_window_large_geometry_ordered_digest_mismatches
sim_safe_window_large_geometry_unordered_digest_mismatches
```

Interpretation:

```text
ordered digest:
  compares current in-memory candidate/safe-store order.

unordered/canonical digest:
  compares sorted/canonical candidate frontier and safe-store state sets.

order-only mismatch:
  ordered differs, but canonical/unordered compare matches.

value/set mismatch:
  canonical/unordered compare differs, so raw/finer geometry is not a
  drop-in semantic equivalent for the current coarsened authority.
```

## Mode

The sample run used the recommended safe-store GPU best path plus exact shadow:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_SAFE_WINDOW_LARGE_GEOMETRY_EXACT_SHADOW=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
OUTPUT_SUBDIR=cuda_safe_window_large_geometry_digest_taxonomy_r2
./scripts/run_sample_exactness_cuda.sh
```

Run log:

```text
.tmp/cuda_safe_window_large_geometry_digest_taxonomy_r2/stderr.log
```

## Result

| Field | Value |
| --- | ---: |
| sim_safe_window_large_geometry_exact_shadow_enabled | 1 |
| sim_safe_window_large_geometry_exact_shadow_calls | 515 |
| sim_safe_window_large_geometry_exact_shadow_selected_calls | 204 |
| sim_safe_window_large_geometry_exact_shadow_compared_calls | 204 |
| sim_safe_window_large_geometry_exact_shadow_est_saved_cells | 84,328,722 |
| sim_safe_window_large_geometry_exact_shadow_result_mismatches | 0 |
| sim_safe_window_large_geometry_exact_shadow_count_mismatches | 0 |
| sim_safe_window_large_geometry_exact_shadow_digest_mismatches | 203 |
| sim_safe_window_large_geometry_exact_shadow_unsupported_calls | 0 |
| sim_safe_window_large_geometry_exact_shadow_fallbacks | 0 |

Taxonomy:

| Field | Value |
| --- | ---: |
| sim_safe_window_large_geometry_digest_mismatch_calls | 203 |
| sim_safe_window_large_geometry_order_only_mismatch_calls | 0 |
| sim_safe_window_large_geometry_value_mismatch_calls | 203 |
| sim_safe_window_large_geometry_set_mismatch_calls | 203 |
| sim_safe_window_large_geometry_first_mismatch_call | 13 |
| sim_safe_window_large_geometry_canonical_digest_mismatches | 203 |
| sim_safe_window_large_geometry_ordered_digest_mismatches | 203 |
| sim_safe_window_large_geometry_unordered_digest_mismatches | 203 |

Timing from this diagnostic run:

| Field | Value |
| --- | ---: |
| sim_region_scan_gpu_seconds | 2.74396 |
| sim_region_d2h_seconds | 0.624768 |
| sim_seconds | 28.1874 |
| total_seconds | 30.1679 |

The run matched the existing oracle output because coarsened geometry remained
the real authority. The mismatch counters belong only to the diagnostic shadow.

## Interpretation

The 203 digest mismatches are not order-only:

```text
order_only_mismatch_calls = 0
canonical_digest_mismatches = 203
unordered_digest_mismatches = 203
value_mismatch_calls = 203
set_mismatch_calls = 203
```

This means canonical/unordered comparison still differs. The large-window
estimator from PR #42 remains useful as a measurement of inflated cell
opportunity, but the raw/finer selected-bucket geometry is not exact-safe.

## Decision

Do not proceed to:

```text
canonical digest shadow
large-window geometry validate/fallback opt-in
fine/raw geometry real path
safe-window planner authority changes
region batching / true-batch
```

Recommended next direction:

```text
region kernel / cell-work profiling
```

If geometry is revisited later, the first task should be explaining the
canonical value/set drift, not adding a real large-window geometry path.
