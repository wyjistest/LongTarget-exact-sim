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

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1` asks
the same real opt-in to consume the GPU-resident initial summary buffer produced
by the CUDA initial scan. When the resident buffer is available and its summary
count matches the CPU-visible summary vector, the helper skips the 44.8M-summary
host-to-device upload and only downloads the unique precombined states. If the
resident source is unavailable, the path falls back to the existing host-H2D
source and reports that fallback through resident-source telemetry.

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
| legacy | 2.19257 | 0.75571 | 2.94828 | 8.97514 | 13.7493 | 15.8051 | 0 | 0 | 0 |
| GPU precombine | 1.99814 | 0.70735 | 2.70549 | 8.17471 | 12.9241 | 15.0081 | 0.781556 | 0 | 0 |
| GPU precombine + validate | 6.43444 | 0.863345 | 7.29778 | 13.6019 | 18.3277 | 20.4041 | 0.395027 | 4.23816 | 0 |
| GPU precombine + resident source | 1.53962 | 0.724097 | 2.26372 | 7.86503 | 12.6762 | 14.7772 | 0.333206 | 0 | 0 |
| GPU precombine + resident source + validate | 6.57683 | 0.812232 | 7.38906 | 13.7357 | 18.1793 | 20.4215 | 0.544042 | 4.22082 | 0 |

The non-validating opt-in reduces the measured initial store rebuild in this
sample while preserving exact output. The resident-source opt-in removes the
1.43 GB summary H2D from this precombine stage, but still pays the unique-state
D2H cost and leaves CPU prune/upload authority unchanged. Validation mode is
intentionally more expensive because it builds the legacy CPU side store for
comparison.

## Shape

| item | value |
| --- | ---: |
| input summaries | 44,777,038 |
| GPU unique states | 8,831,091 |
| estimated saved upserts | 35,945,947 |
| host-H2D source H2D bytes | 1,432,865,216 |
| resident-source H2D bytes | 0 |
| resident-source H2D bytes saved | 1,432,865,216 |
| D2H bytes | 317,919,276 |
| size mismatches | 0 |
| candidate mismatches | 0 |
| order mismatches | 0 |
| digest mismatches | 0 |
| fallbacks | 0 |

The host-H2D source still uploads the materialized host summaries to the CUDA
helper, so the 1.43 GB H2D cost is reported honestly. The resident source
reuses the CUDA initial scan's summary buffer when available; otherwise it falls
back to the host-H2D source rather than changing production authority.

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
benchmark.sim_initial_safe_store_gpu_precombine_resident_source_requested
benchmark.sim_initial_safe_store_gpu_precombine_resident_source_active
benchmark.sim_initial_safe_store_gpu_precombine_resident_source_supported
benchmark.sim_initial_safe_store_gpu_precombine_resident_source_disabled_reason
benchmark.sim_initial_safe_store_gpu_precombine_summary_h2d_elided
benchmark.sim_initial_safe_store_gpu_precombine_summary_h2d_bytes_saved
benchmark.sim_initial_safe_store_gpu_precombine_input_source
```

`benchmark.sim_initial_safe_store_gpu_precombine_input_source` is `none` when
the opt-in does not run, `host_h2d` for the materialized-summary upload path,
and `device_resident` when the resident source is active. The resident-source
disabled reason is `not_requested`, `active`, `resident_source_unavailable`, or
`not_run`.

## Validation

Run:

```bash
make check-sim-initial-safe-store-gpu-precombine
make check-sim-initial-safe-store-gpu-precombine-validate
make check-sim-initial-safe-store-gpu-precombine-resident
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
