# CUDA Safe-Workset Deferred-Index Shadow

Base branch:

```text
cuda-safe-workset-safe-store-erase-index-structure
```

Base commit:

```text
e6806f7
```

This is a default-off diagnostic PR. It does not change the real safe-store
erase/prune path, skip erase, skip prune, use a shadow store as authority, change
region dispatch, change safe-window planner authority, default any GPU best-path
env, activate the clean frontier gate, or route through `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## Goal

PR #37 showed that safe-workset host merge is dominated by two safe-store index
rebuilds:

```text
erase index rebuild ~= 0.57s
prune index rebuild ~= 0.32s
```

This PR adds:

```text
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_SHADOW=1
```

The shadow tests whether the safe-store merge can be represented as:

```text
filter old states by affected-start
upsert returned states into a side store
apply the same prune predicate
rebuild safe-store index once at the end
compare against authoritative post-merge safe store
```

The real path remains:

```text
erase affected starts -> rebuild index
upsert returned states
prune -> rebuild index
```

## Implementation

The shadow is run after the existing authoritative merge. It receives a
pre-merge host safe-store snapshot and the already-materialized returned states,
then builds a side store. It uses a temporary map only for shadow upsert
semantics; the safe-store index in the side store is rebuilt once after prune.

It compares:

```text
size
candidate values
order
digest
index entry count
kept count
removed count
```

## Sample Run

Mode:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_SHADOW=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
OUTPUT_SUBDIR=cuda_safe_workset_deferred_index_shadow_best_path
./scripts/run_sample_exactness_cuda.sh
```

Log:

```text
.tmp/cuda_safe_workset_deferred_index_shadow_best_path/stderr.log
```

## Results

| Field | Value |
| --- | ---: |
| sim_safe_workset_deferred_index_shadow_enabled | 1 |
| sim_safe_workset_deferred_index_shadow_calls | 515 |
| sim_safe_workset_deferred_index_shadow_seconds | 1.78377 |
| sim_safe_workset_deferred_index_shadow_input_states | 6,261,830 |
| sim_safe_workset_deferred_index_shadow_returned_states | 185,280 |
| sim_safe_workset_deferred_index_shadow_affected_start_keys | 187,473 |
| sim_safe_workset_deferred_index_shadow_legacy_index_rebuilds | 1,030 |
| sim_safe_workset_deferred_index_shadow_shadow_index_rebuilds | 515 |
| sim_safe_workset_deferred_index_shadow_est_index_rebuilds_saved | 515 |
| sim_safe_workset_deferred_index_shadow_index_rebuild_seconds | 0.250787 |
| sim_safe_workset_deferred_index_shadow_est_seconds_saved | 0.586984 |
| sim_safe_workset_deferred_index_shadow_kept_states | 3,094,987 |
| sim_safe_workset_deferred_index_shadow_removed_states | 3,166,192 |
| sim_safe_workset_deferred_index_shadow_index_entries | 3,094,987 |

Per safe-workset merge call, this is the expected structural signal:

```text
legacy index rebuilds = 2
shadow index rebuilds = 1
estimated rebuilds saved = 1
```

The single sample estimates:

```text
legacy index rebuild seconds = 0.533641 + 0.304131 = 0.837772
shadow final index rebuild   = 0.250787
estimated seconds saved      = 0.586984
```

That estimated save is about `70.06%` of the measured legacy index rebuild
slice in this diagnostic run.

## Correctness

| Field | Value |
| --- | ---: |
| sim_safe_workset_deferred_index_shadow_size_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_candidate_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_order_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_digest_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_index_entry_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_kept_count_mismatches | 0 |
| sim_safe_workset_deferred_index_shadow_removed_count_mismatches | 0 |

Boundary checks:

```text
sim_initial_safe_store_gpu_precombine_prune_fallbacks=0
sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_order_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_digest_mismatches=0
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

## Interpretation

The shadow answers the #37 question: the erase/prune sequence can be represented
as one final safe-store index rebuild on this sample while preserving store
size, values, order, digest, index entry count, and prune kept/removed counts.

This does not prove a real path should be enabled. The shadow adds substantial
diagnostic work (`1.78377s`) and should not be used as a wall-clock performance
measurement. The useful result is the structural estimate: one safe-store index
rebuild per safe-workset merge can likely be removed if a real opt-in path can
preserve hostEpoch, order, prune, and GPU safe-store handoff semantics.

## Next Step

The next PR can be a default-off real opt-in only if it stays narrow:

```text
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX=1
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_VALIDATE=1
```

Validation should compare the real deferred-index materialized store against the
legacy post-merge store and fallback on any mismatch. If hostEpoch/index or GPU
safe-store upload semantics become ambiguous, stop and pivot to safe-window
geometry/coarsening instead.
