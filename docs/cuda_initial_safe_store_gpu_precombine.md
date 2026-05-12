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

## GPU-Pruned Real Opt-In

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1` keeps the same
default-off boundary but moves the safe-store prune predicate into the CUDA
precombine helper. With resident summaries available, the path is:

```text
GPU resident summaries
-> GPU unique-start precombine
-> GPU safe-store prune predicate
-> D2H kept states only
-> host safe-store materialization / index rebuild
-> existing upload, locate, and region path
```

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_VALIDATE=1` builds
the legacy CPU post-prune safe store on a side context and compares size,
candidate content, first-seen order, and digest before accepting the
GPU-pruned host store. A mismatch records the prune mismatch/fallback counters
and falls back to the legacy CPU update/prune path.

Fresh sample telemetry for the non-validating resident prune opt-in:

| item | value |
| --- | ---: |
| unique input states | 8,831,091 |
| kept states | 3,311,201 |
| removed states | 5,519,890 |
| removed ratio | 0.625052 |
| D2H bytes | 119,203,236 |
| D2H bytes saved vs all unique states | 198,716,040 |
| prune mismatches | 0 |
| prune fallbacks | 0 |

The path is a real opt-in for initial safe-store materialization only. It does
not make GPU precombine or GPU prune the default, does not change candidate
replay, and does not activate the exact-frontier clean gate.

## Packed Kept-State D2H Measurement

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H=1`
adds a default-off measurement for packing only the kept states after GPU prune.
It is only meaningful with the resident GPU precombine prune path enabled:

```text
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H=1
```

The measurement packs each kept `SimScanCudaCandidateState` from 36 bytes to a
20-byte record when all coordinates fit in 16 bits, downloads that packed
payload, unpacks it on host, and compares size, candidate values, order, and
digest against the existing unpacked kept-state D2H result. The authoritative
host safe-store materialization still uses the unpacked kept-state vector in
this PR; packed mismatches or non-fitting states record packed fallback
telemetry and do not change output, upload, locate, region, or clean-gate
behavior.

Fresh sample telemetry:

| item | value |
| --- | ---: |
| kept states | 3,311,201 |
| unpacked kept-state D2H | 119,203,236 bytes |
| packed kept-state D2H | 66,224,020 bytes |
| estimated packed bytes saved | 52,979,216 bytes |
| packed fallbacks | 0 |
| packed size/candidate/order/digest mismatches | 0 |

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H_REAL=1`
uses the packed kept-state payload as the opt-in host safe-store materialization
source. With the resident GPU precombine prune path enabled, the real path is:

```text
GPU resident summaries
-> GPU unique-start precombine
-> GPU safe-store prune predicate
-> GPU pack kept states
-> D2H packed kept states only
-> host unpack / materialize safe-store / rebuild index
-> existing upload, locate, and region path
```

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H_VALIDATE=1`
adds a validation side path that also downloads the unpacked kept states and
compares them with the packed-materialized host states. Validation mismatches
record packed mismatch/fallback telemetry and fall back to the unpacked
kept-state path. Validation adds extra D2H and is not the performance path.

Fresh sample telemetry for packed real:

| item | value |
| --- | ---: |
| kept states | 3,311,201 |
| packed real active | 1 |
| packed D2H bytes | 66,224,020 |
| unpacked D2H bytes elided | 119,203,236 |
| packed bytes saved vs unpacked kept states | 52,979,216 |
| packed fallbacks | 0 |
| packed size/candidate/order/digest mismatches | 0 |

## Prune Shadow Follow-Up

`LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_SHADOW=1` adds a
separate diagnostic-only proof for the next slimming step. It applies the
existing safe-store prune predicate on GPU to the pre-prune unique states,
downloads the kept states, and compares them with the CPU authoritative
post-prune store. The sample shadow keeps 3,311,201 of 8,831,091 states and
estimates D2H shrinking from 317,919,276 bytes to 119,203,236 bytes, with zero
size, candidate, order, or digest mismatches. See
`docs/cuda_initial_safe_store_gpu_precombine_prune_shadow.md`.

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
benchmark.sim_initial_safe_store_gpu_precombine_prune_requested
benchmark.sim_initial_safe_store_gpu_precombine_prune_active
benchmark.sim_initial_safe_store_gpu_precombine_prune_validate_enabled
benchmark.sim_initial_safe_store_gpu_precombine_prune_calls
benchmark.sim_initial_safe_store_gpu_precombine_prune_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_input_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_kept_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_removed_states
benchmark.sim_initial_safe_store_gpu_precombine_prune_removed_ratio
benchmark.sim_initial_safe_store_gpu_precombine_prune_d2h_bytes
benchmark.sim_initial_safe_store_gpu_precombine_prune_d2h_bytes_saved
benchmark.sim_initial_safe_store_gpu_precombine_prune_validate_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_size_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_order_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_digest_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_fallbacks
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_requested
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_active
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_supported
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_disabled_reason
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes
benchmark.sim_initial_safe_store_gpu_precombine_prune_unpacked_d2h_bytes
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_bytes_saved
benchmark.sim_initial_safe_store_gpu_precombine_prune_pack_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_unpack_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_unpack_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_fallbacks
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_size_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_candidate_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_order_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_digest_mismatches
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_real_requested
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_real_active
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_d2h_validate_enabled
benchmark.sim_initial_safe_store_gpu_precombine_prune_unpacked_d2h_bytes_elided
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_materialize_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_index_rebuild_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_host_apply_seconds
benchmark.sim_initial_safe_store_gpu_precombine_prune_packed_validate_seconds
```

`benchmark.sim_initial_safe_store_gpu_precombine_input_source` is `none` when
the opt-in does not run, `host_h2d` for the materialized-summary upload path,
and `device_resident` when the resident source is active. The resident-source
disabled reason is `not_requested`, `active`, `resident_source_unavailable`, or
`not_run`.

For the packed real opt-in, `packed_unpack_seconds` is the host unpack time
reported by the packed kept-state D2H helper, `packed_materialize_seconds` is
the subsequent host safe-store materialization time, `packed_index_rebuild_seconds`
is the index rebuild slice inside materialization, and
`packed_host_apply_seconds` is `packed_unpack_seconds + packed_materialize_seconds`.
These fields characterize the remaining host-side cost only; they do not change
the default path or make packed D2H a recommended/default mode.
See `docs/cuda_initial_safe_store_packed_real_characterization.md` for the
current 3-run sample A/B and interpretation.

## Validation

Run:

```bash
make check-sim-initial-safe-store-gpu-precombine
make check-sim-initial-safe-store-gpu-precombine-validate
make check-sim-initial-safe-store-gpu-precombine-resident
make check-sim-initial-safe-store-gpu-precombine-prune
make check-sim-initial-safe-store-gpu-precombine-prune-validate
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h-real
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h-real-validate
```

Normal benchmark telemetry keeps the opt-in disabled and checks zeroed default
fields through:

```bash
make check-benchmark-telemetry
```

## Non-Goals

- No default behavior change.
- No upload, locate, or region authority change.
- No candidate replay changes.
- No exact frontier clean gate activation.
- No `gpu_real`, `ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY` route.
