# CUDA Initial Safe-Store GPU Precombine Shadow

This document records the default-off diagnostic shadow for the initial
safe-store update bottleneck.

## Scope

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_SHADOW=1` runs a CUDA
unique-start precombine over the initial run summaries and compares the result
with the CPU-authoritative post-update safe store.

This is a shadow-only diagnostic. It does not replace CPU safe-store update, does
not feed pruning or upload, does not affect locate or region, and does not change
production authority.

## Current Sample Result

The sample CUDA SIM region-locate target reports:

| item | value |
| --- | ---: |
| input summaries | 44,777,038 |
| GPU unique states | 8,831,091 |
| estimated saved upserts | 35,945,947 |
| H2D bytes | 1,432,865,216 |
| D2H bytes | 317,919,276 |
| size mismatches | 0 |
| candidate mismatches | 0 |
| order mismatches | 0 |
| digest mismatches | 0 |

The helper preserves CPU safe-store first-seen order for comparison, so
`order_mismatches=0` means the downloaded unique states match the authoritative
post-update store order as well as its content digest.

## Telemetry

The benchmark log emits:

```text
benchmark.sim_initial_safe_store_gpu_precombine_shadow_enabled
benchmark.sim_initial_safe_store_gpu_precombine_shadow_calls
benchmark.sim_initial_safe_store_gpu_precombine_shadow_seconds
benchmark.sim_initial_safe_store_gpu_precombine_shadow_input_summaries
benchmark.sim_initial_safe_store_gpu_precombine_shadow_unique_states
benchmark.sim_initial_safe_store_gpu_precombine_shadow_est_saved_upserts
benchmark.sim_initial_safe_store_gpu_precombine_shadow_h2d_bytes
benchmark.sim_initial_safe_store_gpu_precombine_shadow_d2h_bytes
benchmark.sim_initial_safe_store_gpu_precombine_shadow_size_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_shadow_candidate_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_shadow_order_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_shadow_digest_mismatches
```

## Validation

Run:

```bash
make check-sim-initial-safe-store-gpu-precombine-shadow
```

Normal benchmark telemetry keeps the shadow disabled and checks zeroed default
fields through:

```bash
make check-benchmark-telemetry
```

## Non-Goals

- No production safe-store authority change.
- No CPU safe-store update replacement.
- No candidate replay changes.
- No prune, upload, locate, or region changes.
- No exact frontier clean gate activation.
- No `gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.
