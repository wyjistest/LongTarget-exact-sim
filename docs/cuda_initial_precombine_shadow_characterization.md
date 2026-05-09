# CUDA initial safe-store precombine shadow characterization

Date: 2026-05-09

Base: `cuda-initial-precombine-shadow`

This is a docs-only characterization of the default-off initial safe-store
duplicate-start precombine shadow added in PR #16. It does not add a real
precombine path, does not change initial dispatch, candidate replay, safe-store
update order, prune semantics, upload/device handoff, region dispatch, planner
authority, validation, fallback, or output behavior.

## Question

PR #15 showed that the sample initial safe-store update processes
`44,777,038` summaries but inserts only `8,831,091` unique safe-store states.
PR #16 proved that a duplicate-start precombine shadow can reproduce the
authoritative post-update safe-store on the sample path with zero
size/candidate/order/digest mismatches.

This pass asks whether that shadow is cheap and robust enough to justify the
next PR being a default-off real precombine path.

## Method

The following commands were run from this branch:

```text
make check-benchmark-telemetry
make check-sample-cuda-sim-region-locate
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRECOMBINE_SHADOW=1 make check-sample-cuda-sim-region-locate
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRECOMBINE_SHADOW=1 make check-matrix-cuda-sim-region
```

The sample and matrix opt-in runs passed their exactness checks. The matrix run
is an opt-in smoke for additional order-sensitive coverage; it is not used as a
wall-clock performance claim.

## Results

| workload | mode | update seconds | prune seconds | shadow seconds | input summaries | unique states | duplicate summaries | saved upserts | mismatch total | sim seconds | total seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| benchmark | default | 0.158299 | 0.045746 | 0 | 4,691,334 | 929,829 | 3,761,505 | 0 | 0 | 7.70086 | 9.81646 |
| sample | default | 2.18637 | 0.730164 | 0 | 44,777,038 | 8,831,091 | 35,945,947 | 0 | 0 | 13.1049 | 15.234 |
| sample | shadow | 2.21346 | 0.922472 | 2.16823 | 44,777,038 | 8,831,091 | 35,945,947 | 35,945,947 | 0 | 19.0264 | 21.1632 |
| matrix | shadow | 0.0793472 | 0.0242225 | 0.0781375 | 2,101,113 | 315,812 | 1,785,301 | 1,785,301 | 0 | 1.33062 | 1.68421 |

Opt-in mismatch counters:

| workload | size | candidate | order | digest |
| --- | ---: | ---: | ---: | ---: |
| sample shadow | 0 | 0 | 0 | 0 |
| matrix shadow | 0 | 0 | 0 | 0 |

Derived cost model:

| workload | duplicate ratio | shadow / input summary | shadow / unique state | legacy update / input summary | shadow / legacy update |
| --- | ---: | ---: | ---: | ---: | ---: |
| sample shadow | 80.28% | 48.42 ns | 245.52 ns | 49.43 ns | 97.96% |
| matrix shadow | 84.97% | 37.19 ns | 247.42 ns | 37.76 ns | 98.48% |

## Interpretation

The exactness signal is strong. The precombine shadow reproduced the
authoritative post-update safe-store on both sample and matrix opt-in coverage,
including the order-sensitive comparator. The duplicate ratio is also stable and
high: about `80%` on the sample path and about `85%` on the matrix smoke.

The cost signal is not favorable enough for a real path yet. The current shadow
implementation is effectively another host `unordered_map` pass over all input
summaries. On the sample run, the shadow costs `2.16823s` while the legacy
authoritative update costs `2.21346s`. On matrix, the shadow costs `0.0781375s`
while the legacy update costs `0.0793472s`. In both cases the shadow is about
`98%` of the legacy update cost.

That does not mean precombine is a bad target. It means the current host shadow
structure is a proof of semantic opportunity, not a proof of production speed.
A real path that simply adds this grouping pass before the existing update would
likely duplicate most of the current update work. A useful real path needs a
cheaper grouping/build structure or must replace enough of the legacy update
work to recover the grouping cost.

The shadow timing includes grouping/build plus full comparison work, so it is
not a production timing. But even with that caveat, the cost is too close to the
legacy update to justify jumping straight to a real precombine PR.

## Answers

| question | answer |
| --- | --- |
| Is shadow precombine cheaper than legacy safe-store update? | Only marginally in this diagnostic form. It is `97.96%` of sample update time and `98.48%` of matrix update time. |
| Is duplicate ratio consistently high? | Yes on covered paths: `80.28%` sample, `84.97%` matrix, and `80.18%` on the default benchmark shape. |
| Are all mismatch counters zero on sample and matrix? | Yes. Size, candidate, order, and digest mismatches are all zero on both opt-in runs. |
| Does shadow cost look dominated by grouping/build or comparison? | Existing telemetry cannot separate them. Since the helper performs one host grouping pass and then compares the full shadow store, the next useful step is cost decomposition if this path stays active. |
| Is a future real precombine path likely to reduce update seconds? | Not with the current host shadow structure as an added pre-pass. It may be viable if the precombined output replaces the legacy summary-by-summary upsert loop or uses a cheaper grouping layout. |
| What should the next PR be? | Do not add a real precombine path yet. Either decompose precombine shadow cost, or design a cheaper replacement structure with validation. If the goal is a smaller next proof PR, move to initial prune/index rebuild shadow. |

## Recommendation

Do not implement `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRECOMBINE=1` as the
next PR from the current host shadow structure.

Recommended next step:

```text
initial precombine cost decomposition
```

Useful decomposition fields would be:

```text
precombine_group_seconds
precombine_compare_order_seconds
precombine_compare_set_seconds
precombine_digest_seconds
precombine_index_build_seconds
```

If the grouping portion is much lower than the full shadow time, a future
default-off real path can be reconsidered. If grouping itself is close to the
legacy update time, pause precombine implementation and move to initial
prune/index rebuild shadow or context-apply decomposition.
