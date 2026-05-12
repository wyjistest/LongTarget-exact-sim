# CUDA Safe-Workset Deferred-Index Real Opt-In

Base branch:

```text
cuda-safe-workset-deferred-index-shadow
```

This PR adds a default-off real opt-in:

```text
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX=1
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_VALIDATE=1
```

The default path is unchanged.

## Goal

PR #38 showed that safe-workset safe-store merge can be represented as:

```text
filter affected starts
upsert returned states
prune
rebuild safe-store index once at final commit
```

This PR makes that shape a real opt-in for safe-workset host merge. It replaces
the legacy two-index-rebuild sequence:

```text
erase affected starts -> rebuild index
upsert returned states
prune -> rebuild index
```

with one final index rebuild. CPU host safe-store remains authoritative.

## Validation

With validation enabled, the implementation builds the legacy two-rebuild
safe-store result on a side context and compares:

```text
size
candidate values
order
digest
index entry count
kept count
removed count
```

Any mismatch records telemetry and falls back to the legacy side-store result.

## Boundary

This PR does not change:

```text
default behavior
region dispatch
safe-window planner authority
initial safe-store GPU best path
candidate/frontier replay
clean frontier gate
gpu_real / ordered_segmented_v3 / EXACT_FRONTIER_REPLAY routes
```

## Sample A/B

Mode:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

Single-run sample:

| Mode | total_seconds | sim_seconds | safe_workset_merge | safe_workset_total |
| --- | ---: | ---: | ---: | ---: |
| best path legacy | 13.6144 | 11.2870 | 1.17270 | 3.90254 |
| best path + deferred index | 13.7638 | 11.6983 | 1.10075 | 4.27110 |
| best path + deferred index + validate | 16.4663 | 14.2315 | 3.57890 | 6.87444 |

The real opt-in removes the erase-side index rebuild in the sampled run:

```text
legacy erase index rebuild = 0.570869s
legacy prune index rebuild = 0.311218s
real erase index rebuild   = 0
real final index rebuild   = 0.251276s
```

The validation mode is a correctness gate, not a performance mode.

## Real Opt-In Telemetry

Best path + deferred index:

```text
sim_safe_workset_deferred_index_requested=1
sim_safe_workset_deferred_index_active=1
sim_safe_workset_deferred_index_validate_enabled=0
sim_safe_workset_deferred_index_calls=515
sim_safe_workset_deferred_index_legacy_index_rebuilds=1030
sim_safe_workset_deferred_index_actual_index_rebuilds=515
sim_safe_workset_deferred_index_index_rebuilds_saved=515
sim_safe_workset_deferred_index_fallbacks=0
```

Best path + deferred index + validate:

```text
sim_safe_workset_deferred_index_size_mismatches=0
sim_safe_workset_deferred_index_candidate_mismatches=0
sim_safe_workset_deferred_index_order_mismatches=0
sim_safe_workset_deferred_index_digest_mismatches=0
sim_safe_workset_deferred_index_index_entry_mismatches=0
sim_safe_workset_deferred_index_kept_count_mismatches=0
sim_safe_workset_deferred_index_removed_count_mismatches=0
sim_safe_workset_deferred_index_fallbacks=0
```

Boundary:

```text
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

## Interpretation

The real opt-in is exact-clean on the sample and matrix checks and removes one
safe-store index rebuild per safe-workset merge call. It is still not a default
candidate: the single-run wall-clock result is noisy, and validation mode is
intentionally expensive because it builds the legacy side result.

The next step after review is a 3-run median A/B before deciding whether this
should become a recommended opt-in.
