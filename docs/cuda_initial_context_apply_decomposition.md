# CUDA initial context apply decomposition

Date: 2026-05-09

Base: `cuda-initial-prune-index-shadow`

This pass decomposes the existing initial CPU context-apply timing. It adds
telemetry only. It does not change context apply semantics, candidate update
order, `runningMin` / floor behavior, safe-store update/prune/upload behavior,
initial dispatch, region dispatch, planner authority, validation, fallback, or
output behavior.

## Question

The prune/index compact prototype was exact but slower, so it should not be
submitted. After the safe-store update/prune routes produced negative real-path
results, the next unexplained CPU-side target is:

```text
benchmark.sim_initial_scan_cpu_context_apply_seconds
```

This pass asks whether that time is dominated by candidate replay, floor /
`runningMin` refresh, frontier synchronization, safe-store handoff, or no-op
events.

## New telemetry

The new fields are:

```text
benchmark.sim_initial_context_apply_candidate_seconds
benchmark.sim_initial_context_apply_floor_seconds
benchmark.sim_initial_context_apply_frontier_seconds
benchmark.sim_initial_context_apply_safe_store_handoff_seconds
benchmark.sim_initial_context_apply_candidate_erase_seconds
benchmark.sim_initial_context_apply_candidate_insert_seconds
benchmark.sim_initial_context_apply_candidate_sort_seconds
benchmark.sim_initial_context_apply_running_min_updates
benchmark.sim_initial_context_apply_candidate_updates
benchmark.sim_initial_context_apply_frontier_updates
benchmark.sim_initial_context_apply_safe_store_handoffs
benchmark.sim_initial_context_apply_noop_events
```

The timers wrap only existing local blocks when benchmark telemetry is enabled.
The legacy summary replay path explicitly opts into this breakdown so reducer
helpers and shadow/oracle calls do not pollute the context-apply counters.
This pass instruments the default summary-replay path and the opt-in chunk-skip
replay path. Zero-valued frontier, safe-store handoff, candidate erase,
candidate insert, and candidate sort fields mean the covered path did not use a
locally separated block in this pass.

## Commands

Small benchmark path:

```text
make check-benchmark-telemetry
```

Sample region-locate exactness path:

```text
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=cuda_initial_context_apply_decomposition_sample \
TARGET=$(pwd)/longtarget_cuda \
./scripts/run_sample_exactness_cuda.sh
```

Both runs passed exactness / telemetry gates.

## Results

| Field | benchmark | sample |
| --- | ---: | ---: |
| `context_apply_seconds` | 0.176298 | 1.58242 |
| `candidate_apply_seconds` | 0.176231 | 1.58233 |
| `floor/running_min_seconds` | 0.000004457 | 0.00000443 |
| `frontier_seconds` | 0 | 0 |
| `safe_store_handoff_seconds` | 0 | 0 |
| `candidate_erase_seconds` | 0 | 0 |
| `candidate_insert_seconds` | 0 | 0 |
| `candidate_sort_seconds` | 0 | 0 |
| `candidate_updates` | 4,691,334 | 44,777,038 |
| `running_min_updates` | 69 | 48 |
| `frontier_updates` | 0 | 0 |
| `safe_store_handoffs` | 0 | 0 |
| `noop_events` | 0 | 0 |
| `safe_store_update_seconds` | 0.164841 | 2.1891 |
| `safe_store_prune_seconds` | 0.0467582 | 0.741149 |
| `store_rebuild_seconds` | 0.211599 | 2.93025 |
| `initial_cpu_merge_seconds` | 0.39147 | 4.70721 |
| `initial_scan_seconds` | 1.06876 | 8.44705 |
| `safe_workset_total_seconds` | 0.442991 | 4.22754 |
| `safe_workset_merge_seconds` | 0.0784797 | 1.37479 |
| `sim_seconds` | 1.99638 | 13.0961 |
| `total_seconds` | 4.08563 | 15.4374 |

Derived shape:

| workload | candidate / context apply | candidate updates / second | no-op events |
| --- | ---: | ---: | ---: |
| benchmark | 99.96% | 26.62M | 0 |
| sample | 99.99% | 28.30M | 0 |

## Interpretation

The default initial context apply path is almost entirely candidate replay over
run summaries. On the sample path, `44,777,038` candidate updates account for
`1.58233s` of the `1.58242s` context-apply total. Floor refresh is microseconds.
The frontier / safe-store handoff / candidate erase / candidate insert / sort
fields are zero because the covered default summary-handoff path did not use a
locally separated block for those categories in this pass.

This narrows the remaining CPU-side target. The context-apply cost on this
covered path is not floor refresh or a hidden local sort. It is the existing
per-summary candidate mutation path. The new counters do not split
`addnodeIndexed` / `applySimCudaInitialRunSummary` internals, because doing so
would require refactoring the exact state machine rather than wrapping local
blocks.

The default path reports zero no-op events because chunk-skip is disabled in
these runs. That means the current telemetry does not yet prove a no-op skip is
available. It only shows that if context apply is pursued next, the target must
be candidate replay structure, duplicate/no-op shadow evidence, or a different
workload with clearer candidate mutation behavior.

## Answers

| question | answer |
| --- | --- |
| Which sub-step dominates initial context apply? | Candidate replay dominates: `99.96%` of benchmark context apply and `99.99%` of sample context apply. |
| Is context apply mostly candidate mutation, floor/runningMin update, frontier sync, or safe-store handoff? | Candidate mutation / replay on the covered default path. Floor refresh is microseconds; frontier and safe-store handoff were not locally separated on this path. |
| Are there many no-op events that could justify a future shadow skip? | Not on the default runs; `noop_events=0`. A future no-op/duplicate shadow would need to enable or add explicit diagnostic coverage before claiming skip potential. |
| What is the next likely PR? | Candidate mutation structure telemetry or a default-off context-apply duplicate/no-op shadow. Do not revive prune/index compact or host precombine without a new data structure. |

## Recommendation

Do not continue the current prune/index compact prototype. For the next stage,
either decompose candidate replay internals locally, or add a diagnostic
duplicate/no-op shadow that estimates whether many summary updates are redundant
without changing candidate update order.

If candidate replay internals are too entangled to split without state-machine
refactoring, stop this CPU-side micro-optimization line and seek a workload or
structure where the critical path is easier to isolate.
