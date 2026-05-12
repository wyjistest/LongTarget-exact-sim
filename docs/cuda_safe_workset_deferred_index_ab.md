# CUDA Safe-Workset Deferred-Index A/B

Base branch:

```text
cuda-safe-workset-deferred-index-real
```

Base commit:

```text
6fac1aa
```

This is a docs-only characterization PR. It does not add a new runtime path,
default deferred-index, change region dispatch, change safe-window planner
authority, activate the clean frontier gate, or route through `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## Goal

PR #39 added a default-off real opt-in:

```text
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX=1
LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_VALIDATE=1
```

The single-run result was exact-clean but did not prove a wall-clock win. This
document records a 3-run median A/B under the recommended safe-store GPU best
path before deciding whether deferred-index should become a recommended opt-in.

## Modes

All runs used the recommended safe-store GPU best path:

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

The A/B modes were:

| Mode | Extra env |
| --- | --- |
| best path legacy | none |
| best path + deferred index | `LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX=1` |
| best path + deferred index + validate | `LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX=1 LONGTARGET_SIM_CUDA_SAFE_WORKSET_DEFERRED_INDEX_VALIDATE=1` |

Run logs:

```text
.tmp/cuda_deferred_index_ab_legacy_r1/stderr.log
.tmp/cuda_deferred_index_ab_legacy_r2/stderr.log
.tmp/cuda_deferred_index_ab_legacy_r3/stderr.log
.tmp/cuda_deferred_index_ab_real_r1/stderr.log
.tmp/cuda_deferred_index_ab_real_r2/stderr.log
.tmp/cuda_deferred_index_ab_real_r3/stderr.log
.tmp/cuda_deferred_index_ab_validate_r1/stderr.log
.tmp/cuda_deferred_index_ab_validate_r2/stderr.log
.tmp/cuda_deferred_index_ab_validate_r3/stderr.log
```

## Core Medians

| Field | Legacy | Deferred index | Deferred index + validate |
| --- | ---: | ---: | ---: |
| total_seconds | 13.5224 | 13.4932 | 15.8509 |
| sim_seconds | 11.4548 | 11.4676 | 13.8145 |
| sim_safe_workset_total_seconds | 4.27818 | 4.15273 | 6.51894 |
| sim_safe_workset_merge_seconds | 1.15953 | 1.10033 | 3.53469 |
| sim_region_scan_gpu_seconds | 2.70936 | 2.47525 | 2.48973 |
| sim_region_d2h_seconds | 0.627432 | 0.636395 | 0.677864 |

Median deltas versus legacy:

| Field | Deferred index | Deferred index + validate |
| --- | ---: | ---: |
| total_seconds | -0.0292 | +2.3285 |
| sim_seconds | +0.0128 | +2.3597 |
| sim_safe_workset_total_seconds | -0.12545 | +2.24076 |
| sim_safe_workset_merge_seconds | -0.0592 | +2.37516 |
| sim_region_scan_gpu_seconds | -0.23411 | -0.21963 |
| sim_region_d2h_seconds | +0.008963 | +0.050432 |

## Merge Structure Medians

| Field | Legacy | Deferred index | Deferred index + validate |
| --- | ---: | ---: | ---: |
| safe_store_upsert_seconds | 0.645739 | 0.0910596 | 0.0851953 |
| safe_store_erase_seconds | 0.630099 | 0.0799781 | 0.0743892 |
| safe_store_erase_index_rebuild_seconds | 0.56186 | 0 | 0 |
| safe_store_prune_seconds | 0.457056 | 0.655932 | 3.06295 |
| safe_store_prune_index_rebuild_seconds | 0.31118 | 0.25433 | 0.24844 |
| deferred_index_seconds | 0 | 0.655799 | 2.98969 |
| deferred_index_legacy_validate_seconds | 0 | 0 | 1.55887 |

The real opt-in removes the erase-side index rebuild and still performs one
final index rebuild during prune/final commit:

| Field | Legacy | Deferred index | Deferred index + validate |
| --- | ---: | ---: | ---: |
| deferred_index_calls | 0 | 515 | 515 |
| legacy_index_rebuilds | 0 | 1,030 | 1,030 |
| actual_index_rebuilds | 0 | 515 | 515 |
| index_rebuilds_saved | 0 | 515 | 515 |

Validation mode is intentionally expensive because it builds the legacy
two-rebuild side result and compares it against the deferred-index result. It
is a correctness mode, not a performance mode.

## Per-Run Core Results

| Mode | Run | total_seconds | sim_seconds | safe_workset_total | safe_workset_merge | region_gpu | region_d2h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 1 | 13.5536 | 11.4548 | 4.27818 | 1.17076 | 2.70936 | 0.627432 |
| legacy | 2 | 13.5224 | 11.4629 | 4.38722 | 1.15953 | 2.83137 | 0.62222 |
| legacy | 3 | 13.2680 | 11.2283 | 4.17808 | 1.15692 | 2.63956 | 0.639777 |
| deferred index | 1 | 13.5189 | 11.4891 | 4.15273 | 1.11641 | 2.49035 | 0.594185 |
| deferred index | 2 | 13.4932 | 11.4676 | 4.18477 | 1.10033 | 2.47525 | 0.658683 |
| deferred index | 3 | 13.4183 | 11.3820 | 4.04981 | 1.09323 | 2.46858 | 0.636395 |
| deferred index + validate | 1 | 15.8370 | 13.8137 | 6.53451 | 3.53030 | 2.51550 | 0.677864 |
| deferred index + validate | 2 | 15.8509 | 13.8145 | 6.51894 | 3.54219 | 2.48973 | 0.629068 |
| deferred index + validate | 3 | 15.9155 | 13.8422 | 6.41268 | 3.53469 | 2.38862 | 0.679194 |

## Correctness And Boundary

Deferred-index real and validation runs reported:

```text
sim_safe_workset_deferred_index_active=1
sim_safe_workset_deferred_index_calls=515
sim_safe_workset_deferred_index_legacy_index_rebuilds=1030
sim_safe_workset_deferred_index_actual_index_rebuilds=515
sim_safe_workset_deferred_index_index_rebuilds_saved=515
sim_safe_workset_deferred_index_size_mismatches=0
sim_safe_workset_deferred_index_candidate_mismatches=0
sim_safe_workset_deferred_index_order_mismatches=0
sim_safe_workset_deferred_index_digest_mismatches=0
sim_safe_workset_deferred_index_index_entry_mismatches=0
sim_safe_workset_deferred_index_kept_count_mismatches=0
sim_safe_workset_deferred_index_removed_count_mismatches=0
sim_safe_workset_deferred_index_fallbacks=0
```

Boundary counters remained inactive:

```text
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_replay_enabled=0
```

No production authority or default behavior changes are part of this
characterization.

## Interpretation

Deferred-index remains exact-clean and removes one safe-store index rebuild per
safe-workset merge call. The local median moved in the expected direction:

```text
safe_workset_merge_seconds: 1.15953 -> 1.10033 (-0.0592s)
safe_workset_total_seconds: 4.27818 -> 4.15273 (-0.12545s)
```

However, the wall-clock signal is still too small to justify making it a
recommended opt-in:

```text
total_seconds: 13.5224 -> 13.4932 (-0.0292s)
sim_seconds:   11.4548 -> 11.4676 (+0.0128s)
```

The local merge slice improves, but the `sim_seconds` median does not. This
should stay an exact-clean default-off opt-in unless broader repeats or larger
workloads show a stable `sim_seconds` and `total_seconds` win.

## Decision

Current decision:

```text
correctness: clean
fallbacks: 0
local merge slice: improved
stable sim/total wall-clock win: not proven
recommended opt-in: no
default: no
```

If this line is revisited, the next evidence should be broader workload or
repeat coverage. Otherwise, pivot to safe-window geometry/coarsening shadow,
because region batching was ruled out by #35 and deferred-index only produced a
small local host-merge gain in this 3-run A/B.
