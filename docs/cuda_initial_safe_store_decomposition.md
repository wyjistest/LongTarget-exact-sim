# CUDA initial safe-store rebuild decomposition

Date: 2026-05-09

Base: `cuda-sample-initial-scan-composition`

This pass decomposes the CPU-side initial safe-store rebuild that PR #14
identified as the largest visible sample initial-scan subphase. It adds
telemetry only. It does not change initial scan dispatch, candidate replay,
safe-store ordering, safe-store pruning semantics, region dispatch, planner
authority, validation, fallback, or CUDA kernels.

## Question

PR #14 showed the stable sample initial scan includes about `~3.0s` of
CPU-side safe-store update/prune work:

```text
safe-store update   ~2.21s
safe-store prune    ~0.77s
update + prune      ~3.0s
```

This pass asks what that rebuild is doing internally.

## New telemetry

The initial safe-store update loop now reports:

```text
benchmark.sim_initial_safe_store_update_calls
benchmark.sim_initial_safe_store_update_summaries
benchmark.sim_initial_safe_store_update_inserted_states
benchmark.sim_initial_safe_store_update_merged_summaries
benchmark.sim_initial_safe_store_update_store_size_before
benchmark.sim_initial_safe_store_update_store_size_after
```

The prune pass now reports:

```text
benchmark.sim_initial_safe_store_prune_calls
benchmark.sim_initial_safe_store_prune_scanned_states
benchmark.sim_initial_safe_store_prune_kept_states
benchmark.sim_initial_safe_store_prune_removed_states
benchmark.sim_initial_safe_store_prune_kept_above_floor
benchmark.sim_initial_safe_store_prune_kept_frontier
benchmark.sim_initial_safe_store_prune_index_rebuild_seconds
```

`kept_above_floor` and `kept_frontier` are mutually exclusive keep reasons.

## Sample result

One fresh `check-sample-cuda-sim-region-locate` run produced:

| field | value |
| --- | ---: |
| `sim_initial_scan_seconds` | 8.65271 |
| `sim_initial_scan_cpu_merge_seconds` | 5.09161 |
| `sim_initial_scan_cpu_context_apply_seconds` | 1.62576 |
| `sim_initial_scan_cpu_safe_store_update_seconds` | 2.43955 |
| `sim_initial_scan_cpu_safe_store_prune_seconds` | 0.899105 |
| `sim_initial_store_rebuild_seconds` | 3.33866 |
| `sim_initial_scan_d2h_seconds` | 1.64938 |
| `sim_initial_scan_gpu_seconds` | 0.878237 |

Safe-store rebuild shape:

| field | value |
| --- | ---: |
| `sim_initial_safe_store_update_calls` | 48 |
| `sim_initial_safe_store_update_summaries` | 44,777,038 |
| `sim_initial_safe_store_update_inserted_states` | 8,831,091 |
| `sim_initial_safe_store_update_merged_summaries` | 35,945,947 |
| `sim_initial_safe_store_update_store_size_before` | 0 |
| `sim_initial_safe_store_update_store_size_after` | 8,831,091 |
| `sim_initial_safe_store_prune_calls` | 48 |
| `sim_initial_safe_store_prune_scanned_states` | 8,831,091 |
| `sim_initial_safe_store_prune_kept_states` | 3,311,201 |
| `sim_initial_safe_store_prune_removed_states` | 5,519,890 |
| `sim_initial_safe_store_prune_kept_above_floor` | 3,311,189 |
| `sim_initial_safe_store_prune_kept_frontier` | 12 |
| `sim_initial_safe_store_prune_index_rebuild_seconds` | 0.568251 |

## Benchmark result

The small benchmark path shows the same structure at smaller scale:

| field | value |
| --- | ---: |
| `sim_initial_scan_cpu_safe_store_update_seconds` | 0.157564 |
| `sim_initial_scan_cpu_safe_store_prune_seconds` | 0.0460879 |
| `sim_initial_store_rebuild_seconds` | 0.203652 |
| `sim_initial_safe_store_update_calls` | 69 |
| `sim_initial_safe_store_update_summaries` | 4,691,334 |
| `sim_initial_safe_store_update_inserted_states` | 929,829 |
| `sim_initial_safe_store_update_merged_summaries` | 3,761,505 |
| `sim_initial_safe_store_prune_scanned_states` | 929,829 |
| `sim_initial_safe_store_prune_kept_states` | 434,435 |
| `sim_initial_safe_store_prune_removed_states` | 495,394 |
| `sim_initial_safe_store_prune_index_rebuild_seconds` | 0.029109 |

## Interpretation

The sample safe-store rebuild is not dominated by upload or a small scalar
operation. The update phase replays `44.8M` run summaries into a host
`unordered_map` indexed safe-store, but only `8.83M` of those summaries create
new states. About `80%` of update inputs are duplicate-start merges.

The prune phase then scans all `8.83M` unique states and removes `5.52M` of
them. The index rebuild inside prune accounts for about `0.57s`, so a meaningful
part of prune is rebuilding the host start-coordinate index after filtering.
Most retained states are kept because they are above the running floor; only
`12` sample states are retained solely because they are current frontier starts.

## Recommendation

The next optimization should target safe-store rebuild structure, not transfer
alone:

```text
1. Reduce duplicate-start host summary replay before unordered_map upsert.
2. Avoid full host prune/index rebuild when most scanned states are removed.
3. Consider a grouped/segmented safe-store construction that emits one state per
   start before host merge, but only behind exact shadow validation.
4. Treat safe-store upload as secondary; this report's sample rebuild cost is
   update/prune dominated.
```

If the next PR stays telemetry-first, the useful gap is timing inside update:
hash lookup/upsert versus state merge. If it moves toward implementation, it
needs an exact shadow gate because this path is order-sensitive and feeds the
safe-workset locate authority.
