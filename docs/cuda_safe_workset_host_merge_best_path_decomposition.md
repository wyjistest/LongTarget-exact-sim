# CUDA Safe-Workset Host Merge Best-Path Decomposition

Base branch:

```text
cuda-region-best-path-launch-geometry
```

Base commit:

```text
0207dac
```

This is a telemetry and characterization PR. It does not optimize safe-workset
merge, skip states, change safe-store update/prune/upload behavior, change
region dispatch, enable true-batch, change safe-window planner authority,
default any GPU best-path env, activate the clean frontier gate, or route
through `gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## Goal

PR #35 ruled out region batching as the next step on the current sample:
`mergeable_calls=0` and `est_launch_reduction=0`. The next visible local slice
is safe-workset host merge, around `1.14s` in the safe-store GPU best path.

This pass decomposes that merge slice and adds one local telemetry field:

```text
benchmark.sim_safe_workset_merge_safe_store_prune_index_rebuild_seconds
```

The new field reuses the existing `pruneSimSafeCandidateStateStore(..., stats)`
index-rebuild timer inside the safe-workset merge path. It records timing only;
it does not change prune semantics.

## Mode

All sample runs used the recommended safe-store GPU best path:

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
.tmp/cuda_safe_workset_host_merge_best_path_r1/
.tmp/cuda_safe_workset_host_merge_best_path_r2/
.tmp/cuda_safe_workset_host_merge_best_path_r3/
```

## Top-Level Medians

| Field | Median | Range |
| --- | ---: | ---: |
| total_seconds | 12.8117 | 0.6879 |
| sim_seconds | 10.7308 | 0.4482 |
| calc_score_seconds | 1.74587 | 0.01763 |
| sim_initial_scan_seconds | 6.34286 | 0.32454 |
| sim_initial_store_rebuild_seconds | 0.856364 | 0.168224 |
| sim_safe_workset_total_seconds | 4.02879 | 0.03714 |
| sim_safe_workset_build_seconds | 0.330397 | 0.003255 |
| sim_safe_workset_merge_seconds | 1.15968 | 0.01739 |
| sim_region_scan_gpu_seconds | 2.47554 | 0.05032 |
| sim_region_d2h_seconds | 0.639483 | 0.039783 |
| sim_region_summary_bytes_d2h | 6,670,080 | 0 |

Safe-workset host merge is stable in these runs. Region GPU remains larger, but
PR #35 showed no conservative batching opportunity, so host merge is the next
local target.

## Host Merge Breakdown

| Field | Median | Range | Share of merge |
| --- | ---: | ---: | ---: |
| sim_safe_workset_merge_seconds | 1.15968 | 0.01739 | 100.00% |
| sim_safe_workset_merge_safe_store_upsert_seconds | 0.647244 | 0.014436 | 55.81% |
| sim_safe_workset_merge_safe_store_erase_seconds | 0.632624 | 0.014486 | 54.55% |
| sim_safe_workset_merge_safe_store_upsert_loop_seconds | 0.0147335 | 0.0001637 | 1.27% |
| sim_safe_workset_merge_safe_store_prune_seconds | 0.455938 | 0.003423 | 39.32% |
| sim_safe_workset_merge_safe_store_prune_index_rebuild_seconds | 0.305928 | 0.002009 | 26.38% |
| sim_safe_workset_merge_safe_store_upload_seconds | 0.0447138 | 0.000219 | 3.86% |
| sim_safe_workset_merge_candidate_apply_seconds | 0.00897141 | 0.0001088 | 0.77% |
| sim_safe_workset_merge_candidate_erase_seconds | 0.00335889 | 0.0001341 | 0.29% |
| sim_safe_workset_merge_materialize_seconds | 0.000048781 | 0.0000131 | 0.00% |

`safe_store_upsert_seconds` is the combined safe-store erase plus upsert-loop
timer. The data shows that erase dominates the upsert bucket; the actual
returned-state upsert loop is small.

Within prune, index rebuild is the largest exposed sub-slice:

```text
safe-store prune                         ~= 0.456s
safe-store prune index rebuild           ~= 0.306s
index rebuild share of safe-store prune  ~= 67.10%
```

## Merge Shape

| Field | Median |
| --- | ---: |
| sim_safe_workset_returned_states | 185,280 |
| sim_safe_workset_merge_unique_start_keys | 185,280 |
| sim_safe_workset_merge_duplicate_states | 0 |
| sim_safe_workset_merge_candidate_updates | 185,280 |
| sim_safe_workset_merge_safe_store_updates | 185,280 |
| sim_safe_workset_merge_residency_updates | 0 |
| sim_safe_workset_merge_affected_start_keys | 187,473 |
| returned states / affected starts | 0.988302 |

Returned states are unique by start key on this sample. There is no duplicate
pressure in the returned states, so duplicate-state skipping is not supported by
this evidence.

There is no direct value-level no-op telemetry in this PR. Adding such a counter
would require comparing returned states against existing candidate/safe-store
state values, which is a separate diagnostic and not needed to identify the
dominant merge stages here.

## Safe-Store Shape

| Field | Median |
| --- | ---: |
| sim_safe_workset_merge_safe_store_size_before | 6,261,830 |
| sim_safe_workset_merge_safe_store_size_after_erase | 6,075,899 |
| sim_safe_workset_merge_safe_store_size_after_upsert | 6,261,179 |
| sim_safe_workset_merge_safe_store_size_after_prune | 3,094,987 |
| sim_safe_workset_merge_prune_scanned_states | 6,261,179 |
| sim_safe_workset_merge_prune_removed_states | 3,166,192 |
| sim_safe_workset_merge_prune_kept_states | 3,094,987 |

Derived shape:

```text
states removed by affected-start erase = 185,931
states reinserted by returned upsert   = 185,280
states removed by prune                = 3,166,192
prune removed ratio                    ~= 50.57%
```

The host merge cost is therefore mostly safe-store maintenance over a multi-
million-state store: erase affected starts, reinsert returned states, then prune
and rebuild the safe-store index.

## Answers

1. The dominant host-merge sub-stage is safe-store maintenance. The largest
   reported bucket is safe-store erase/upsert at about `0.647s`, followed by
   safe-store prune at about `0.456s`.

2. Safe-store upsert/prune is still the main cost. Candidate apply, candidate
   erase, materialization, and upload are all small by comparison.

3. Returned states are unique, not duplicate-heavy:
   `returned_states=185,280`, `unique_start_keys=185,280`,
   `duplicate_states=0`.

4. Upload/handoff is not material at this stage. It is about `0.045s`, or
   roughly `3.9%` of host merge.

5. There is no evidence for duplicate skip. There is also no value-level no-op
   counter yet; this PR intentionally avoids adding one because it would require
   new semantic comparison logic. The useful opportunity is structural
   safe-store maintenance, especially prune/index rebuild.

6. The next PR should be a safe-workset safe-store merge/prune structure shadow,
   focused on whether the erase/upsert/prune/index sequence can be reduced or
   fused while preserving ordering, hostEpoch, prune semantics, and GPU
   safe-store handoff. Upload/handoff reduction and region D2H packing should
   stay lower priority for this sample.

## Boundary Checks

The collected best-path runs reported:

```text
sim_initial_safe_store_gpu_precombine_prune_fallbacks=0
sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_order_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_digest_mismatches=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

No production authority changed in this characterization.
