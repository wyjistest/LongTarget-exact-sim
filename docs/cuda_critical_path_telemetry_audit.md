# CUDA critical-path telemetry audit

Date: 2026-05-09

Base: `cuda-region-deferred-counts-overhead-audit`

This is a docs-only critical-path and run-to-run variance audit. It does not add
an optimization, does not default deferred counts, and does not change region
dispatch, candidate/run/event ordering, safe-store behavior, planner authority,
validation, fallback, or CUDA kernels.

## Question

The deferred-count line showed a recurring pattern: a local D2H counter can move
strongly while `sim_seconds` does not move proportionally. PR #11 found no local
deferred-count overhead large enough to explain that gap.

This pass asks which existing CUDA SIM phases currently control end-to-end
wall-clock, and whether region D2H is a reliable next optimization target on
the covered workloads.

## Telemetry inventory

The existing benchmark fields were sufficient for this audit. No C++/CUDA
counter or script was added.

| Area | Existing fields |
| --- | --- |
| Global | `benchmark.total_seconds`, `benchmark.sim_seconds`, `benchmark.calc_score_seconds` |
| Initial scan | `benchmark.sim_initial_scan_seconds`, `sim_initial_scan_d2h_seconds`, `sim_initial_scan_cpu_merge_seconds`, `sim_initial_scan_cpu_merge_subtotal_seconds` |
| Initial materialize / sync | `benchmark.sim_initial_summary_result_materialize_seconds`, `sim_initial_frontier_sync_seconds`, `sim_materialize_seconds`, `sim_traceback_post_seconds` |
| Safe-workset | `benchmark.sim_safe_workset_total_seconds`, `sim_safe_workset_build_seconds`, `sim_safe_workset_merge_seconds`, safe-store erase/prune/upload split fields |
| Region | `benchmark.sim_region_scan_gpu_seconds`, `sim_region_d2h_seconds`, `sim_region_cpu_merge_seconds`, `sim_region_summary_bytes_d2h`, direct-reduce GPU/count/snapshot D2H fields |
| Validation / opt-in context | Deferred-count validation mismatch fields and safe-store shadow mismatch fields |

The branch still lacks a dedicated `sim_region_sync_wait_seconds` or global
critical-path overlap field. This audit therefore uses existing phase timers
instead of trying to infer overlap precisely.

## Modes and runs

Each workload was run five times per mode.

Modes:

```text
baseline  default stack mode, no direct reducer override
direct    LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1
deferred  direct + LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1
validate  deferred + LONGTARGET_SIM_CUDA_REGION_DEFERRED_COUNTS_VALIDATE=1
```

Direct, deferred, and validate runs also enabled:

```text
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1
```

Workloads:

```text
small   benchmark path: testDNA.fa vs H19.fa, two-stage prealign_cuda
sample  sample region-locate exactness path
```

Sample runs used unique `.tmp/cuda_critical_path_audit/<timestamp>/...` output
directories to avoid the known exactness-output collision.

## Phase medians

| workload | mode | sim | total | initial_scan | initial_d2h | materialize | frontier_sync | safe_workset_total | safe_workset_merge | region_gpu | region_d2h | region_cpu_merge | traceback_post |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small | baseline | 2.066690 | 4.107050 | 1.053540 | 0.217945 | 0.022008 | 0.003357 | 0.375599 | 0.078661 | 0.247388 | 0.065700 | 0.078661 | 0.000685 |
| small | direct | 1.876540 | 3.944050 | 1.045380 | 0.209760 | 0.021997 | 0.003231 | 0.346268 | 0.079900 | 0.222112 | 0.067379 | 0.079900 | 0.000690 |
| small | deferred | 1.854370 | 3.898560 | 1.031230 | 0.209000 | 0.021946 | 0.003137 | 0.343761 | 0.079139 | 0.217465 | 0.002616 | 0.079139 | 0.000664 |
| small | validate | 1.908230 | 3.956010 | 1.033760 | 0.217092 | 0.022067 | 0.003180 | 0.347731 | 0.079615 | 0.218494 | 0.002619 | 0.079615 | 0.000677 |
| sample | baseline | 13.442900 | 15.467000 | 8.538450 | 1.654310 | 0.330987 | 0.136256 | 4.415320 | 1.503130 | 2.483400 | 0.619353 | 1.503130 | 0.026914 |
| sample | direct | 13.655400 | 15.677000 | 8.866300 | 1.579060 | 0.328822 | 0.262724 | 4.334800 | 1.617980 | 2.340110 | 0.652757 | 1.617980 | 0.029096 |
| sample | deferred | 13.330200 | 15.572200 | 8.735650 | 1.669620 | 0.327953 | 0.197332 | 4.165260 | 1.498800 | 2.284410 | 0.010405 | 1.498800 | 0.027994 |
| sample | validate | 13.387100 | 15.419200 | 8.777420 | 1.642740 | 0.324316 | 0.154419 | 4.184550 | 1.452250 | 2.316870 | 0.010162 | 1.452250 | 0.027830 |

On the sample, deferred counts still remove most region D2H
(`0.652757s -> 0.010405s` versus direct). The end-to-end median improves only
`0.325200s` in `sim_seconds`, about half of the region D2H delta, and
`total_seconds` improves only `0.104800s`.

## Sample variance

| mode | field | median | min | max | max-min | cv % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | `sim_seconds` | 13.442900 | 12.701000 | 15.690700 | 2.989700 | 7.51 |
| baseline | `sim_initial_scan_seconds` | 8.538450 | 8.317560 | 9.718680 | 1.401120 | 5.65 |
| baseline | `sim_initial_scan_cpu_merge_seconds` | 5.008280 | 4.737310 | 6.017780 | 1.280470 | 8.65 |
| baseline | `sim_safe_workset_total_seconds` | 4.415320 | 4.048140 | 5.188970 | 1.140830 | 8.61 |
| baseline | `sim_safe_workset_merge_seconds` | 1.503130 | 1.319520 | 2.128140 | 0.808620 | 17.90 |
| baseline | `sim_region_d2h_seconds` | 0.619353 | 0.509656 | 0.633189 | 0.123533 | 7.67 |
| direct | `sim_seconds` | 13.655400 | 13.437100 | 13.696300 | 0.259200 | 0.67 |
| direct | `sim_initial_scan_seconds` | 8.866300 | 8.796290 | 8.911990 | 0.115700 | 0.43 |
| direct | `sim_initial_scan_d2h_seconds` | 1.579060 | 1.547340 | 1.668630 | 0.121290 | 3.05 |
| direct | `sim_initial_frontier_sync_seconds` | 0.262724 | 0.192958 | 0.325521 | 0.132563 | 18.58 |
| direct | `sim_safe_workset_total_seconds` | 4.334800 | 4.135830 | 4.449330 | 0.313500 | 2.35 |
| direct | `sim_region_d2h_seconds` | 0.652757 | 0.635951 | 0.664906 | 0.028955 | 1.66 |
| deferred | `sim_seconds` | 13.330200 | 13.093000 | 13.661200 | 0.568200 | 1.53 |
| deferred | `sim_initial_scan_seconds` | 8.735650 | 8.559390 | 8.883320 | 0.323930 | 1.37 |
| deferred | `sim_initial_scan_d2h_seconds` | 1.669620 | 1.656340 | 1.885170 | 0.228830 | 6.08 |
| deferred | `sim_initial_frontier_sync_seconds` | 0.197332 | 0.125996 | 0.305490 | 0.179494 | 30.40 |
| deferred | `sim_materialize_seconds` | 0.327953 | 0.320677 | 0.487312 | 0.166635 | 20.30 |
| deferred | `sim_traceback_post_seconds` | 0.027994 | 0.027134 | 0.200445 | 0.173311 | 87.57 |
| deferred | `sim_region_d2h_seconds` | 0.010405 | 0.010152 | 0.010445 | 0.000293 | 1.12 |
| validate | `sim_seconds` | 13.387100 | 12.949300 | 13.603500 | 0.654200 | 1.81 |
| validate | `sim_initial_scan_seconds` | 8.777420 | 8.424350 | 8.807800 | 0.383450 | 2.03 |
| validate | `sim_initial_scan_d2h_seconds` | 1.642740 | 1.635030 | 1.878860 | 0.243830 | 6.63 |
| validate | `sim_initial_frontier_sync_seconds` | 0.154419 | 0.097436 | 0.319633 | 0.222197 | 41.86 |
| validate | `sim_materialize_seconds` | 0.324316 | 0.318133 | 0.498758 | 0.180625 | 21.52 |
| validate | `sim_traceback_post_seconds` | 0.027830 | 0.025503 | 0.198375 | 0.172872 | 87.95 |
| validate | `sim_region_d2h_seconds` | 0.010162 | 0.010139 | 0.010274 | 0.000135 | 0.47 |

The direct-mode sample is relatively stable in this run, but the baseline has a
large outlier and the deferred/validate modes still show enough phase movement
outside region D2H to make sub-second wall-clock claims fragile.

## Deferred-count delta attribution

| field | small direct | small deferred | delta |
| --- | ---: | ---: | ---: |
| `sim_seconds` | 1.876540 | 1.854370 | -0.022170 |
| `total_seconds` | 3.944050 | 3.898560 | -0.045490 |
| `sim_region_d2h_seconds` | 0.067379 | 0.002616 | -0.064763 |
| `sim_region_single_request_direct_reduce_count_d2h_seconds` | 0.061922 | 0.001333 | -0.060589 |
| `sim_region_scan_gpu_seconds` | 0.222112 | 0.217465 | -0.004647 |
| `sim_safe_workset_total_seconds` | 0.346268 | 0.343761 | -0.002507 |
| `sim_initial_scan_seconds` | 1.045380 | 1.031230 | -0.014150 |

| field | sample direct | sample deferred | delta |
| --- | ---: | ---: | ---: |
| `sim_seconds` | 13.655400 | 13.330200 | -0.325200 |
| `total_seconds` | 15.677000 | 15.572200 | -0.104800 |
| `sim_region_d2h_seconds` | 0.652757 | 0.010405 | -0.642352 |
| `sim_region_single_request_direct_reduce_count_d2h_seconds` | 0.591262 | 0.005529 | -0.585733 |
| `sim_region_scan_gpu_seconds` | 2.340110 | 2.284410 | -0.055700 |
| `sim_region_cpu_merge_seconds` | 1.617980 | 1.498800 | -0.119180 |
| `sim_safe_workset_total_seconds` | 4.334800 | 4.165260 | -0.169540 |
| `sim_initial_scan_seconds` | 8.866300 | 8.735650 | -0.130650 |
| `sim_initial_scan_d2h_seconds` | 1.579060 | 1.669620 | +0.090560 |
| `sim_initial_summary_result_materialize_seconds` | 0.497870 | 0.535058 | +0.037188 |
| `sim_initial_frontier_sync_seconds` | 0.262724 | 0.197332 | -0.065392 |

The sample run shows a positive direct-to-deferred median delta this time, but
the wall-clock gain remains much smaller than the region D2H delta. That keeps
the PR #11 conclusion intact: deferred counts are correctness-gated and
D2H-positive, but not yet a default candidate.

## Validation / opt-in status

Validation stayed clean in all validate runs:

| workload | validate calls | total mismatches | fallbacks | validate seconds median |
| --- | ---: | ---: | ---: | ---: |
| small | 140 | 0 | 0 | 0.002304 |
| sample | 515 | 0 | 0 | 0.008749 |

Safe-store shadow stayed disabled by default in the benchmark gate. This audit
did not enable any new real path.

## Answers

| Question | Answer |
| --- | --- |
| Which fields move more than the deferred-count D2H saving? | In the sample direct/deferred medians, no single unrelated field moves more than the `0.642352s` region D2H drop. But run-to-run ranges in baseline `sim_seconds`, baseline initial scan, and baseline safe-workset merge exceed that scale, and deferred/validate materialize/traceback outliers remain large enough to destabilize small wall-clock claims. |
| Is region D2H likely on the end-to-end critical path? | Partially, but not cleanly. Removing `0.642352s` of sample region D2H produced only `0.325200s` median `sim_seconds` improvement and `0.104800s` median `total_seconds` improvement. |
| Are initial/materialize/frontier-sync fields too noisy to support small D2H decisions? | Yes for sub-second decisions on these workloads. Initial scan dominates the sample (`8.7s` median), and frontier/materialize/traceback variance can move enough to hide or exaggerate local D2H wins. |
| Is safe-store upload large enough to justify reduction work? | Not as the next standalone target. Sample safe-store upload median is around `0.05s`, much smaller than safe-store erase/prune/merge and smaller than observed run-to-run phase movement. |
| Is broader region transfer packing likely to affect wall-clock? | It may improve counters, but this audit does not prove it will move wall-clock. Region D2H can be reduced sharply while only part of the saving reaches `sim_seconds`. |
| What is the next best optimization target? | Improve or stabilize critical-path telemetry around initial scan/materialize/frontier sync first, or find a heavier workload where a target transfer is known to be on the end-to-end critical path. Do not start another transfer-only optimization from these data alone. |

## Decision

Pause transfer-only CUDA micro-optimizations on the covered workloads. The next
small PR should not default deferred counts, region packing, or safe-store
upload reduction. The better next step is one of:

```text
1. add narrowly scoped critical-path/overlap telemetry for initial scan,
   materialize, and frontier sync if a missing field is already local,
2. stabilize the sample benchmark harness enough to reduce run-to-run phase
   variance before using sub-second deltas for decisions,
3. find a heavier workload where region D2H or safe-store upload is proven to be
   on the end-to-end critical path, or
4. return to safe-store data-structure work only with a design that avoids the
   full-copy/full-index-rebuild compact path that already regressed locally.
```

Until then, deferred counts should remain default-off diagnostic/targeted opt-in
and region D2H packing should be treated as a counter-improvement candidate, not
as a proven wall-clock optimization.
