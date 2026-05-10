# CUDA GPU exact frontier replay shadow contract

Date: 2026-05-10

Base: `cuda-initial-candidate-container-full-shadow`

This is a docs-only contract pass for the next GPU-resident exact ordered
frontier replay shadow. It does not add a real GPU authority path, does not
default `ordered_segmented_v3`, does not add hierarchical top-K, and does not
change initial, locate, region, safe-store, planner, or validation behavior.

## Why this contract exists

Recent CPU-side telemetry closed the low-risk host alternatives. On the sample
path, replay processed `44,777,038` summaries, accepted `44,395,027` updates,
had `rejected_below_floor=0`, performed `40,318,731` replacements/erasures, and
overwrote `98.49%` of accepted slot updates before the final frontier. A GPU
follow-up must therefore be exact ordered replay shadow, not unordered
reduction or approximate top-K.

## Replay input contract

The shadow input is the ordered `SimScanCudaInitialRunSummary` stream:

| Field | Contract role |
| --- | --- |
| `startCoord` | Candidate key; packed `(startI,startJ)` identity. |
| `score` | Candidate score used for max-score / floor behavior. |
| `endI` | Replay event row and candidate bounds update. |
| `minEndJ` / `maxEndJ` | Candidate horizontal bounds update. |
| `scoreEndJ` | First-max end column for score/end tie behavior. |

Required ordering is the CPU replay order consumed by
`applySimCudaInitialRunSummary`: ascending source row order and row-run
coalescing order. Any chunked shadow must preserve global summary order.
Packed summary formats may be used only if unpacking is byte-identical to the
unpacked `SimScanCudaInitialRunSummary` stream.

## Replay state contract

The GPU shadow state must be comparable to CPU ordered replay at the chosen
boundary:

| State | Required contract |
| --- | --- |
| Candidate set | Same candidate count and same ordered candidate values. |
| Candidate key | Same `(STARI,STARJ)` / `startCoord` identity per active candidate. |
| Candidate value | Same score, end, and bounds fields. |
| Running floor / `runningMin` | Same value as CPU after the same replay boundary. |
| Min candidate | Same score and deterministic tie identity at full-frontier boundaries. |
| First-max / tie behavior | Same `ENDI` / `ENDJ` result for equal-score updates. |
| Safe-store state | Same pruned safe-store set before any handoff is considered. |
| Safe-store epoch | Same epoch/handle validity semantics if a GPU safe-store handle exists. |
| Frontier digest | Same count, runningMin, slot-order, identity, score, and bounds digest. |
| Ordered digest | Same digest over CPU-visible candidate slot order. |
| Unordered digest | Same digest over sorted candidate values when order is not observable. |

The CPU ordered replay remains authoritative until all of these are explicitly
validated by shadow-only telemetry.

## Shadow comparison points

Minimum comparison point is after full initial replay, before any GPU shadow
result can influence output. Useful later comparison points, in order:

```text
after row chunk / summary chunk
before safe-store prune
after safe-store prune
before GPU safe-store handoff
after safe-store upload or persistent handle refresh
```

Chunk-level comparison is optional for the first shadow PR. If implemented, the
chunk boundary must be defined in summary ordinal space and must not change CPU
replay order.

## Required mismatch counters

A complete shadow contract needs separate counters for candidate count/value,
ordered and unordered digest, runningMin/floor, min candidate, first-max/tie,
safe-store digest/epoch, frontier digest, and chunk-boundary mismatches.
Aggregating these into one mismatch counter is not enough for a real follow-up.

## Existing counter inventory

| Concept | Existing key / location | Missing? |
| --- | --- | --- |
| replay authority | `benchmark.sim_initial_replay_authority`, `longtarget.cpp:347` / `longtarget.cpp:1752` | Present, but `EXACT_FRONTIER_REPLAY=1` can report `gpu_real` when initial reduce is enabled. |
| exact replay scaffold | `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1`, `README.md:86`, `sim.h:3426` | Present as scaffold, not a shadow contract. |
| ordered summary input | `SimScanCudaInitialRunSummary`, `cuda/sim_scan_cuda.h:24` | Present. Contract needs explicit order/chunk wording. |
| chunk boundary support | `benchmark.sim_initial_reduce_chunks_*`, `README.md:253`; reducer chunk size in ordered replay kernels | Partial. Boundary mismatch counters are missing. |
| frontier digest | `digestSimCudaFrontierStatesForTransducerShadow`, `sim.h:15521` | Present for transducer shadow; not exposed as ordered/unordered contract counters. |
| frontier shadow mismatch | `benchmark.sim_initial_frontier_transducer_shadow_mismatches`, `longtarget.cpp:2732` | Present as aggregate mismatch only. |
| candidate count mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_count_mismatches`, `longtarget.cpp:2742` | Present for ordered_segmented_v3 shadow. |
| candidate value mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_value_mismatches`, `longtarget.cpp:2744` | Present for ordered_segmented_v3 shadow. |
| runningMin/floor mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_running_min_mismatches`, `longtarget.cpp:2738` | Present for final shadow boundary. Separate floor/min-candidate counters missing. |
| safe-store digest mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_safe_store_mismatches`, `longtarget.cpp:2740` | Partial. It is set equality, not a named digest counter. |
| safe-store epoch mismatch | safe-store handle telemetry epoch exists in CUDA handle code; stale-epoch rejection is reported by handoff/scheduler counters | Missing as an exact replay shadow mismatch. |
| first-max/tie mismatch | candidate churn reports `first_max_updates` / `tie_updates` counts | Missing as a GPU-vs-CPU comparison. |
| min candidate mismatch | candidate container estimator has final `min_candidate_mismatches` | Missing for GPU exact replay shadow. |
| device safe-store handle state | `benchmark.sim_initial_exact_frontier_replay_device_safe_stores`, `benchmark.sim_initial_safe_store_handoff_*` | Partial. Availability exists; epoch/digest equivalence missing. |

## Existing shadow mapping

`runSimCudaInitialFrontierTransducerShadowIfEnabled` compares a GPU transducer
digest and ordered candidate states against the CPU context after CPU replay,
but exposes only one aggregate mismatch counter.

`runSimCudaInitialOrderedSegmentedV3ShadowIfEnabled` compares final frontier,
`runningMin`, safe-store set, candidate count, and candidate values against a
CPU oracle. Missing pieces are first-max/tie mismatch classification,
min-candidate mismatch, ordered/unordered digest counters, safe-store
digest/epoch counters, and chunk-boundary mismatch counters.

## Authority model

CPU ordered replay remains authoritative. GPU exact replay must be shadow-only,
must not feed output, locate, region, safe-store handoff, or planner authority,
and mismatch counters must not change output or defaults.

The current `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1` scaffold is
not the desired next step for this contract because it can report `gpu_real`
authority on the experimental initial reduce path. The next PR should add a
shadow-only gate or reuse an existing shadow gate without changing authority.

## Non-goals

This contract is not hierarchical top-K, unordered reduction, approximate
replay, Layer 3 transducer composition, default `ordered_segmented_v3`, packed
summary default, DP/D2H overlap, or host precombine/compact/lazy-container
revival.

## Recommendation

The next PR should be one of:

| Option | When to choose it |
| --- | --- |
| `GPU shadow stub` | If we want activation/disabled-reason telemetry first, with authority fixed to CPU. |
| `ordered_segmented_v3 counter cleanup` | If the fastest useful step is splitting existing mismatches into digest/min/tie/epoch counters. |
| `minimal CUDA replay shadow for one chunk` | If a single-chunk shadow can reuse existing transducer test entry points without new authority paths. |
| stop | If first-max/tie or safe-store epoch comparison requires broad kernel changes. |

Recommended immediate next step: `ordered_segmented_v3 counter cleanup` plus a
shadow-only gate, because existing final-boundary comparisons already cover
frontier, runningMin, safe-store set, candidate count, and candidate values.
Do not implement a real GPU replay authority path until the missing mismatch
counters are explicit and clean.
