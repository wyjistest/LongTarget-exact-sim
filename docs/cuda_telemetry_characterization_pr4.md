# CUDA PR4 telemetry characterization

This note characterizes the stacked telemetry state after PR #4
(`cuda-telemetry-gapfill`). It uses telemetry-only counters from PR #3 and PR #4
to choose the next CUDA mining target. It does not change dispatch, grouping,
fallback behavior, validation, deep compare, planner authority, or CUDA kernels.

## Context

- Branch: `cuda-telemetry-gapfill`
- Base stack: PR #3 `cuda-locate-region-telemetry`
- Head commit used for collection: `4a311ea cuda: gap-fill safe-workset and region telemetry`
- Logs:
  - `.tmp/benchmark_telemetry/stderr.log`
  - `.tmp/sample_exactness_cuda_sim_region_locate/stderr.log`
- Commands used to collect/validate:
  - `make check-benchmark-telemetry`
  - `make check-sample-cuda-sim-region-locate`

## Telemetry sample

| Field | Benchmark path | Sample path |
| --- | ---: | ---: |
| `benchmark.sim_locate_batch_calls` | 0 | 0 |
| `benchmark.sim_locate_batch_requests` | 0 | 0 |
| `benchmark.sim_locate_batch_shared_input_requests` | 0 | 0 |
| `benchmark.sim_locate_batch_serial_fallback_requests` | 0 | 0 |
| `benchmark.sim_locate_batch_launches` | 0 | 0 |
| `benchmark.sim_safe_workset_build_seconds` | 0.0982849 | 0.368656 |
| `benchmark.sim_safe_workset_merge_seconds` | 0.147146 | 1.46053 |
| `benchmark.sim_safe_workset_total_seconds` | 0.807397 | 4.49217 |
| `benchmark.sim_safe_workset_passes` | 140 | 515 |
| `benchmark.sim_safe_workset_fallback_invalid_store` | 0 | 0 |
| `benchmark.sim_safe_workset_fallback_no_affected_start` | 0 | 0 |
| `benchmark.sim_safe_workset_fallback_no_workset` | 0 | 0 |
| `benchmark.sim_safe_workset_fallback_invalid_bands` | 0 | 0 |
| `benchmark.sim_safe_workset_fallback_scan_failure` | 0 | 0 |
| `benchmark.sim_safe_workset_fallback_shadow_mismatch` | 0 | 0 |
| `benchmark.sim_region_calls` | 140 | 515 |
| `benchmark.sim_region_requests` | 140 | 515 |
| `benchmark.sim_region_launches` | 140 | 515 |
| `benchmark.sim_region_batch_calls` | 0 | 0 |
| `benchmark.sim_region_batch_requests` | 0 | 0 |
| `benchmark.sim_region_serial_fallback_requests` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_telemetry_enabled` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_calls` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_mergeable_calls` | 0 | 0 |
| `benchmark.sim_region_scheduler_shape_est_launch_reduction` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_enabled` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_batches` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_requests` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_fused_requests` | 0 | 0 |
| `benchmark.sim_region_bucketed_true_batch_shadow_mismatches` | 0 | 0 |
| `benchmark.sim_region_event_bytes_d2h` | 0 | 0 |
| `benchmark.sim_region_summary_bytes_d2h` | 1764360 | 6670080 |
| `benchmark.sim_region_single_request_direct_reduce_enabled` | 0 | 0 |
| `benchmark.sim_region_single_request_direct_reduce_deferred_counts_enabled` | 0 | 0 |
| `benchmark.sim_region_single_request_direct_reduce_deferred_count_snapshot_d2h_seconds` | 0 | 0 |
| `benchmark.sim_region_scan_gpu_seconds` | 0.485736 | 2.53003 |
| `benchmark.sim_region_d2h_seconds` | 0.0911982 | 0.687118 |
| `benchmark.sim_initial_scan_seconds` | 1.12876 | 8.15796 |
| `benchmark.sim_locate_seconds` | 0.807397 | 4.49217 |
| `benchmark.calc_score_seconds` | 3.65743 | 3.66581 |
| `benchmark.sim_seconds` | 2.46378 | 13.0031 |
| `benchmark.total_seconds` | 6.54433 | 17.0024 |

No region-specific H2D byte counter was emitted in these two runs. The visible
region transfer signal is D2H summary bytes and region D2H time.

## Characterization

1. Locate batching is not characterized by these default runs. All
   `benchmark.sim_locate_batch_*` counters are zero, so these paths do not show
   whether locate is dominated by serial fallback requests or shared-input
   batches. This is evidence that the default sample does not exercise the PR #3
   locate batch path, not evidence that shared-input grouping has no value.

2. Region execution is one request per launch on both runs. The benchmark path
   reports `140 calls = 140 requests = 140 launches`; the sample path reports
   `515 calls = 515 requests = 515 launches`. This is the strongest signal in
   this pass.

3. Region batch counters are zero because batching is inactive on the default
   path. `benchmark.sim_region_bucketed_true_batch_enabled=0`, and the new PR #4
   split counters show `sim_region_batch_calls=0` and
   `sim_region_batch_requests=0`. This does not indicate a failed batch path; it
   confirms no region true-batch dispatch is active.

4. Scheduler shape counters are not yet identifying mergeable calls in the
   default runs because `benchmark.sim_region_scheduler_shape_telemetry_enabled=0`.
   The counters are present but disabled, so this pass cannot estimate
   mergeability without enabling diagnostic shape telemetry.

5. Safe-workset time is material enough to justify a shadow-only planner pass.
   On the sample path, `benchmark.sim_safe_workset_total_seconds=4.49217`, which
   matches `benchmark.sim_locate_seconds=4.49217`. Merge alone accounts for
   `1.46053` seconds. Fallback counters are all zero, so the path is stable
   enough for shadow comparison, but not enough evidence to trust a GPU planner
   as authority.

6. Region D2H remains visible. The sample path reports
   `benchmark.sim_region_summary_bytes_d2h=6670080` and
   `benchmark.sim_region_d2h_seconds=0.687118`; the benchmark path reports
   `1764360` bytes and `0.0911982` seconds. Event bytes are zero, so the current
   visible transfer cost is summary D2H, not raw event D2H.

## Recommended next mining target

The best next target is `region bucketed true-batch shadow`, preceded or paired
with enabling diagnostic scheduler shape telemetry for characterization. The
reason is direct: both runs show hundreds of region calls, requests, and launches
with a one-to-one ratio, while region batching is disabled.

Suggested ordering:

1. `cuda: add region scheduler shape characterization`:
   enable telemetry-only shape diagnostics and collect mergeability/rejection
   counters without changing dispatch.
2. `cuda: add region bucketed true-batch shadow`:
   compare bucketed launch geometry against the existing CPU/oracle authority,
   with real dispatch still disabled.
3. `cuda: add safe-window planner shadow telemetry`:
   justified by safe-workset total and merge seconds, but it should remain
   shadow-only with CPU builder authority.
4. `cuda: defer region reduce counts`:
   plausible because region summary D2H is visible, but it should follow shape
   and shadow work unless scalar-count D2H is shown to dominate.
5. `cuda: group locate batches by shared input signature`:
   deferred until a locate-heavy run exercises nonzero locate batch counters;
   first version must keep mandatory deep compare.
6. `cuda: reduce calc_score orientation scores on device`:
   viable as an independent side lane, but these PR #4 counters do not make it
   the main CUDA mining target.

## Explicitly out of scope

This pass intentionally does not port or recommend enabling:

- safe-window real path or GPU planner authority
- safe-window default changes
- region bucketed true-batch real dispatch
- shared-input locate grouping or upload caching
- fast locate real path
- validation, deep-compare, or input-check skips
- direct region reduce real path
- packed summary defaulting
- ordered_segmented_v3 defaulting
- DP/D2H overlap
- Layer 3 transducer composition
