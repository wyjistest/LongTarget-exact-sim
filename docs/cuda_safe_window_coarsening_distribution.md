# CUDA Safe-Window Coarsening Distribution

Base branch:

```text
cuda-safe-workset-deferred-index-ab
```

Base commit:

```text
19dd3b3
```

This is a telemetry and characterization PR. It does not change safe-window
planner authority, region dispatch, safe-store/candidate replay semantics,
runtime defaults, the clean frontier gate, or any `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.

## Goal

PR #35 showed that region batching is not structurally available under the
safe-store GPU best path:

```text
region calls / launches = 515 / 515
mergeable_calls = 0
est_launch_reduction = 0
```

The same run reported safe-window coarsening inflation of about `98M` cells
(`24.22%` raw-cell inflation). This PR adds telemetry to understand whether that
inflation is concentrated in a few calls, in small windows, or in large windows.

## Telemetry Added

The existing `LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1` diagnostic
now also records:

```text
sim_safe_window_geometry_calls
sim_safe_window_inflation_ratio
sim_safe_window_max_inflated_cells
sim_safe_window_calls_inflation_gt_10pct
sim_safe_window_calls_inflation_gt_25pct
sim_safe_window_calls_inflation_gt_50pct
sim_safe_window_small_window_raw_cell_threshold
sim_safe_window_small_window_calls
sim_safe_window_small_window_inflation_cells
sim_safe_window_large_window_calls
sim_safe_window_large_window_inflation_cells
sim_safe_window_top_inflated_call_{1,2,3}_{raw,exec,inflated}_cells
```

The small/large split uses raw planned cells:

```text
small window: raw cells <= 1,000,000
large window: raw cells > 1,000,000
```

These counters are diagnostic only. They are emitted as zero when geometry
telemetry is not enabled.

## Mode

All sample runs used the recommended safe-store GPU best path plus geometry
telemetry:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
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
.tmp/cuda_safe_window_coarsening_distribution_r1/stderr.log
.tmp/cuda_safe_window_coarsening_distribution_r2/stderr.log
.tmp/cuda_safe_window_coarsening_distribution_r3/stderr.log
```

## 3-Run Medians

| Field | Median |
| --- | ---: |
| total_seconds | 13.1631 |
| sim_seconds | 10.9949 |
| sim_initial_scan_seconds | 6.66622 |
| sim_safe_workset_total_seconds | 4.02094 |
| sim_safe_workset_build_seconds | 0.320441 |
| sim_safe_workset_merge_seconds | 1.14402 |
| sim_region_scan_gpu_seconds | 2.49303 |
| sim_region_d2h_seconds | 0.64716 |
| sim_region_calls | 515 |
| sim_region_launches | 515 |

The region path is still one request per launch, and region GPU remains the
largest safe-workset slice.

## Coarsening Totals

The geometry counters were identical across all three sample runs:

| Field | Median |
| --- | ---: |
| sim_safe_window_geometry_calls | 515 |
| sim_safe_window_attempts | 515 |
| sim_safe_window_applied | 515 |
| sim_safe_window_count | 8,097 |
| sim_safe_window_raw_cells | 405,737,653 |
| sim_safe_window_exec_cells | 503,991,297 |
| sim_safe_window_coarsening_inflated_cells | 98,253,644 |
| sim_safe_window_inflation_ratio | 0.242161 |
| sim_safe_window_raw_max_window_cells | 5,039,004 |
| sim_safe_window_exec_max_band_cells | 9,963,012 |
| sim_safe_window_max_inflated_cells | 2,414,722 |

Derived:

```text
inflated / raw  = 24.2161%
inflated / exec = 19.4951%
avg raw cells per geometry call      ~= 787,840
avg inflated cells per geometry call ~= 190,784
avg exec cells per region launch     ~= 978,624
```

## Distribution

| Field | Median |
| --- | ---: |
| sim_safe_window_calls_inflation_gt_10pct | 421 |
| sim_safe_window_calls_inflation_gt_25pct | 167 |
| sim_safe_window_calls_inflation_gt_50pct | 17 |
| sim_safe_window_small_window_raw_cell_threshold | 1,000,000 |
| sim_safe_window_small_window_calls | 436 |
| sim_safe_window_small_window_inflation_cells | 26,202,733 |
| sim_safe_window_large_window_calls | 79 |
| sim_safe_window_large_window_inflation_cells | 72,050,911 |

The large-window bucket is only `79 / 515` calls (`15.34%`) but contributes
`72,050,911 / 98,253,644` inflated cells (`73.33%`). Small windows are most
calls, but only `26.67%` of inflated cells.

The top individual inflated calls were:

| Rank | raw cells | exec cells | inflated cells | share of total inflated |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 6,870,578 | 9,285,300 | 2,414,722 | 2.46% |
| 2 | 6,566,409 | 8,974,914 | 2,408,505 | 2.45% |
| 3 | 6,779,950 | 8,979,048 | 2,199,098 | 2.24% |

Top 3 calls together explain only `7.15%` of inflated cells. The signal is not a
few pathological calls; it is broader large-window coarsening.

## Correctness And Boundary

The sampled runs reported:

```text
sim_safe_window_exact_fallbacks=0
sim_safe_window_fallbacks=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

This PR does not enable fine geometry, sparse_v2 real/default behavior, region
batching, or any safe-window planner authority change.

## Answers

1. Coarsening inflation is not concentrated in a tiny number of calls. The top
   3 inflated calls explain only `7.15%` of inflated cells.

2. Large windows dominate inflated cells. Calls with raw cells above `1M`
   account for only `15.34%` of geometry calls but `73.33%` of inflated cells.

3. A threshold-based shadow strategy is plausible, but the threshold should be
   broad large-window/high-inflation selection, not top-N call special-casing.
   For example, a future shadow could target raw cells `> 1M` or inflation
   `> 25%`.

4. The next PR should be a safe-window geometry shadow for high-inflation /
   large-window calls. It should still keep coarsened execution as authority and
   compare any alternative geometry against the existing exact-safe result.

5. Do not make fine geometry real/default from this evidence. Earlier
   fine-shadow runs had high mismatch counts, so the next step must remain
   shadow/diagnostic.

## Decision

Current decision:

```text
region batching: no structural opportunity
deferred-index: exact-clean but not a recommended opt-in
coarsening distribution: large-window bucket dominates inflation
next line: high-inflation safe-window geometry shadow
default/runtime behavior change: no
```

If high-inflation geometry shadow is still mismatch-heavy or does not estimate a
material region GPU reduction, pause geometry and move to the `calc_score` side
lane.
