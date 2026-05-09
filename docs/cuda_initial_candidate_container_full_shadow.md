# CUDA initial candidate container full shadow stop report

Date: 2026-05-09

Base: `cuda-initial-candidate-container-shadow`

This pass evaluated whether the estimator-only candidate container diagnostic
could be extended into a full intermediate-state lazy/versioned container
shadow:

```text
LONGTARGET_SIM_CUDA_INITIAL_CANDIDATE_CONTAINER_SHADOW=1
```

No full shadow was implemented. The current code shape trips the stop
conditions for a small stacked PR: intermediate floor/min validation is not a
local wrapper around the existing replay, first-max/tie comparison is not a
separate observable state, and the estimator already shows sample stale growth
near the number of accepted replay updates.

## Prior estimator baseline

| Field | benchmark | sample |
| --- | ---: | ---: |
| `candidate_apply_seconds` | 0.204088 | 1.87687 |
| `events` | 4,691,334 | 44,777,038 |
| `active_candidates` | 3,450 | 2,400 |
| `stale_entries` | 4,609,673 | 44,392,627 |
| `high_water_entries` | 4,613,123 | 44,395,027 |
| `lazy_pops` | 3,889,333 | 40,318,731 |
| `est_saved_erasures` | 3,889,333 | 40,318,731 |
| `est_saved_index_rebuilds` | 16,168 | 384,448 |
| `state_mismatches` | 0 | 0 |
| `floor_mismatches` | 0 | 0 |
| `min_candidate_mismatches` | 0 | 0 |
| `digest_mismatches` | 0 | 0 |
| `order_mismatches` | 0 | 0 |
| `full_shadow_seconds` | not implemented | not implemented |
| `full_shadow_aborted` | not implemented | not implemented |
| `full_shadow_abort_reason` | full shadow not local | full shadow not local |

The zero mismatch counters above are final-state self-checks from the existing
estimator. They do not prove lazy/versioned equivalence at intermediate
candidate-container states.

## Inventory

The authoritative candidate container is updated directly inside
`ensureSimCandidateIndexForRun` and `applySimCudaInitialRowEventRun`.
Replacement selects the current min candidate from the authoritative heap,
erases the start-index entry, overwrites the slot, reinserts the new start key,
updates the heap, and rebuilds the start index when tombstones exceed `K`.

The existing initial replay loops call `applySimCudaInitialRunSummary` for each
summary, then refresh `runningMin` once after the whole batch. The candidate
container estimator is recorded only after that refresh. In the chunk-skip path,
the same pattern applies: replay chunks, refresh `runningMin`, then record the
estimator.

This means the current estimator sees only the final authoritative container.
A full intermediate-state shadow would need to feed a second container inside
the per-summary replay path and compare after safe intermediate points. That is
not a local post-replay diagnostic.

Relevant code points:

```text
sim.h:12144  ensureSimCandidateIndexForRun updates authoritative slots/index/heap
sim.h:12717  applySimCudaInitialRowEventRun applies each summary to the context
sim.h:12822  first-max updates are replay classification counters
sim.h:13446  default initial replay loop applies summaries
sim.h:13463  default path refreshes runningMin after replay
sim.h:13478  default path records the existing estimator after final refresh
sim.h:13532  chunk-skip replay applies summaries inside chunks
sim.h:13551  chunk-skip path refreshes runningMin after replay
sim.h:13568  chunk-skip path records the existing estimator after final refresh
sim.h:15700  runSimInitialCandidateContainerShadowEstimator uses final state
```

## Why full shadow stopped

1. Intermediate floor/min validation is not local. Initial replay refreshes
   `runningMin` after the full summary replay, not after each summary, so there
   is no existing authoritative intermediate floor state to compare without
   inserting new per-summary observation work.
2. Min-candidate comparison would require a live side container plus a live
   authoritative scan/heap observation at comparison points. Doing this over
   44.8M sample summaries would perturb the path or require a replay refactor.
3. First-max and tie behavior are currently counted as replay classifications.
   There is no separate first-max/tie state object that a lazy container can
   compare against locally.
4. The lazy append-only shape has unsafe stale growth for this small PR. The
   sample estimator reports `44,392,627` stale entries for only `2,400` active
   candidates. A full shadow would need memory limits, abort reasons, and
   enough machinery to avoid destabilizing sample/matrix runs.
5. Implementing the above would turn a telemetry PR into a broad candidate
   replay/container refactor, which is outside the intended review size.

## Answers

| Question | Answer |
| --- | --- |
| Can lazy/versioned shadow reproduce authoritative intermediate state? | Not proven. Full intermediate validation was not implemented because it is not local to the current replay structure. |
| Are floor/min-candidate mismatches zero? | Only final estimator self-checks are zero. Intermediate floor/min checks were not available without invasive replay hooks. |
| Are first-max/tie mismatches zero? | Not measured. First-max/tie are classification counters in the current replay telemetry, not a separately comparable state. |
| Is stale growth manageable? | No evidence that it is manageable. Sample stale entries reach `44,392,627` for `2,400` active candidates. |
| Do lazy pops or compaction estimates erase the saved-work benefit? | The estimator reports `40,318,731` lazy pops and a `44,395,027` compaction estimate on sample, so any real path would need to prove those costs do not replace the saved erase/index work. |
| Should the next PR be real lazy container, more host shadow, GPU replay shadow, or abandon host restructuring? | Do not move to a real lazy container. The next useful PR should be GPU-resident exact ordered frontier replay shadow, unless a much narrower host comparison hook is designed first. |

## Recommendation

Stop the host lazy/versioned container line for now. The estimator showed real
saved-work potential, but the full-shadow proof would require intrusive
intermediate replay hooks and would carry very high stale-state memory risk.

The next evidence-driven target should be:

```text
GPU-resident exact ordered frontier replay shadow
```

That path matches the current bottleneck better: high-churn, order-sensitive
candidate replay where nearly every summary mutates state, but most accepted
updates are overwritten before the final frontier.

No default behavior changed, no telemetry fields were added, and no real
lazy/tombstone candidate path was introduced.
