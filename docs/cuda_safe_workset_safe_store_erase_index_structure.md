# CUDA Safe-Workset Safe-Store Erase/Index Structure

Base branch:

```text
cuda-safe-workset-host-merge-best-path-decomposition
```

Base commit:

```text
dab749b
```

This is a telemetry and characterization PR. It does not optimize safe-store
erase, skip erase, skip prune, implement tombstones, change region dispatch,
change safe-window planner authority, default GPU best-path envs, activate the
clean frontier gate, or route through `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY`.

## Goal

PR #36 showed safe-workset host merge is dominated by safe-store maintenance.
This pass splits the affected-start safe-store erase and prune/index work:

```text
affected-start erase:
  scan/lookup/copy loop
  vector swap/compact
  index rebuild

safe-store prune:
  predicate scan/copy loop
  vector swap/compact
  index rebuild
```

It also extends the existing default-off
`LONGTARGET_SIM_CUDA_SAFE_STORE_MERGE_STRUCTURE_SHADOW=1` diagnostic with
tombstone/generation first-order estimates. The shadow remains diagnostic only;
the existing host safe-store remains authoritative.

## Mode

All 3-run sample medians used the recommended safe-store GPU best path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
./scripts/run_sample_exactness_cuda.sh
```

Run logs:

```text
.tmp/cuda_safe_workset_safe_store_erase_index_structure_r1/
.tmp/cuda_safe_workset_safe_store_erase_index_structure_r2/
.tmp/cuda_safe_workset_safe_store_erase_index_structure_r3/
```

One additional diagnostic run enabled:

```text
LONGTARGET_SIM_CUDA_SAFE_STORE_MERGE_STRUCTURE_SHADOW=1
```

Its log is:

```text
.tmp/cuda_safe_workset_safe_store_erase_index_structure_shadow/
```

## Top-Level Medians

| Field | Median | Range |
| --- | ---: | ---: |
| total_seconds | 13.2247 | 0.4661 |
| sim_seconds | 11.1543 | 0.5129 |
| calc_score_seconds | 1.74872 | 0.01224 |
| sim_initial_scan_seconds | 6.71026 | 0.17553 |
| sim_initial_store_rebuild_seconds | 0.760306 | 0.129621 |
| sim_safe_workset_total_seconds | 4.06589 | 0.38489 |
| sim_safe_workset_build_seconds | 0.327535 | 0.004757 |
| sim_safe_workset_merge_seconds | 1.1821 | 0.02087 |
| sim_region_scan_gpu_seconds | 2.48436 | 0.39391 |
| sim_region_d2h_seconds | 0.636292 | 0.034269 |

Region GPU is still the larger aggregate, but PR #35 showed no conservative
batching opportunity. This PR focuses on the next local host merge structure
question.

## Merge Structure

| Field | Median | Range | Share of merge |
| --- | ---: | ---: | ---: |
| sim_safe_workset_merge_seconds | 1.1821 | 0.02087 | 100.00% |
| safe_store_upsert_seconds | 0.656247 | 0.023608 | 55.52% |
| safe_store_erase_seconds | 0.641128 | 0.024503 | 54.24% |
| safe_store_erase_scan_lookup_seconds | 0.0656285 | 0.0036432 | 5.55% |
| safe_store_erase_compact_seconds | 0.00001247 | 0.00000043 | 0.00% |
| safe_store_erase_index_rebuild_seconds | 0.568602 | 0.023815 | 48.10% |
| safe_store_upsert_loop_seconds | 0.0152244 | 0.0010001 | 1.29% |
| safe_store_prune_seconds | 0.465666 | 0.015945 | 39.39% |
| safe_store_prune_scan_seconds | 0.0717278 | 0.0030826 | 6.07% |
| safe_store_prune_compact_seconds | 0.000012156 | 0.000000781 | 0.00% |
| safe_store_prune_index_rebuild_seconds | 0.317182 | 0.012438 | 26.83% |
| safe_store_upload_seconds | 0.0456509 | 0.0002656 | 3.86% |

The key result is that affected-start erase is not dominated by sorted lookup
or vector compaction. It is dominated by rebuilding the safe-store start index
after the erase. Prune has the same shape: the predicate scan is visible, but
index rebuild is the dominant sub-slice.

Combined erase + prune index rebuild is:

```text
0.568602s + 0.317182s = 0.885784s
```

That is about `74.93%` of the host merge median.

## Store Shape

| Field | Median |
| --- | ---: |
| sim_safe_workset_returned_states | 185,280 |
| sim_safe_workset_merge_affected_start_keys | 187,473 |
| sim_safe_workset_merge_unique_start_keys | 185,280 |
| sim_safe_workset_merge_duplicate_states | 0 |
| safe_store_size_before | 6,261,830 |
| safe_store_size_after_erase | 6,075,899 |
| safe_store_size_after_upsert | 6,261,179 |
| safe_store_size_after_prune | 3,094,987 |
| safe_store_erase_scanned_states | 6,261,830 |
| safe_store_erased_states | 185,931 |
| erase_index_entries_before | 6,261,830 |
| erase_index_entries_after | 6,075,899 |
| prune_scanned_states | 6,261,179 |
| prune_removed_states | 3,166,192 |
| prune_kept_states | 3,094,987 |
| prune_index_entries_before | 6,261,179 |
| prune_index_entries_after | 3,094,987 |

Derived shape:

```text
erased states / affected starts = 0.991775
prune removed ratio            = 50.5686%
returned duplicate states      = 0
```

Returned states are still unique. There is no evidence for duplicate-state
skip or upload/handoff reduction as the next target.

## Tombstone Estimates

Always-on first-order estimates from the current path:

| Field | Median |
| --- | ---: |
| tombstone_est_mark_ops | 187,473 |
| tombstone_est_erase_scan_states_saved | 6,074,489 |
| tombstone_est_erase_index_entries_saved | 6,075,899 |

The scan-saved estimate is `97.01%` of the current erase full-store scan:

```text
current erase scans         = 6,261,830 states
estimated tombstone marks   = 187,473 affected starts
estimated scan states saved = 6,074,489
```

This is only an estimate. A real tombstone/generation path would still need to
preserve safe-store ordering, hostEpoch semantics, lookup semantics, prune
authority, and GPU safe-store handoff behavior.

## Shadow Run

With `LONGTARGET_SIM_CUDA_SAFE_STORE_MERGE_STRUCTURE_SHADOW=1`:

| Field | Value |
| --- | ---: |
| sim_safe_store_merge_shadow_calls | 515 |
| sim_safe_store_merge_shadow_seconds | 1.22445 |
| sim_safe_store_merge_shadow_digest_mismatches | 0 |
| sim_safe_store_merge_shadow_size_mismatches | 0 |
| sim_safe_store_merge_shadow_candidate_mismatches | 0 |
| sim_safe_store_merge_shadow_order_mismatches | 0 |
| sim_safe_store_merge_shadow_est_current_scanned_states | 12,523,009 |
| sim_safe_store_merge_shadow_est_compact_scanned_states | 6,447,110 |
| sim_safe_store_merge_shadow_est_saved_scans | 6,075,899 |
| sim_safe_store_merge_shadow_est_tombstone_mark_ops | 187,473 |
| sim_safe_store_merge_shadow_est_tombstone_erase_scan_states_saved | 6,074,489 |
| sim_safe_store_merge_shadow_est_tombstone_erase_index_entries_saved | 6,075,899 |
| sim_safe_store_merge_shadow_prune_removed_ratio | 0.505686 |

The shadow run is correctness and estimate telemetry only. Its runtime should
not be used as a performance datapoint because the diagnostic copy/rebuild work
is deliberately extra work after the authoritative merge.

## Boundary Checks

The best-path runs reported:

```text
sim_initial_safe_store_gpu_precombine_prune_fallbacks=0
sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

The shadow run additionally reported:

```text
sim_safe_store_merge_shadow_digest_mismatches=0
sim_safe_store_merge_shadow_size_mismatches=0
sim_safe_store_merge_shadow_candidate_mismatches=0
sim_safe_store_merge_shadow_order_mismatches=0
```

## Answers

1. Affected-start erase is around `0.64s` because the current path rebuilds the
   multi-million-entry safe-store start index after erase. The scan/lookup loop
   is only about `0.066s`; index rebuild is about `0.569s`.

2. The current sample erases `185,931` states for `187,473` affected starts, or
   about `0.992` states per affected start.

3. Prune index rebuild is structurally required for the current vector + map
   representation after compaction. It is not proven avoidable without a
   different representation or deferred-index strategy.

4. A tombstone/generation strategy is promising enough for a shadow/reduction
   design PR: it could replace a full-store erase scan with affected-start marks
   and defer the erase index rebuild. It is not proven safe as a real path yet.

5. The next real investigation should be a default-off safe-store
   tombstone/deferred-index shadow or structure design. If that cannot preserve
   hostEpoch/index/order/upload semantics locally, pivot to safe-window geometry.

