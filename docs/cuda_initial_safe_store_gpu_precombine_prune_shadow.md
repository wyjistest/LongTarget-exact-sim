# CUDA Initial Safe-Store GPU Precombine Prune Shadow

This document records the default-off diagnostic shadow for pruning the
GPU-precombined initial safe store on device.

## Scope

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_SHADOW=1` runs after
the existing CPU-authoritative initial safe-store prune. The shadow takes the
pre-prune safe-store states, applies the same prune predicate on GPU, downloads
the kept states, and compares them with the CPU authoritative post-prune store.

The prune predicate is intentionally the existing CPU predicate:

```text
keep if state.score > runningMin
keep if state.startCoord is still present in the final frontier
```

The shadow is diagnostic only. It does not feed production safe-store contents,
upload, locate, region, output, or the exact-frontier clean gate. CPU prune and
CPU upload remain authoritative.

## Current Sample Signal

Fresh sample CUDA SIM region-locate with resident precombine plus prune shadow:

| item | value |
| --- | ---: |
| input states | 8,831,091 |
| kept states | 3,311,201 |
| removed states | 5,519,890 |
| removed ratio | 0.625052 |
| estimated D2H before prune | 317,919,276 bytes |
| estimated D2H after prune | 119,203,236 bytes |
| estimated D2H saved | 198,716,040 bytes |
| shadow seconds | 0.104496 |
| size mismatches | 0 |
| candidate mismatches | 0 |
| order mismatches | 0 |
| digest mismatches | 0 |

This is a D2H slimming proof, not a real path. The current shadow still uploads
the pre-prune states to the CUDA helper for diagnosis. A later real opt-in can
avoid that diagnostic upload by keeping the GPU-precombined states resident and
feeding the kept states into the existing CPU-authoritative post-prune/upload
handoff only after validation.

## Telemetry

The benchmark log emits:

```text
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_enabled
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_calls
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_input_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_kept_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_removed_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_removed_ratio
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_est_d2h_bytes_before
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_est_d2h_bytes_after
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_est_d2h_bytes_saved
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_size_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_candidate_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_order_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_shadow_digest_mismatches
```

## Validation

Run:

```bash
make check-sim-initial-safe-store-gpu-precombine-prune-shadow
```

Normal benchmark telemetry keeps the shadow disabled and checks zeroed default
fields through:

```bash
make check-benchmark-telemetry
```

## Non-Goals

- No default behavior change.
- No real GPU-pruned safe-store path.
- No CPU prune, upload, locate, or region authority change.
- No candidate replay changes.
- No exact frontier clean gate activation.
- No `gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.
