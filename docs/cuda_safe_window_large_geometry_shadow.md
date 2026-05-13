# CUDA Safe-Window Large Geometry Shadow

Base branch:

```text
cuda-safe-window-coarsening-distribution
```

Base commit:

```text
15626d1
```

This is a default-off diagnostic PR. It does not change safe-window planner
authority, region dispatch, safe-store/candidate replay semantics, runtime
defaults, the clean frontier gate, or any `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY` route.

## Goal

PR #41 showed that safe-window coarsening inflation is dominated by broad
large-window geometry rather than a few pathological calls:

```text
inflated cells = 98,253,644
large windows >1M raw cells: 79 / 515 calls
large-window inflated cells = 72,050,911 / 98,253,644 = 73.33%
top 3 inflated calls share = 7.15%
```

This PR adds a default-off diagnostic:

```text
LONGTARGET_SIM_CUDA_SAFE_WINDOW_LARGE_GEOMETRY_SHADOW=1
```

The diagnostic selects large-window or high-inflation safe-window calls and
estimates how many execution cells raw/finer geometry could save.

## Boundary

This is estimator-only. It does not execute raw/fine geometry, compare candidate
state output, or prove exactness.

Current coarsened geometry remains the only executed path:

```text
safe-window planner output -> coarsened execution workset -> existing region update
```

The diagnostic only records:

```text
current coarsened exec cells
raw/fine geometry cell estimate
estimated saved cells
thresholds and selection counts
```

The mismatch counter is emitted for schema compatibility, but it remains zero
because this PR does not run an exact shadow comparison.

## Selection

A safe-window call is selected when either condition is true:

```text
raw cells > 1,000,000
inflated/raw > 25%
```

Telemetry:

```text
sim_safe_window_large_geometry_shadow_enabled
sim_safe_window_large_geometry_shadow_calls
sim_safe_window_large_geometry_shadow_large_calls
sim_safe_window_large_geometry_shadow_threshold_raw_cells
sim_safe_window_large_geometry_shadow_threshold_inflation_pct
sim_safe_window_large_geometry_shadow_current_exec_cells
sim_safe_window_large_geometry_shadow_shadow_exec_cells
sim_safe_window_large_geometry_shadow_est_saved_cells
sim_safe_window_large_geometry_shadow_est_saved_ratio
sim_safe_window_large_geometry_shadow_mismatches
sim_safe_window_large_geometry_shadow_fallbacks
sim_safe_window_large_geometry_shadow_estimator_only
```

## Mode

The 3-run characterization used the recommended safe-store GPU best path with
both large-geometry shadow and geometry telemetry:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_SAFE_WINDOW_LARGE_GEOMETRY_SHADOW=1
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
./scripts/run_sample_exactness_cuda.sh
```

Run logs:

```text
.tmp/cuda_safe_window_large_geometry_shadow_geometry_r1/stderr.log
.tmp/cuda_safe_window_large_geometry_shadow_geometry_r2/stderr.log
.tmp/cuda_safe_window_large_geometry_shadow_geometry_r3/stderr.log
```

## 3-Run Medians

| Field | Median |
| --- | ---: |
| total_seconds | 12.7094 |
| sim_seconds | 10.7379 |
| sim_safe_workset_total_seconds | 4.06652 |
| sim_safe_workset_merge_seconds | 1.17357 |
| sim_region_scan_gpu_seconds | 2.47275 |
| sim_region_d2h_seconds | 0.603558 |

Geometry totals:

| Field | Median |
| --- | ---: |
| sim_safe_window_attempts | 515 |
| sim_safe_window_applied | 515 |
| sim_safe_window_exec_cells | 503,991,297 |
| sim_safe_window_raw_cells | 405,737,653 |
| sim_safe_window_coarsening_inflated_cells | 98,253,644 |
| sim_safe_window_inflation_ratio | 0.242161 |
| sim_safe_window_calls_inflation_gt_25pct | 167 |
| sim_safe_window_large_window_calls | 79 |
| sim_safe_window_large_window_inflation_cells | 72,050,911 |

Large-geometry shadow estimator:

| Field | Median |
| --- | ---: |
| sim_safe_window_large_geometry_shadow_enabled | 1 |
| sim_safe_window_large_geometry_shadow_calls | 204 |
| sim_safe_window_large_geometry_shadow_large_calls | 79 |
| sim_safe_window_large_geometry_shadow_threshold_raw_cells | 1,000,000 |
| sim_safe_window_large_geometry_shadow_threshold_inflation_pct | 25 |
| sim_safe_window_large_geometry_shadow_current_exec_cells | 403,057,802 |
| sim_safe_window_large_geometry_shadow_shadow_exec_cells | 318,729,080 |
| sim_safe_window_large_geometry_shadow_est_saved_cells | 84,328,722 |
| sim_safe_window_large_geometry_shadow_est_saved_ratio | 0.209222 |
| sim_safe_window_large_geometry_shadow_mismatches | 0 |
| sim_safe_window_large_geometry_shadow_fallbacks | 0 |
| sim_safe_window_large_geometry_shadow_estimator_only | 1 |

Derived:

```text
selected calls / attempts        = 204 / 515 = 39.61%
large calls / selected calls     = 79 / 204 = 38.73%
estimated saved / total inflated = 84,328,722 / 98,253,644 = 85.83%
selected current / total exec    = 403,057,802 / 503,991,297 = 79.97%
estimated saved / total exec     = 16.73%
shadow cells / selected current  = 79.08%
```

The estimator says the large/high-inflation selector captures most of the
inflated-cell opportunity. It does not say that raw/fine geometry is exact-safe.

## Boundary Checks

The runs reported:

```text
sim_safe_window_exact_fallbacks=0
sim_safe_window_fallbacks=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

No fine geometry real/default path, sparse_v2 default, region batching, or
safe-store/candidate replay change is included.

## Interpretation

The selected `204` calls cover `84.33M` of the `98.25M` inflated cells, so the
large-window / high-inflation selector is strong enough for a narrower exact
shadow follow-up.

But this PR is deliberately not that exact shadow. The existing fine-shadow
diagnostic has historically been mismatch-heavy, so a real geometry opt-in would
be premature.

## Decision

Current decision:

```text
selector signal: strong
estimated saved cells: high
exactness: not proven
recommended/default: no
next step: exact shadow on the selected large/high-inflation bucket
```

If an exact selected-bucket geometry shadow is still mismatch-heavy, pause
safe-window geometry real-path work and pivot to region kernel/cell-work
profiling or the `calc_score` side lane.
