# CUDA region deferred-count overhead audit

Date: 2026-05-09

Base: `cuda-region-deferred-counts-ab`

This is a docs-only follow-up to the deferred-count A/B characterization. It
does not default deferred counts, does not change region dispatch, and does not
change scalar-count, candidate, run, event, safe-store, planner, validation, or
fallback behavior.

## Question

PR #10 showed that deferred counts collapse direct-reduce count D2H, but the
sample median did not produce a stable wall-clock win:

```text
sample median, PR #10:
  direct   region_d2h_seconds = 0.722324, sim_seconds = 12.8142
  deferred region_d2h_seconds = 0.010137, sim_seconds = 12.9055
```

This audit asks where the saved D2H time went. The goal is to decide whether
there is a small local deferred-count overhead to optimize, or whether deferred
counts should remain a correctness-gated diagnostic opt-in for now.

## Inventory

The existing benchmark telemetry was sufficient for this pass. No code counters
or scripts were added.

| Area | Existing fields used |
| --- | --- |
| End-to-end timing | `benchmark.sim_seconds`, `benchmark.total_seconds` |
| Region transfer timing | `benchmark.sim_region_d2h_seconds`, `benchmark.sim_region_single_request_direct_reduce_count_d2h_seconds`, `benchmark.sim_region_single_request_direct_reduce_deferred_count_snapshot_d2h_seconds` |
| Direct-reduce GPU timing | `benchmark.sim_region_single_request_direct_reduce_gpu_seconds`, `dp_gpu_seconds`, `filter_reduce_gpu_seconds`, `compact_gpu_seconds` |
| Pipeline split | `benchmark.sim_region_single_request_direct_reduce_pipeline_*_seconds` with `LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1` |
| Host merge / safe-workset context | `benchmark.sim_region_cpu_merge_seconds`, `benchmark.sim_safe_workset_total_seconds`, `benchmark.sim_safe_workset_merge_seconds` |
| Validation context | `benchmark.sim_region_deferred_count_validate_seconds`, mismatch counters, scalar/snapshot copy counters |

There is no separate `sim_region_sync_wait_seconds` or
`sim_region_cpu_finalize_seconds` field on this branch. The closest host-side
region field is `sim_region_cpu_merge_seconds`.

## Modes

All runs enabled the single-request direct reducer and pipeline telemetry:

```text
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1
```

Modes:

```text
direct    no deferred counts
deferred  LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1
validate  deferred + LONGTARGET_SIM_CUDA_REGION_DEFERRED_COUNTS_VALIDATE=1
```

The small benchmark and sample region-locate exactness path were each run three
times per mode. Sample runs used unique `.tmp/deferred_counts_overhead_audit/*`
output subdirectories to avoid the known sample-output collision when exactness
jobs run concurrently.

## Median overhead table

| workload | mode | sim | total | region_d2h | count_d2h | snapshot_d2h | direct_gpu | cpu_merge | safe_workset_total | validation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small | direct | 1.999470 | 4.039760 | 0.071033 | 0.065516 | 0.000000 | 0.223531 | 0.078821 | 0.349473 | 0.000000 |
| small | deferred | 1.892200 | 3.912520 | 0.002606 | 0.001329 | 0.001329 | 0.219061 | 0.078054 | 0.348927 | 0.000000 |
| small | validate | 1.955270 | 4.006300 | 0.002621 | 0.001360 | 0.001360 | 0.219268 | 0.078774 | 0.347060 | 0.002296 |
| sample | direct | 12.820500 | 14.823700 | 0.693458 | 0.632237 | 0.000000 | 2.311050 | 1.342500 | 4.121360 | 0.000000 |
| sample | deferred | 13.118100 | 15.287400 | 0.010033 | 0.005376 | 0.005376 | 2.270040 | 1.321010 | 3.990580 | 0.000000 |
| sample | validate | 13.018000 | 15.051600 | 0.009852 | 0.005301 | 0.005301 | 2.305860 | 1.366460 | 4.037520 | 0.008595 |

## Direct-reduce pipeline split

| workload | mode | metadata_h2d | diag_gpu | event_count_d2h | run_count_d2h | count_snapshot_d2h | accounted_gpu | unaccounted_gpu |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small | direct | 0.003045 | 0.205332 | 0.064702 | 0.000790 | 0.000000 | 0.219363 | 0.004144 |
| small | deferred | 0.002937 | 0.204109 | 0.000000 | 0.000000 | 0.001329 | 0.218256 | 0.000805 |
| small | validate | 0.003072 | 0.204720 | 0.000000 | 0.000000 | 0.001360 | 0.218493 | 0.000775 |
| sample | direct | 0.039361 | 2.137930 | 0.629143 | 0.003034 | 0.000000 | 2.295310 | 0.015773 |
| sample | deferred | 0.039240 | 2.128400 | 0.000000 | 0.000000 | 0.005376 | 2.267150 | 0.002932 |
| sample | validate | 0.038946 | 2.163000 | 0.000000 | 0.000000 | 0.005301 | 2.302960 | 0.002938 |

The direct-reduce split does not show a local deferred-count penalty large
enough to explain the sample wall-clock regression. On the sample median,
deferred counts reduced direct count D2H by `0.626861s`, while direct-reduce GPU
time, CPU merge time, and safe-workset total time also moved slightly downward.

## Broader timing deltas

The sample regression appears in unrelated or less-local stages, not in the
deferred-count region split.

| field | sample direct | sample deferred | deferred - direct |
| --- | ---: | ---: | ---: |
| `sim_seconds` | 12.820500 | 13.118100 | +0.297600 |
| `total_seconds` | 14.823700 | 15.287400 | +0.463700 |
| `sim_region_d2h_seconds` | 0.693458 | 0.010033 | -0.683425 |
| `sim_region_single_request_direct_reduce_gpu_seconds` | 2.311050 | 2.270040 | -0.041010 |
| `sim_region_cpu_merge_seconds` | 1.342500 | 1.321010 | -0.021490 |
| `sim_safe_workset_total_seconds` | 4.121360 | 3.990580 | -0.130780 |
| `sim_initial_scan_seconds` | 8.281290 | 8.571670 | +0.290380 |
| `sim_initial_scan_d2h_seconds` | 1.667270 | 1.885470 | +0.218200 |
| `sim_materialize_seconds` | 0.315231 | 0.453086 | +0.137855 |
| `sim_traceback_post_seconds` | 0.024985 | 0.172392 | +0.147407 |
| `sim_initial_summary_result_materialize_seconds` | 0.528342 | 0.601255 | +0.072913 |
| `sim_initial_frontier_sync_seconds` | 0.207068 | 0.274866 | +0.067798 |

Those larger positive deltas are not part of the direct-region deferred-count
path. They also do not remain consistent in validation mode: for example,
`sim_materialize_seconds` and `sim_traceback_post_seconds` return near direct
levels while validation still preserves the low region D2H time. This points to
run-to-run timing noise or a broader unexposed critical-path shift, not a clear
local deferred-count overhead.

## Validation

Validation remained clean on the covered direct+deferred workloads.

| workload | validate_calls | scalar_copies | snapshot_copies | total_mismatches | fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: |
| small | 140 | 420 | 140 | 0 | 0 |
| sample | 515 | 1545 | 515 | 0 | 0 |

Validation timing is intentionally excluded from production conclusions. It
adds extra scalar/snapshot reads for comparison and is only a diagnostic gate.

## Answers

| Question | Answer |
| --- | --- |
| Is deferred adding extra GPU kernel/reduce time? | Not in this pass. Sample direct-reduce GPU median fell from `2.311050s` to `2.270040s` with deferred counts. |
| Is deferred adding extra sync/wait time? | The exposed region D2H and count-D2H fields drop sharply. There is no separate sync-wait field on this branch, so any remaining wait would need broader critical-path telemetry to isolate. |
| Is D2H no longer on the critical path? | The data is consistent with that possibility. Removing about `0.68s` of region D2H did not lower sample `sim_seconds`, and unrelated initial/materialize/post fields moved more than the region saving. |
| Is sample wall-clock dominated by other stages? | Yes. The sample has multi-second initial scan and safe-workset budgets, and their run-to-run movement is large enough to hide the region-count D2H win in this 3-run pass. |
| Is there a small local overhead to optimize? | No clear local deferred-count overhead is visible. The deferred path replaces scalar count D2H with one packed snapshot per request and does not show a compensating GPU or host-merge penalty. |
| Should deferred counts be defaulted? | No. They are correctness-gated and reduce D2H, but they still do not produce a stable end-to-end win on the covered sample path. |

## Decision

Keep deferred counts default-off. Treat them as a correctness-gated diagnostic
or targeted opt-in, not a default candidate.

This audit does not justify a code optimization PR. The saved D2H time did not
turn into a stable wall-clock win, and the exposed local deferred-count fields
do not identify a small overhead to fix. The next useful step should be one of:

```text
1. pause deferred counts until a heavier direct-reduce workload is available,
2. add broader critical-path telemetry only if needed for another optimization,
3. pivot to broader region transfer packing / summary layout, or
4. pivot to safe-store upload reduction.
```

If deferred counts are revisited, the benchmark should use a heavier workload
where direct-reduce count D2H is known to sit on the end-to-end critical path.
