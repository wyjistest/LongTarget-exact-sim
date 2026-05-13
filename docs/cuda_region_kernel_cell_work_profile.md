# CUDA Region Kernel Cell-Work Profile

Base branch:

```text
cuda-safe-window-large-geometry-digest-taxonomy
```

Base commit:

```text
396944c
```

This is a telemetry and documentation PR. It does not change region dispatch,
safe-window planner authority, safe-window geometry, safe-store/candidate replay
semantics, runtime defaults, the clean frontier gate, or any `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.

## Goal

PR #44 showed that selected large/fine/raw safe-window geometry is not an
exact-safe path:

```text
selected_calls = 204
compared_calls = 204
digest_mismatches = 203
order_only_mismatch_calls = 0
canonical_digest_mismatches = 203
unordered_digest_mismatches = 203
value_mismatch_calls = 203
set_mismatch_calls = 203
```

That blocks a real large-window geometry path for now. This PR profiles the
current coarsened region work to decide whether `region_gpu` is mainly cell
processing, per-launch overhead, or another safe-workset component.

## Telemetry Added

Benchmark output now includes a region cell-work profile:

```text
sim_region_cell_work_profile_calls
sim_region_cell_work_profile_launches
sim_region_cell_work_profile_exec_cells
sim_region_cell_work_profile_raw_cells
sim_region_cell_work_profile_gpu_seconds
sim_region_cell_work_profile_cells_per_launch
sim_region_cell_work_profile_gpu_seconds_per_launch
sim_region_cell_work_profile_gpu_seconds_per_million_cells
sim_region_cell_work_profile_max_exec_cells
sim_region_cell_work_profile_max_gpu_seconds
sim_region_cell_work_profile_large_threshold_cells
sim_region_cell_work_profile_large_calls
sim_region_cell_work_profile_large_exec_cells
sim_region_cell_work_profile_large_raw_cells
sim_region_cell_work_profile_large_gpu_seconds
sim_region_cell_work_profile_bucket_le_100k_{calls,cells,gpu_seconds}
sim_region_cell_work_profile_bucket_100k_500k_{calls,cells,gpu_seconds}
sim_region_cell_work_profile_bucket_500k_1m_{calls,cells,gpu_seconds}
sim_region_cell_work_profile_bucket_gt_1m_{calls,cells,gpu_seconds}
```

The profile is recorded from the same CUDA region success paths that already
feed `sim_region_scan_gpu_seconds`. It is observational only and does not alter
dispatch, shape selection, or result authority.

## Mode

The sample run used the recommended safe-store GPU best path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
OUTPUT_SUBDIR=cuda_region_kernel_cell_work_profile_r1
./scripts/run_sample_exactness_cuda.sh
```

Run log:

```text
.tmp/cuda_region_kernel_cell_work_profile_r1/stderr.log
```

## Result

| Field | Value |
| --- | ---: |
| total_seconds | 13.2555 |
| sim_seconds | 11.2648 |
| sim_safe_workset_total_seconds | 4.08886 |
| sim_safe_workset_merge_seconds | 1.17764 |
| sim_region_scan_gpu_seconds | 2.51635 |
| sim_region_d2h_seconds | 0.600215 |
| sim_region_calls | 515 |
| sim_region_requests | 515 |
| sim_region_launches | 515 |
| sim_region_total_cells | 503,991,297 |

Cell-work profile:

| Field | Value |
| --- | ---: |
| sim_region_cell_work_profile_calls | 515 |
| sim_region_cell_work_profile_launches | 515 |
| sim_region_cell_work_profile_exec_cells | 503,991,297 |
| sim_region_cell_work_profile_raw_cells | 405,737,653 |
| sim_region_cell_work_profile_gpu_seconds | 2.51635 |
| sim_region_cell_work_profile_cells_per_launch | 978,624 |
| sim_region_cell_work_profile_gpu_seconds_per_launch | 0.00488613 |
| sim_region_cell_work_profile_gpu_seconds_per_million_cells | 0.00499285 |
| sim_region_cell_work_profile_max_exec_cells | 9,963,012 |
| sim_region_cell_work_profile_max_gpu_seconds | 0.172386 |
| sim_region_cell_work_profile_large_threshold_cells | 1,000,000 |
| sim_region_cell_work_profile_large_calls | 90 |
| sim_region_cell_work_profile_large_exec_cells | 369,400,286 |
| sim_region_cell_work_profile_large_raw_cells | 294,731,074 |
| sim_region_cell_work_profile_large_gpu_seconds | 1.05114 |

## Bucket Distribution

| Exec-cell bucket | Calls | Exec cells | GPU seconds | GPU seconds per M cells |
| --- | ---: | ---: | ---: | ---: |
| <= 100k | 104 | 4,717,406 | 0.12291 | 0.02605 |
| 100k-500k | 224 | 62,224,656 | 0.699258 | 0.01124 |
| 500k-1m | 97 | 67,648,949 | 0.643042 | 0.00951 |
| > 1m | 90 | 369,400,286 | 1.05114 | 0.00285 |

Derived:

```text
large calls (>1M exec cells) = 90 / 515 = 17.48%
large exec cells             = 369,400,286 / 503,991,297 = 73.29%
large raw cells              = 294,731,074 / 405,737,653 = 72.64%
large GPU seconds            = 1.05114 / 2.51635 = 41.77%

sub-1M calls                 = 425 / 515 = 82.52%
sub-1M exec cells            = 134,591,011 / 503,991,297 = 26.71%
sub-1M GPU seconds           = 1.46521 / 2.51635 = 58.23%

coarsening inflation         = 98,253,644 cells = 24.2161% of raw cells
```

## Interpretation

Large calls dominate cell count but do not dominate GPU time proportionally.
Calls above `1M` execution cells account for `73.29%` of execution cells but only
`41.77%` of profiled GPU seconds.

The smaller buckets show much higher GPU seconds per million cells:

```text
<=100k      0.02605 s / M cells
100k-500k   0.01124 s / M cells
500k-1m     0.00951 s / M cells
>1m         0.00285 s / M cells
```

This suggests `region_gpu` is not purely linear cell work. Fixed per-call or
per-launch overhead is still meaningful, even though region batching remains
blocked by the #35 scheduler shape result (`mergeable_calls=0`,
`est_launch_reduction=0`). Kernel cell processing still matters for the largest
calls, but optimizing only large-call cell work would not address most measured
GPU seconds in this sample.

## Answers

1. `region_gpu` is not dominated by a few very large calls only. Large calls are
   most of the cells, but sub-`1M` calls are most of the profiled GPU time.

2. GPU time does not scale linearly with execution cells. The per-million-cell
   cost is much higher for small and medium buckets.

3. Large-window calls are responsible for most region cells (`73.29%`) but less
   than half of profiled GPU time (`41.77%`).

4. Launch/per-call overhead is likely still meaningful. This does not revive
   true-batch, because existing shape telemetry reports zero conservative
   mergeability. It points to measuring launch overhead or kernel-stage cost
   under the current one-request-per-launch authority.

5. The next PR should be region launch/per-call overhead versus kernel-stage
   profiling. A CUDA Graph or launch-overhead characterization may be useful,
   but it must not route through true-batch or change dispatch semantics.

## Decision

Current decision:

```text
safe-window large/fine/raw geometry: paused
region batching / true-batch: paused
region D2H-only packing: paused
region kernel/cell-work: active characterization line
default/runtime behavior change: no
```

Recommended next direction:

```text
region launch/per-call overhead and kernel-stage profiling
```

If that profiling shows no stable target, pivot to `calc_score` side lane or
benchmark variance stabilization rather than changing geometry or region
dispatch authority.
