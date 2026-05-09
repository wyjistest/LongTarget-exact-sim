# CUDA region deferred-count A/B characterization

Date: 2026-05-09

Base: `cuda-region-deferred-counts-validation`

This is a docs-only characterization of the existing single-request direct region
reducer with deferred counts. It does not default deferred counts and does not
change region dispatch.

## Context

PR #8 showed that deferred counts greatly reduce scalar count D2H and sync time,
but the small benchmark wall-clock result was not a clear win. PR #9 added
default-off validation telemetry:

```text
LONGTARGET_SIM_CUDA_REGION_DEFERRED_COUNTS_VALIDATE=1
```

That validation compares the packed deferred-count snapshot against scalar
event/run/candidate count copies.

## Modes

All runs enabled:

```text
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1
```

Modes:

```text
direct    no deferred counts
deferred  LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1
validate  deferred + LONGTARGET_SIM_CUDA_REGION_DEFERRED_COUNTS_VALIDATE=1
```

The small benchmark and sample were each run 3 times per mode. The matrix smoke
was run once per mode, but it did not exercise the single-request direct reducer
and is included only as a coverage note.

## Median timing

| workload | mode | runs | sim_seconds | total_seconds | region_d2h_seconds | count_d2h_seconds | snapshot_d2h_seconds | validate_calls | mismatches | validate_seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small | direct | 3 | 2.026860 | 4.070130 | 0.073756 | 0.068204 | 0.000000 | 0 | 0 | 0.000000 |
| small | deferred | 3 | 1.883810 | 3.953530 | 0.002701 | 0.001378 | 0.001378 | 0 | 0 | 0.000000 |
| small | validate | 3 | 2.010040 | 4.088550 | 0.002581 | 0.001334 | 0.001334 | 140 | 0 | 0.002270 |
| sample | direct | 3 | 12.814200 | 14.870100 | 0.722324 | 0.660430 | 0.000000 | 0 | 0 | 0.000000 |
| sample | deferred | 3 | 12.905500 | 15.184100 | 0.010137 | 0.005323 | 0.005323 | 0 | 0 | 0.000000 |
| sample | validate | 3 | 12.993000 | 15.033400 | 0.009928 | 0.005234 | 0.005234 | 515 | 0 | 0.008570 |
| matrix | direct | 1 | 45.530838 | 56.364922 | 2.390438 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| matrix | deferred | 1 | 46.037875 | 56.903179 | 2.835964 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |
| matrix | validate | 1 | 46.018958 | 56.732560 | 2.458829 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |

## Min/max timing

| workload | mode | sim_seconds min..max | total_seconds min..max | region_d2h_seconds min..max |
| --- | --- | ---: | ---: | ---: |
| small | direct | 1.862430 .. 7.526950 | 3.911230 .. 9.832880 | 0.072832 .. 0.075671 |
| small | deferred | 1.878890 .. 2.051760 | 3.934630 .. 4.325650 | 0.002579 .. 0.002712 |
| small | validate | 1.880430 .. 2.028770 | 3.943360 .. 4.274410 | 0.002545 .. 0.002668 |
| sample | direct | 12.688400 .. 12.916500 | 14.794300 .. 14.991800 | 0.706224 .. 0.723427 |
| sample | deferred | 12.727800 .. 13.116500 | 14.786900 .. 15.186400 | 0.009922 .. 0.010180 |
| sample | validate | 12.976800 .. 13.173900 | 15.009900 .. 15.228300 | 0.009801 .. 0.009937 |

The first small direct run was a clear wall-clock outlier (`sim_seconds=7.52695`)
while its D2H counters matched the other direct runs. The median is therefore
more useful than the average for this pass.

## Validation

Validation remained clean wherever the direct reducer was exercised:

| workload | mode | validate_calls | scalar_copies | snapshot_copies | total_mismatches | fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| small | validate | 140 | 420 | 140 | 0 | 0 |
| sample | validate | 515 | 1545 | 515 | 0 | 0 |

The matrix smoke passed in all modes but recorded `validate_calls=0`; the current
matrix workload did not cover the single-request direct reducer.

## Interpretation

1. Deferred counts consistently reduce scalar count D2H and region D2H when the
   single-request direct reducer is used. On the sample, median
   `sim_region_d2h_seconds` dropped from `0.722324` to `0.010137`.
2. The wall-clock result is not a stable win. In this run the sample median
   `sim_seconds` moved from `12.8142` direct to `12.9055` deferred, and median
   `total_seconds` moved from `14.8701` to `15.1841`.
3. Validation remained clean on the covered workloads, with zero event/run/
   candidate mismatches and zero validation fallbacks.
4. The small benchmark is noisy in wall-clock terms. Deferred counts lowered D2H
   counters, but the direct mode had one large cold/noise outlier and the
   validate mode's median total time was slightly above direct.
5. The current matrix smoke is not useful for deferred-count performance
   conclusions because it does not exercise the single-request direct reducer.

## Recommendation

Do not default deferred counts yet.

Deferred counts are correctness-gated and remain a useful opt-in candidate for
D2H/sync reduction, but this A/B pass does not show a stable wall-clock win on
the covered sample path. The next useful step is not defaulting; it is either:

```text
1. keep deferred counts as diagnostic/recommended opt-in only for targeted
   heavier workloads, or
2. optimize the remaining deferred-count overhead and rerun A/B, or
3. find/create a heavier direct-reduce workload that exercises the scalar count
   bottleneck without being dominated by safe-workset merge or unrelated CUDA
   stages.
```

If future A/B still shows D2H wins without wall-clock wins, the next mining
target should move away from deferred counts and back to broader region transfer
packing or safe-store upload reduction.
