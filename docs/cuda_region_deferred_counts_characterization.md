# CUDA region deferred-count characterization

This note characterizes existing direct-region-reduce and deferred-count
telemetry on top of `cuda-safe-store-shadow-order-validation`. It does not add a
new direct-reduce path, does not default deferred counts, and does not change
region dispatch, validation, fallback, safe-store behavior, or CUDA kernels.

## Context

- Branch: `cuda-region-deferred-counts-characterization`
- Base stack: `cuda-safe-store-shadow-order-validation`
- Existing direct reducer knob:
  `LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1`
- Existing deferred-count knob:
  `LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1`
- Existing pipeline telemetry knob:
  `LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1`

Recent safe-store work showed that the naive host compact merge experiment is
exact but slower because full snapshot copy, publish copy, full index rebuild,
and compact prune dominate the intended erase/prune savings. This pass asks
whether existing direct region reduce / deferred counts expose a smaller,
better-scoped D2H/sync opportunity.

## Inventory

| Area | Existing knobs / keys | Action |
| --- | --- | --- |
| direct reduce activation | `LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1`, `benchmark.sim_region_single_request_direct_reduce_enabled` | documented and collected |
| deferred counts | `LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1`, `benchmark.sim_region_single_request_direct_reduce_deferred_counts_enabled` | documented and collected |
| pipeline telemetry | `LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1`, `benchmark.sim_region_single_request_direct_reduce_pipeline_telemetry_enabled` | documented and collected |
| scalar count D2H | `benchmark.sim_region_single_request_direct_reduce_count_d2h_seconds`, `candidate_count_d2h_seconds`, pipeline event/run/count-snapshot D2H splits | documented and collected |
| bulk D2H bytes | `benchmark.sim_region_summary_bytes_d2h`, `benchmark.sim_region_event_bytes_d2h` | documented and collected |
| shape / activity | direct-reduce attempts, successes, candidates, events, run summaries, affected starts, reduce work items | documented and collected |
| pipeline launches | event/run count launches, candidate prefix/compact launches, count snapshot launches | documented and collected |

The existing telemetry was sufficient for this characterization. No code or
script changes were needed.

## Commands

Baseline:

```bash
make build-cuda
make check-benchmark-telemetry
make check-sample-cuda-sim-region-locate
```

Small benchmark A/B:

```bash
LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_TWO_STAGE=1 \
LONGTARGET_PREFILTER_BACKEND=prealign_cuda \
./longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/region_deferred_counts/small_default_out

LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 \
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1 \
LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_TWO_STAGE=1 \
LONGTARGET_PREFILTER_BACKEND=prealign_cuda \
./longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/region_deferred_counts/small_direct_out

LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1 \
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1 \
LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_TWO_STAGE=1 \
LONGTARGET_PREFILTER_BACKEND=prealign_cuda \
./longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/region_deferred_counts/small_direct_deferred_out
```

Sample A/B used `scripts/run_sample_exactness_cuda.sh` with the same three
runtime modes and distinct `OUTPUT_SUBDIR` values:

```bash
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=region_deferred_counts_sample_default \
TARGET="$(pwd)/longtarget_cuda" \
./scripts/run_sample_exactness_cuda.sh

LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 \
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=region_deferred_counts_sample_direct \
TARGET="$(pwd)/longtarget_cuda" \
./scripts/run_sample_exactness_cuda.sh

LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1 \
LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=region_deferred_counts_sample_direct_deferred \
TARGET="$(pwd)/longtarget_cuda" \
./scripts/run_sample_exactness_cuda.sh
```

## D2H and Count Telemetry

| Field | Small default | Small direct | Small direct+deferred | Sample default | Sample direct | Sample direct+deferred |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sim_region_d2h_seconds` | 0.0646785 | 0.0746691 | 0.00265864 | 0.61312 | 0.703961 | 0.00998138 |
| `sim_region_summary_bytes_d2h` | 1764360 | 1764360 | 1764360 | 6670080 | 6670080 | 6670080 |
| `sim_region_event_bytes_d2h` | 0 | 0 | 0 | 0 | 0 | 0 |
| direct attempts / successes | 0 / 0 | 140 / 140 | 140 / 140 | 0 / 0 | 515 / 515 | 515 / 515 |
| direct fallbacks / overflows | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| direct candidates | 0 | 49010 | 49010 | 0 | 185280 | 185280 |
| direct events | 0 | 4018664 | 4018664 | 0 | 88433400 | 88433400 |
| direct run summaries | 0 | 926732 | 926732 | 0 | 9026574 | 9026574 |
| direct affected starts | 0 | 49369 | 49369 | 0 | 187473 | 187473 |
| direct reduce work items | 0 | 458315335 | 458315335 | 0 | 18133568718 | 18133568718 |
| `count_d2h_seconds` | 0 | 0.0691129 | 0.00136366 | 0 | 0.642326 | 0.00531013 |
| `candidate_count_d2h_seconds` | 0 | 0.00427799 | 0 | 0 | 0.0569171 | 0 |
| `deferred_count_snapshot_d2h_seconds` | 0 | 0 | 0.00136366 | 0 | 0 | 0.00531013 |
| pipeline event-count D2H seconds | 0 | 0.0683186 | 0 | 0 | 0.639201 | 0 |
| pipeline run-count D2H seconds | 0 | 0.000783371 | 0 | 0 | 0.00308081 | 0 |
| pipeline count-snapshot D2H seconds | 0 | 0 | 0.00136366 | 0 | 0 | 0.00531013 |
| scalar count copy estimate | 0 | 420 | 140 | 0 | 1545 | 515 |
| estimated scalar copy reduction | 0 | baseline | 280 | 0 | baseline | 1030 |
| estimated scalar count bytes | 0 | 1680 | 1680 | 0 | 6180 | 6180 |
| estimated sync points avoided | 0 | baseline | 280 | 0 | baseline | 1030 |

The scalar copy estimate treats the non-deferred direct path as three scalar
D2H count copies per request: event count, run count, and candidate count.
Deferred counts replace those with one packed three-int snapshot copy per
request. The byte count is the same three `int` values per request either way;
the expected win is fewer synchronization points, not fewer scalar bytes.

## Timing

| Field | Small default | Small direct | Small direct+deferred | Sample default | Sample direct | Sample direct+deferred |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sim_region_scan_gpu_seconds` | 0.359239 | 0.225506 | 0.376346 | 2.35079 | 2.31076 | 2.31619 |
| direct GPU seconds | 0 | 0.225506 | 0.376346 | 0 | 2.31076 | 2.31619 |
| direct DP GPU seconds | 0 | 0.216931 | 0.371474 | 0 | 2.23768 | 2.26017 |
| filter-reduce GPU seconds | 0 | 0.00206016 | 0.00192672 | 0 | 0.0485182 | 0.0452187 |
| compact GPU seconds | 0 | 0.0026327 | 0.00241446 | 0 | 0.00960397 | 0.00885898 |
| accounted GPU seconds | 0 | 0.221377 | 0.375543 | 0 | 2.29489 | 2.31328 |
| unaccounted GPU seconds | 0 | 0.00412909 | 0.000802372 | 0 | 0.0158632 | 0.00290739 |
| `sim_safe_workset_merge_seconds` | n/a | n/a | n/a | 1.34437 | 1.34439 | 1.35823 |
| `sim_safe_workset_total_seconds` | n/a | n/a | n/a | 4.10145 | 4.03254 | 4.06919 |
| `sim_seconds` | 7.89018 | 1.97076 | 2.03393 | 12.7087 | 12.8338 | 12.642 |
| `total_seconds` | 9.99887 | 4.01632 | 4.31627 | 14.8256 | 15.0823 | 14.6836 |

Single-run timing is noisy, but the count-D2H direction is clear:
deferred counts collapse scalar count D2H time on both paths. The performance
impact differs by workload.

On the small benchmark, deferred counts reduce D2H time but add enough GPU/DP
time that `sim_seconds` is slightly worse than direct reduce without deferred
counts. On the sample path, deferred counts reduce D2H time from about `0.704s`
to about `0.010s`, while GPU time stays close to the direct path. That sample
run shows a modest positive `sim_seconds` / `total_seconds` signal relative to
both default and non-deferred direct reduce.

## Decision

| Question | Answer |
| --- | --- |
| Are region D2H costs dominated by scalar count syncs or bulk summaries? | In the direct reducer, scalar count syncs dominate measured D2H time. Bulk summary bytes remain unchanged at 1.76 MB / 6.67 MB because candidate summaries are still copied. |
| Are scalar count copies frequent enough to justify deferred counts? | Yes for the sample path: 515 requests imply an estimated 1545 scalar copies without deferred counts vs 515 packed snapshots with deferred counts. |
| Is there already a device count source suitable for compare/diagnosis? | Yes. Existing direct-reduce code already computes event, run, and candidate counts on device and the deferred-count path snapshots those three counts together. |
| Would deferred counts likely save wall time, or only bytes? | It saves sync/D2H time, not scalar bytes. Wall-time benefit is workload-sensitive: positive on the sample run, not positive on the small benchmark run. |
| Should the next PR be default-off direct region reduce real path? | Not yet. The direct/deferred knobs already exist; the next step should be a shadow/compare or broader characterization gate, not defaulting. |

## Recommendation

Do not default deferred counts from this pass alone. The existing deferred-count
path has a strong D2H/sync signal on the sample path and no fallbacks or
overflows in these runs, but the small benchmark shows that reducing scalar D2H
can be offset by extra GPU/DP timing. The best next mining target is a
deferred-count shadow/compare gate or broader A/B characterization that proves
the sample win is stable and not input-specific.

Suggested next step:

```text
cuda: add region deferred-count shadow gate
```

The gate should keep the current region path authoritative, compare deferred
event/run/candidate counts against the non-deferred observed counts, and report
mismatch and timing deltas. If that remains mismatch-free and sample/panel
timing stays positive, then a later opt-in cleanup/default discussion would have
better evidence.

If broader deferred-count runs do not hold up, the next smaller target should be
region D2H packing for candidate summaries. Safe-store upload reduction remains
secondary, while safe-store data-structure redesign is larger than the next
small stacked PR.

## Out of scope

This pass intentionally does not:

- add or default a new deferred-count real path
- change the existing deferred-count knob semantics
- skip scalar copies in the default path
- change region dispatch, grouping, candidate ordering, or fallback behavior
- change safe-store merge, safe-store upload, or GPU safe-store handoff
- revive the host compact safe-store merge experiment
- enable region true-batch real dispatch
- enable fine geometry real path
- default `sparse_v2`
- skip validation, deep compare, or input checks
- change planner authority
- implement DP/D2H overlap or Layer 3 transducer
