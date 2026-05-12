# CUDA Region Best-Path Launch Geometry

Base branch:

```text
cuda-safe-workset-best-path-decomposition
```

Base commit:

```text
68f7b59
```

This is a characterization note only. It does not add optimization code, does
not change region dispatch, does not enable bucketed true-batch, does not change
safe-window planner authority, and does not change safe-store or candidate
replay semantics. Runtime defaults remain unchanged, the clean frontier gate
remains inactive, and no `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY` route is introduced.

## Goal

PR #34 showed that, under the recommended safe-store GPU best path,
safe-workset is the largest aggregate after initial scan and region scan is the
largest safe-workset slice:

```text
sim_safe_workset_total_seconds ~= 4.06s
sim_region_scan_gpu_seconds   ~= 2.48s
sim_safe_workset_merge_seconds ~= 1.14s
```

This pass asks whether the region path is a launch/batching opportunity, a
geometry/cell-work problem, or whether host merge should become the next target.

## Modes

All runs used the recommended safe-store GPU best path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

The new 3-run diagnostic sample also enabled telemetry-only diagnostics:

```bash
LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY=1
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
.tmp/cuda_region_best_path_launch_geometry_shape_r1/
.tmp/cuda_region_best_path_launch_geometry_shape_r2/
.tmp/cuda_region_best_path_launch_geometry_shape_r3/
```

The first diagnostic run had an initial-scan outlier
(`sim_initial_scan_seconds=13.325`), so the launch/shape counters below are the
important signal. Shape, rejection, geometry, and dispatch counters were
identical across all three runs.

## Median Timing

| Field | Median | Range |
| --- | ---: | ---: |
| total_seconds | 13.5543 | 6.8950 |
| sim_seconds | 11.5374 | 6.8471 |
| calc_score_seconds | 1.74783 | 0.02160 |
| sim_initial_scan_seconds | 6.89497 | 6.77629 |
| sim_initial_store_rebuild_seconds | 0.702887 | 0.292116 |
| sim_safe_workset_total_seconds | 4.31014 | 0.16960 |
| sim_safe_workset_build_seconds | 0.324365 | 0.000521 |
| sim_safe_workset_merge_seconds | 1.1944 | 0.01817 |
| sim_region_scan_gpu_seconds | 2.35594 | 0.15154 |
| sim_region_d2h_seconds | 0.627968 | 0.015616 |
| sim_region_summary_bytes_d2h | 6,670,080 | 0 |

The safe-workset split stayed close to #34. Region GPU remains the largest
safe-workset slice, followed by host merge. Region summary D2H is visible but
small in bytes.

## Dispatch Shape

| Field | Median |
| --- | ---: |
| sim_region_calls | 515 |
| sim_region_requests | 515 |
| sim_region_launches | 515 |
| sim_region_batch_calls | 0 |
| sim_region_batch_requests | 0 |
| sim_region_serial_fallback_requests | 0 |

Region still runs one request per launch. However, the per-launch work is not
tiny:

```text
execution cells per launch ~= 978,624
region GPU per launch      ~= 4.575 ms
region D2H per launch      ~= 1.219 ms
host merge per launch      ~= 2.319 ms
```

This makes a pure launch-overhead explanation unlikely. The region path has many
launches, but each launch also carries substantial cell work.

## Scheduler Shape Telemetry

| Field | Median |
| --- | ---: |
| sim_region_scheduler_shape_telemetry_enabled | 1 |
| sim_region_scheduler_shape_calls | 515 |
| sim_region_scheduler_shape_bands | 515 |
| sim_region_scheduler_shape_single_band_calls | 515 |
| sim_region_scheduler_shape_affected_starts | 187,473 |
| sim_region_scheduler_shape_cells | 503,991,297 |
| sim_region_scheduler_shape_max_band_rows | 2,339 |
| sim_region_scheduler_shape_max_band_cols | 4,364 |
| sim_region_scheduler_shape_mergeable_calls | 0 |
| sim_region_scheduler_shape_mergeable_cells | 0 |
| sim_region_scheduler_shape_est_launch_reduction | 0 |
| sim_region_scheduler_shape_rejected_running_min | 362 |
| sim_region_scheduler_shape_rejected_safe_store_epoch | 514 |
| sim_region_scheduler_shape_rejected_score_matrix | 0 |
| sim_region_scheduler_shape_rejected_filter | 503 |

The best-path run preserves the earlier shape-telemetry negative result:
consecutive region calls are not conservatively mergeable. The dominant blockers
are safe-store epoch changes and affected-start filter changes, with many
running-min changes as well. Score matrix compatibility is not the blocker.

Because `mergeable_calls=0` and `est_launch_reduction=0`, this PR does not
enable bucketed true-batch real or shadow runs. Those require the experimental
bucketed region path, and there is no positive mergeability signal to justify
paying that review/runtime cost in this step.

## Bucketed True-Batch Counters

| Field | Median |
| --- | ---: |
| sim_region_bucketed_true_batch_enabled | 0 |
| sim_region_bucketed_true_batch_batches | 0 |
| sim_region_bucketed_true_batch_requests | 0 |
| sim_region_bucketed_true_batch_fused_requests | 0 |
| sim_region_bucketed_true_batch_actual_cells | 0 |
| sim_region_bucketed_true_batch_padded_cells | 0 |
| sim_region_bucketed_true_batch_padding_cells | 0 |
| sim_region_bucketed_true_batch_rejected_padding | 0 |
| sim_region_bucketed_true_batch_shadow_mismatches | 0 |

Bucket padding acceptability was not measured on the production sample because
the semantic scheduler shape probe already reports zero mergeable calls. Padding
is a second-order question until safe-store epoch/filter/running-min
compatibility is addressed or a workload shows nonzero mergeability.

## Safe-Window Geometry

| Field | Median |
| --- | ---: |
| sim_safe_window_planner_mode | dense |
| sim_safe_window_exec_geometry | coarsened |
| sim_safe_window_attempts | 515 |
| sim_safe_window_selected_worksets | 515 |
| sim_safe_window_applied | 515 |
| sim_safe_window_exact_fallbacks | 0 |
| sim_safe_window_fallbacks | 0 |
| sim_safe_window_gpu_builder_fallbacks | 0 |
| sim_safe_window_count | 8,097 |
| sim_safe_window_affected_starts | 187,473 |
| sim_safe_window_coord_bytes_d2h | 13,089,344 |
| sim_safe_window_gpu_seconds | 0.0315797 |
| sim_safe_window_d2h_seconds | 0.0167095 |
| sim_safe_window_exec_bands | 515 |
| sim_safe_window_exec_cells | 503,991,297 |
| sim_safe_window_raw_cells | 405,737,653 |
| sim_safe_window_raw_max_window_cells | 5,039,004 |
| sim_safe_window_exec_max_band_cells | 9,963,012 |
| sim_safe_window_coarsening_inflated_cells | 98,253,644 |
| sim_safe_window_plan_bands | 515 |
| sim_safe_window_plan_cells | 503,991,297 |
| sim_safe_window_plan_fallbacks | 0 |

Coarsening inflates planned raw cells by about `24.22%`:

```text
raw cells       = 405,737,653
exec cells      = 503,991,297
inflated cells  = 98,253,644
```

This is a real geometry signal, but even a perfect removal of coarsening
inflation would target roughly a quarter of the `2.36s` region GPU slice, while
host merge is already about `1.19s`. Geometry remains a plausible later target,
but the current evidence does not support jumping straight to real batching.

## Answers

1. The `515` region launches are not shape-compatible under the current
   conservative consecutive-call criteria: `mergeable_calls=0`.

2. The top rejection reasons are safe-store epoch (`514`), affected-start filter
   (`503`), and running-min (`362`). Score matrix rejection is zero.

3. Estimated launch reduction is zero, so a bucketed true-batch PR is not
   justified from this workload evidence.

4. Bucketed true-batch padding was not evaluated because the semantic
   compatibility probe already blocks batching. Padding should be revisited only
   after nonzero mergeability appears or compatibility rules change.

5. Region GPU is not just many tiny launches. The sample has about `979k`
   execution cells and `4.6ms` GPU time per launch, so real cell work and
   coarsened geometry dominate over pure launch overhead.

6. `host_merge ~= 1.19s` is a better next target than batching on this evidence.
   It is smaller than region GPU, but it is a local, already-visible slice,
   whereas batching has zero conservative launch-reduction signal.

7. The next PR should be safe-workset host merge decomposition/reduction. Keep
   region batching paused until a workload or diagnostic shows nonzero
   mergeability. Safe-window geometry/coarsening can be a later side branch if
   host merge stalls.

## Boundary Checks

The collected runs reported:

```text
sim_initial_safe_store_gpu_precombine_prune_fallbacks=0
sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_order_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_digest_mismatches=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

No production authority changed in this characterization.
