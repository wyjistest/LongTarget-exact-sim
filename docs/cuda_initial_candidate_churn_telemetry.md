# CUDA initial candidate churn telemetry

Date: 2026-05-09

Base: `cuda-initial-candidate-replay-structure`

This pass characterizes candidate container churn inside the existing initial
context-apply candidate replay loop. It adds telemetry only. It does not skip
candidate summaries, add no-op or rejected-below-floor filtering, change
candidate replay order, change top-K / floor / `runningMin` semantics, change
first-max / tie behavior, change safe-store update/prune/upload behavior,
change dispatch, or change output behavior.

## Question

The previous candidate replay structure pass showed that covered initial
context apply is not no-op-heavy or rejected-below-floor-heavy. Nearly every
summary mutates candidate state, but only a tiny final frontier survives.

This pass asks whether that shape looks like candidate container churn:
replacement chains, overwritten slot updates, heap/index maintenance, or final
survivor concentration.

## New telemetry

The new fields are:

```text
benchmark.sim_initial_candidate_churn_container_high_water
benchmark.sim_initial_candidate_churn_container_final_size
benchmark.sim_initial_candidate_churn_cumulative_container_size
benchmark.sim_initial_candidate_churn_replacement_chains
benchmark.sim_initial_candidate_churn_max_replacement_chain
benchmark.sim_initial_candidate_churn_overwritten_updates
benchmark.sim_initial_candidate_churn_final_survivor_updates
benchmark.sim_initial_candidate_churn_overwritten_ratio
benchmark.sim_initial_candidate_churn_first_max_updates
benchmark.sim_initial_candidate_churn_tie_updates
benchmark.sim_initial_candidate_churn_order_sensitive_updates
benchmark.sim_initial_candidate_churn_heap_builds
benchmark.sim_initial_candidate_churn_heap_updates
benchmark.sim_initial_candidate_churn_index_rebuilds
```

The replacement-chain fields are fixed-slot telemetry. They track how many
accepted updates hit a candidate slot before that slot is replaced, then count
those slot updates as overwritten. This is intentionally low-overhead and local
to the existing replay loop; it is not global start-key ancestry.

This pass does not add per-summary `chrono` timers for compare/mutation/erase
because timing 4.7M to 44.8M replay iterations would perturb the measured path.

## Commands

Small benchmark path:

```text
make check-benchmark-telemetry
```

Sample region-locate exactness path:

```text
LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=cuda_initial_candidate_churn_telemetry_sample \
TARGET=$(pwd)/longtarget_cuda \
./scripts/run_sample_exactness_cuda.sh
```

Both runs passed exactness / telemetry gates.

## Results

| Field | benchmark | sample |
| --- | ---: | ---: |
| `candidate_apply_seconds` | 0.207613 | 1.93711 |
| `processed_summaries` | 4,691,334 | 44,777,038 |
| `accepted_updates` | 4,613,123 | 44,395,027 |
| `rejected_below_floor` | 0 | 0 |
| `replacements` | 3,889,333 | 40,318,731 |
| `erasures` | 3,889,333 | 40,318,731 |
| `container_high_water` | 3,450 | 2,400 |
| `container_final_size` | 3,450 | 2,400 |
| `cumulative_container_size` | 234,425,509 | 2,238,768,530 |
| `replacement_chains` | 3,889,333 | 40,318,731 |
| `max_replacement_chain` | 18,898 | 34,412 |
| `overwritten_updates` | 4,301,151 | 43,726,691 |
| `final_survivor_updates` | 311,972 | 668,336 |
| `overwritten_ratio` | 0.932373 | 0.984946 |
| `first_max_updates` | 4,005,536 | 41,581,067 |
| `tie_updates` | 0 | 0 |
| `order_sensitive_updates` | 4,613,123 | 44,395,027 |
| `heap_builds` | 69 | 48 |
| `heap_updates` | 4,000,738 | 41,578,209 |
| `index_rebuilds` | 16,168 | 384,448 |

Derived shape:

| workload | accepted / processed | replacements / processed | overwritten slot updates / accepted | max replacement chain |
| --- | ---: | ---: | ---: | ---: |
| benchmark | 98.33% | 82.91% | 93.24% | 18,898 |
| sample | 99.15% | 90.04% | 98.49% | 34,412 |

Timing context:

| Field | benchmark | sample |
| --- | ---: | ---: |
| `sim_initial_scan_cpu_context_apply_seconds` | 0.207693 | 1.93722 |
| `sim_initial_context_apply_candidate_seconds` | 0.207613 | 1.93711 |
| `sim_initial_store_rebuild_seconds` | 0.203612 | 2.89998 |
| `sim_initial_scan_seconds` | 1.14943 | 9.09293 |
| `sim_seconds` | 2.00526 | 14.0172 |
| `total_seconds` | 4.10493 | 16.1145 |

## Interpretation

Candidate replay is high-churn. On the sample path, `44,395,027` accepted
updates collapse to `2,400` final candidate slots. Fixed-slot tracking estimates
that `43,726,691` accepted slot updates are overwritten before the final
frontier, for an overwritten ratio of `98.49%`. The longest observed slot chain
contains `34,412` accepted updates.

This does not support a no-op skip or rejected-below-floor prefilter:
`rejected_below_floor=0`, tie updates remain zero, and almost every processed
summary is order-sensitive. It also does not prove a simple host shortcut is
safe, because the overwritten updates are discovered only after ordered replay.

The material local structure is replacement churn plus heap/index maintenance:
the sample path reports `40,318,731` replacements/erasures, `41,578,209` heap
updates, and `384,448` index rebuilds. Because this pass does not time each
operation separately, it identifies structure rather than assigning exact
seconds to compare vs container mutation.

## Answers

| question | answer |
| --- | --- |
| Is replay dominated by candidate comparison or container mutation? | The pass does not add per-summary timers. Counters show most summaries mutate candidate state and most accepted slot updates are later overwritten. |
| Are erase/insert/sort operations the main cost? | Replacements/erasures are very high, but there is no separate erase/insert/sort timing in this low-overhead pass. Heap updates and index rebuilds are visible structural costs. |
| Are replacement chains long enough to justify a future shadow compaction? | Yes as a diagnostic target: max slot chains reach `34,412` on sample and overwritten slot updates are `98.49%` of accepted slot updates. Any compaction must remain shadow-first because ordered replay discovers those chains. |
| Are most accepted updates overwritten before final output? | Yes by fixed-slot estimate: `43,726,691` overwritten vs `668,336` final-survivor slot updates on sample. |
| Is there a local host data-structure opportunity? | Possibly a lazy tombstone, handle-based replacement, or per-slot chain compression shadow. A real path is not justified by this telemetry alone. |
| Or does this point toward GPU-resident exact ordered replay? | If host container shadows cannot reduce churn without changing order semantics, the evidence points toward GPU-resident exact ordered replay/transducer shadow rather than skip/filter work. |

## Recommendation

Do not implement no-op skip, rejected-below-floor prefilter, or a real candidate
container optimization from this pass. The next useful PR should remain
diagnostic:

```text
candidate container structure shadow
GPU-resident exact ordered frontier replay shadow
```

If a host-side follow-up is chosen, start with a default-off shadow for lazy
tombstones or handle-based replacement and validate final ordered frontier
identity before considering a real path.
