# CUDA Initial Safe-Store GPU Precombine Opt-In

This document records the default-off real opt-in for the initial safe-store
update bottleneck.

## Scope

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1` uses the CUDA
unique-start precombine result as the input to the initial host safe-store
update. It replaces replaying all initial summaries through the CPU safe-store
update loop with applying one precombined state per unique start.

CPU remains authoritative after that point. The existing CPU prune, upload,
locate, and region paths still consume the host safe store. The opt-in does not
change candidate replay, final output, exact-frontier clean gate status,
`gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## Validation Mode

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_VALIDATE=1` builds the
legacy CPU update result on a side store and compares it with the
GPU-precombined update before accepting the opt-in store. The comparison covers
store size, candidate content, first-seen order, and safe-store digest.

If validation mismatches appear, the path records mismatch and fallback
telemetry, then runs the legacy CPU summary update. The validation side store is
diagnostic only and does not feed prune, upload, locate, or region.

## Current Sample A/B

Fresh sample CUDA SIM region-locate runs report:

| mode | update s | prune s | rebuild s | initial scan s | sim s | total s | gpu s | validate s | fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 2.18771 | 0.729365 | 2.91708 | 8.66062 | 13.2627 | 15.3441 | 0 | 0 | 0 |
| GPU precombine | 1.89648 | 0.714702 | 2.61119 | 8.14095 | 12.8808 | 15.018 | 0.652199 | 0 | 0 |
| GPU precombine + validate | 6.88146 | 0.874295 | 7.75575 | 13.8343 | 18.6388 | 20.7233 | 0.546278 | 4.49781 | 0 |

The non-validating opt-in reduces the measured initial store rebuild in this
sample while preserving exact output. Validation mode is intentionally more
expensive because it builds the legacy CPU side store for comparison.

## Shape

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
| fallbacks | 0 |

The first real opt-in still uploads the materialized host summaries to the CUDA
helper, so the 1.43 GB H2D cost is reported honestly. A later optimization can
target GPU-resident summary reuse without changing this contract.

## Telemetry

The benchmark log emits:

```text
benchmark.sim_initial_safe_store_gpu_precombine_requested
benchmark.sim_initial_safe_store_gpu_precombine_active
benchmark.sim_initial_safe_store_gpu_precombine_validate_enabled
benchmark.sim_initial_safe_store_gpu_precombine_calls
benchmark.sim_initial_safe_store_gpu_precombine_seconds
benchmark.sim_initial_safe_store_gpu_precombine_input_summaries
benchmark.sim_initial_safe_store_gpu_precombine_unique_states
benchmark.sim_initial_safe_store_gpu_precombine_est_saved_upserts
benchmark.sim_initial_safe_store_gpu_precombine_h2d_bytes
benchmark.sim_initial_safe_store_gpu_precombine_d2h_bytes
benchmark.sim_initial_safe_store_gpu_precombine_validate_seconds
benchmark.sim_initial_safe_store_gpu_precombine_size_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_candidate_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_order_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_digest_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_fallbacks
```

## Validation

Run:

```bash
make check-sim-initial-safe-store-gpu-precombine
make check-sim-initial-safe-store-gpu-precombine-validate
```

Normal benchmark telemetry keeps the opt-in disabled and checks zeroed default
fields through:

```bash
make check-benchmark-telemetry
```

## Non-Goals

- No default behavior change.
- No CPU prune, upload, locate, or region authority change.
- No candidate replay changes.
- No exact frontier clean gate activation.
- No `gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.
