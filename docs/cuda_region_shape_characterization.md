# CUDA region scheduler shape characterization

This note characterizes existing region scheduler shape telemetry on top of PR
#4 (`cuda-telemetry-gapfill`). It answers whether the current one-request region
launches are conservatively mergeable by scheduler shape. This is diagnostic
only: no dispatch, bucketization, planner authority, validation, or CUDA kernel
behavior changes are made.

## Context

- Branch: `cuda-region-shape-characterization`
- Base stack: PR #4 `cuda-telemetry-gapfill`
- Collection env:
  - `LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY=1`
- Commands:
  - `LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY=1 make check-benchmark-telemetry`
  - `LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY=1 make check-sample-cuda-sim-region-locate`
- Logs:
  - `.tmp/benchmark_telemetry/stderr.log`
  - `.tmp/sample_exactness_cuda_sim_region_locate/stderr.log`

The env is already documented as telemetry-only. Existing benchmark output also
already includes the shape counters, so no C++ or script changes were needed.

## Shape telemetry

| Field | Benchmark path | Sample path |
| --- | ---: | ---: |
| `benchmark.sim_region_calls` | 140 | 515 |
| `benchmark.sim_region_requests` | 140 | 515 |
| `benchmark.sim_region_launches` | 140 | 515 |
| `benchmark.sim_region_scheduler_shape_telemetry_enabled` | 1 | 1 |
| `benchmark.sim_region_scheduler_shape_calls` | 140 | 515 |
| `benchmark.sim_region_scheduler_shape_bands` | 140 | 515 |
| `benchmark.sim_region_scheduler_shape_single_band_calls` | 140 | 515 |
| `benchmark.sim_region_scheduler_shape_affected_starts` | 49369 | 187473 |
| `benchmark.sim_region_scheduler_shape_cells` | 12283040 | 503991297 |
| `benchmark.sim_region_scheduler_shape_max_band_rows` | 793 | 2339 |
| `benchmark.sim_region_scheduler_shape_max_band_cols` | 400 | 4364 |
| `benchmark.sim_region_scheduler_shape_mergeable_calls` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_mergeable_cells` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_est_launch_reduction` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_rejected_running_min` | 130 | 362 |
| `benchmark.sim_region_scheduler_shape_rejected_safe_store_epoch` | 139 | 514 |
| `benchmark.sim_region_scheduler_shape_rejected_score_matrix` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_rejected_filter` | 139 | 503 |
| `benchmark.sim_region_bucketed_true_batch_enabled` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_batches` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_requests` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_fused_requests` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_shadow_mismatches` | 0 | 0 |
| `benchmark.sim_safe_workset_total_seconds` | 0.408363 | 4.88425 |
| `benchmark.sim_safe_workset_merge_seconds` | 0.0805924 | 1.42879 |
| `benchmark.sim_region_summary_bytes_d2h` | 1764360 | 6670080 |
| `benchmark.sim_region_d2h_seconds` | 0.063598 | 0.681867 |
| `benchmark.sim_region_scan_gpu_seconds` | 0.247965 | 2.69751 |
| `benchmark.sim_locate_seconds` | 0.408363 | 4.88425 |
| `benchmark.sim_seconds` | 1.99943 | 19.2036 |
| `benchmark.total_seconds` | 4.084 | 21.302 |

## Interpretation

The current sample does not justify region bucketed true-batch shadow as the
immediate next PR. The default and sample paths still show one request per region
launch, but the conservative scheduler shape probe reports zero mergeable calls
and zero estimated launch reduction.

The blocker is not score-matrix compatibility. It is per-call state and filter
compatibility:

- Benchmark path: `139` safe-store epoch rejects and `139` filter rejects across
  `140` shape calls; `130` running-min rejects.
- Sample path: `514` safe-store epoch rejects and `503` filter rejects across
  `515` shape calls; `362` running-min rejects.

That means a naive consecutive-call bucket/merge pass would not reduce launches
on these runs under the current exact-safe compatibility rules.

## Answers

1. Many region calls are not shape-compatible under the current conservative
   criteria. `mergeable_calls=0` on both runs.
2. Estimated launch reduction is `0` on both runs.
3. Region bucketed true-batch shadow is not justified as the immediate next
   mining PR from this evidence. It may become useful after the safe-store/filter
   compatibility blockers are better understood or if a different workload shows
   positive mergeability.
4. Rejection counters point to safe-store epoch and affected-start filter changes
   as the main blockers; running-min changes also reject many consecutive calls.
5. Safe-window planner shadow should move ahead of bucketed true-batch shadow for
   this stack because safe-workset time is material and shape mergeability is
   currently zero.
6. Direct region reduce/deferred counts should remain deferred. Region summary
   D2H is visible, but the next region batching step lacks positive mergeability
   evidence, and direct reduce is behavior-changing enough to require a separate
   shadow/diagnostic path.

## Recommendation

Next mining target: `cuda: add safe-window planner shadow telemetry`.

Keep the next PR shadow-only: CPU builder and existing dispatch remain
authoritative, and GPU planner output should be compared through digest/count or
builder comparison telemetry before any real path is trusted.

Deferred:

- `cuda: add region bucketed true-batch shadow`: wait for positive shape
  mergeability or a targeted workload showing mergeable calls.
- `cuda: defer region reduce counts`: still plausible because summary D2H is
  visible, but not the next region scheduling bottleneck based on this pass.
- `cuda: group locate batches by shared input signature`: still lacks nonzero
  locate batch evidence from the default/sample runs.

## Out of scope

This pass intentionally does not enable or implement:

- region bucketed true-batch real dispatch
- new region bucketization behavior
- safe-window real path or GPU planner authority
- safe-window default changes
- locate shared-input grouping or upload caching
- validation, deep-compare, or input-check skips
- direct region reduce or deferred counts real paths
- packed summary defaulting
- ordered_segmented_v3 defaulting
- DP/D2H overlap
- Layer 3 transducer composition
