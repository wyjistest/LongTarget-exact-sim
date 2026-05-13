# CUDA Safe-Window Large Geometry Exact Shadow

Base branch:

```text
cuda-safe-window-large-geometry-shadow
```

Base commit:

```text
675c9be
```

This is a default-off diagnostic PR. It does not change safe-window planner
authority, region dispatch, safe-store/candidate replay semantics, runtime
defaults, the clean frontier gate, or any `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY` route.

## Goal

PR #42 showed a strong estimator signal for selected large/high-inflation
safe-window calls:

```text
selected calls = 204 / 515
current selected exec cells = 403,057,802
raw/shadow estimated cells = 318,729,080
estimated saved cells = 84,328,722
```

That was estimator-only. This PR adds a selected-bucket exact shadow:

```text
LONGTARGET_SIM_CUDA_SAFE_WINDOW_LARGE_GEOMETRY_EXACT_SHADOW=1
```

The diagnostic compares current coarsened authority against raw/finer geometry
for selected calls. It never feeds the raw/fine result into the real region,
safe-store, locate, candidate replay, or output path.

## Selection

A safe-window call is selected when either condition is true:

```text
raw cells > 1,000,000
inflated/raw > 25%
```

The thresholds intentionally match the estimator from PR #42.

## Telemetry

The PR emits:

```text
sim_safe_window_large_geometry_exact_shadow_enabled
sim_safe_window_large_geometry_exact_shadow_calls
sim_safe_window_large_geometry_exact_shadow_selected_calls
sim_safe_window_large_geometry_exact_shadow_compared_calls
sim_safe_window_large_geometry_exact_shadow_est_saved_cells
sim_safe_window_large_geometry_exact_shadow_result_mismatches
sim_safe_window_large_geometry_exact_shadow_count_mismatches
sim_safe_window_large_geometry_exact_shadow_digest_mismatches
sim_safe_window_large_geometry_exact_shadow_unsupported_calls
sim_safe_window_large_geometry_exact_shadow_fallbacks
```

`calls` counts safe-window-path diagnostic attempts. `selected_calls` counts the
large/high-inflation bucket. `compared_calls` counts selected calls where the
shadow could run both geometries and compare the resulting contexts.

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
OUTPUT_SUBDIR=cuda_safe_window_large_geometry_exact_shadow_r1
./scripts/run_sample_exactness_cuda.sh
```

Run log:

```text
.tmp/cuda_safe_window_large_geometry_exact_shadow_r1/stderr.log
```

## Result

The exact compare contract is available for the selected bucket, but it is not
clean:

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

The run still matched the existing oracle output because coarsened geometry
remained authority. The mismatch counters belong only to the diagnostic shadow.

Diagnostic runtime was high because the shadow executes the selected raw/fine
geometry side path:

| Field | Value |
| --- | ---: |
| sim_region_scan_gpu_seconds | 5.56826 |
| sim_region_d2h_seconds | 1.30593 |
| sim_seconds | 52.6166 |
| total_seconds | 55.939 |

This timing is not an optimization A/B. It only shows that the exact shadow is
expensive enough to keep as a diagnostic.

## Interpretation

PR #42 remains a strong estimator result, but this PR does not support a real
large-window geometry path:

```text
selected-bucket exact compare: available
selected calls compared: 204 / 204
digest mismatches: 203
real/default geometry path: no
recommended opt-in: no
```

The mismatch-heavy result means the current raw/finer geometry is not a safe
drop-in replacement for coarsened safe-window authority, even on the selected
large/high-inflation bucket.

## Decision

Do not proceed to:

```text
LONGTARGET_SIM_CUDA_SAFE_WINDOW_LARGE_GEOMETRY=1
fine/raw geometry default
region batching / true-batch
safe-window planner authority changes
```

Next reasonable directions:

```text
region kernel / cell-work profiling
safe-window planner fallback analysis
calc_score side lane
```

If safe-window geometry is revisited, it should start by explaining the digest
mismatch pattern, not by adding a real geometry opt-in.
