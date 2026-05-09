# CUDA initial safe-store prune/index shadow

Date: 2026-05-09

Base: `cuda-initial-precombine-shadow-cost-breakdown`

This pass adds a default-off diagnostic shadow for the initial safe-store
prune/index structure. It does not replace the real prune path, does not skip
prune, and does not change safe-store ordering, candidate replay, prune
semantics, upload/device handoff, dispatch, planner authority, validation,
fallback, or output behavior.

## Question

PR #18 closed the current host-side precombine real-path route: duplicate-start
opportunity and exactness are strong, but the host group-build cost is too close
to the authoritative update loop. The remaining initial safe-store rebuild cost
is prune/index work.

This pass asks whether the initial prune/index structure has a local target:
scan/predicate, compaction/write, or index rebuild.

## Method

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRUNE_INDEX_SHADOW=1` captures the
pre-prune context, runs the existing prune predicate on a side-copy store, and
compares the shadow post-prune store with the authoritative real post-prune
store. The shadow result is never used for upload, dispatch, validation
authority, or later locate/region work.

Telemetry added:

```text
benchmark.sim_initial_safe_store_prune_index_shadow_enabled
benchmark.sim_initial_safe_store_prune_index_shadow_calls
benchmark.sim_initial_safe_store_prune_index_shadow_seconds
benchmark.sim_initial_safe_store_prune_index_shadow_scan_seconds
benchmark.sim_initial_safe_store_prune_index_shadow_compact_seconds
benchmark.sim_initial_safe_store_prune_index_shadow_index_rebuild_seconds
benchmark.sim_initial_safe_store_prune_index_shadow_states_scanned
benchmark.sim_initial_safe_store_prune_index_shadow_states_kept
benchmark.sim_initial_safe_store_prune_index_shadow_states_removed
benchmark.sim_initial_safe_store_prune_index_shadow_removed_ratio
benchmark.sim_initial_safe_store_prune_index_shadow_size_mismatches
benchmark.sim_initial_safe_store_prune_index_shadow_candidate_mismatches
benchmark.sim_initial_safe_store_prune_index_shadow_order_mismatches
benchmark.sim_initial_safe_store_prune_index_shadow_digest_mismatches
```

Commands used for the reported opt-in data:

```text
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRUNE_INDEX_SHADOW=1 make check-sample-cuda-sim-region-locate
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRUNE_INDEX_SHADOW=1 make check-matrix-cuda-sim-region
```

Both opt-in exactness runs passed.

## Results

| workload | prune seconds | index rebuild seconds | scanned | kept | removed | removed ratio | shadow seconds | shadow scan | shadow compact | shadow index rebuild | size mismatches | candidate mismatches | order mismatches | digest mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sample | 0.767659 | 0.467476 | 8,831,091 | 3,311,201 | 5,519,890 | 62.51% | 1.09485 | 0.152691 | 0.000001216 | 0.304935 | 0 | 0 | 0 | 0 |
| matrix | 0.0190056 | 0.00769845 | 315,812 | 40,998 | 274,814 | 87.02% | 0.0295162 | 0.0057652 | 0.000000039 | 0.00543412 | 0 | 0 | 0 | 0 |

Derived ratios:

| workload | index / prune | shadow scan / prune | shadow index / prune | removed / scanned |
| --- | ---: | ---: | ---: | ---: |
| sample | 60.90% | 19.89% | 39.72% | 62.51% |
| matrix | 40.51% | 30.33% | 28.59% | 87.02% |

## Interpretation

The full shadow compare is exact on covered paths. Size, candidate, order, and
digest mismatches are all zero for sample and matrix opt-in coverage.

Index rebuild is a visible standalone target. On the sample path, the existing
authoritative index rebuild is `0.467476s`, about `60.90%` of prune time. On the
matrix run, it is `0.00769845s`, about `40.51%` of prune time. This is a better
localized signal than host precombine: it is smaller than update, but it is
clearly separable and consistently visible.

The removed ratio is high. Sample removes `62.51%` of scanned states; matrix
removes `87.02%`. That suggests a structure that avoids rebuilding an index for
states that are about to be discarded may be worth exploring. It does not prove
a real compact path is faster: the shadow total includes side-copy and full
compare/digest work, so it is a diagnostic exactness/cost decomposition, not
production timing.

Compaction itself is not visible in this vector-swap implementation. The
shadow compact timer is near zero because the current code builds a kept vector
during scan, then swaps it into the store. The practical costs are scan/predicate,
kept-vector writes during scan, and index rebuild.

## Answers

| question | answer |
| --- | --- |
| Is prune dominated by scanning, compacting, or index rebuild? | Index rebuild is the clearest standalone component: about `60.90%` of sample prune and `40.51%` of matrix prune. Scan/predicate is also visible. Compact swap is not a meaningful cost by itself. |
| Is index rebuild a standalone target? | Yes. It is already separately timed in the authoritative path and remains visible in shadow. |
| Is the removed ratio stable and high enough to justify a new structure? | It is high on covered paths: `62.51%` sample and `87.02%` matrix. That is enough for a default-off validation prototype, not enough for a default. |
| Does a shadow pruned store match the real post-prune store exactly? | Yes on covered sample and matrix runs: size/candidate/order/digest mismatches are all zero. |
| Should the next PR be a real prune/index compact path? | Not a default path. A small default-off prune/index compact prototype with validation is reasonable if it replaces rebuild work locally; otherwise continue cost decomposition or move to context-apply decomposition. |

## Recommendation

The next PR can be a narrow default-off prune/index compact validation prototype
only if it stays local and keeps the current prune path authoritative under
validation. It should compare size, ordered candidates, set candidates, and
digest, and must not change upload/device handoff or later locate/region work.

If that prototype needs broad safe-store data-structure changes, pause this line
and move to initial context-apply decomposition instead.
