# CUDA exact frontier safe-store epoch contract

Date: 2026-05-10

Base: `cuda-exact-frontier-chunk-boundary-contract-gapfill`

This is a docs-only design note for the safe-store epoch gap in the future GPU
exact ordered frontier replay shadow contract. It does not implement GPU
replay, does not route through `ordered_segmented_v3`, does not report
`gpu_real` authority, and does not make the clean shadow gate active.

## Contract meaning

For exact frontier replay, a safe-store epoch is a freshness token for the
authoritative safe-store state consumed by replay, upload, handoff, locate, and
`safe_workset` code. The epoch must distinguish two stores that may have the
same active flag shape but were produced by different rebuild, prune, upload, or
refresh events.

The contract needs to separate these meanings:

- Host authoritative store freshness: whether the CPU `SimCandidateStateStore`
  seen by replay is the same generation that later comparison expects.
- GPU mirrored handle freshness: whether a persistent device handle still
  mirrors the host store and cached frontier state it claims to represent.
- Stale invalidation: whether a handoff or locate path rejected a device store
  because the CPU/GPU state relationship is no longer fresh.
- Refresh/prune/upload generation: whether mutations that rebuild, prune, or
  upload the store advanced an observable generation.
- Consumption safety: whether `locate` and `safe_workset` are reading a store
  whose generation matches the replay boundary being validated.

Digest equality can help validate contents, but it is not an epoch. An epoch is
about freshness and ordering across mutations; a digest is about content at one
observation point.

## Inventory

| Concept | Existing key/helper | Status |
| --- | --- | --- |
| CPU safe-store digest | `simCandidateStateStoreFingerprint(context.safeCandidateStateStore)` | Available as a CPU baseline when the host store is valid. |
| CPU safe-store epoch | none on `SimCandidateStateStore` | Missing; keep `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available=0`. |
| GPU safe-store handle active | `SimCudaPersistentSafeStoreHandle::valid`, `stateCount`, `frontierValid` | Device-handle availability only; not host replay epoch proof. |
| GPU safe-store handle generation | `SimCudaPersistentSafeStoreHandle::telemetryEpoch` | Related device telemetry; bumped on handle/frontier-cache mutations, not a CPU authoritative epoch. |
| stale safe-store invalidation | `benchmark.sim_initial_safe_store_handoff_rejected_stale_epoch` | Existing handoff diagnostic; not exact frontier CPU-vs-shadow epoch comparison. |
| frontier cache synchronized | `markSimGpuFrontierCacheSynchronized`, `gpuFrontierCacheInSync` | Cache usability flag; not an epoch or generation counter. |
| safe-store upload generation | `sim_scan_cuda_upload_persistent_safe_candidate_state_store` bumps handle `telemetryEpoch` | Device upload telemetry only unless paired with a host generation. |
| clean gate epoch support | `benchmark.sim_initial_exact_frontier_shadow_has_safe_store_epoch_check=0` | Correctly unsupported until an actual CPU-vs-shadow epoch comparison exists. |
| missing CPU-vs-shadow epoch compare | none | Do not emit safe-store epoch mismatch counters. |

## Why CPU epoch is unavailable

The host authoritative `SimCandidateStateStore` currently contains only
`valid`, `states`, and `startCoordToIndex`. Its mutation helpers reset, upsert,
prune, and rebuild the index without recording a generation counter.

The existing CPU safe-store digest is useful, but it cannot answer whether two
observations happened in the same store generation. Equal digest values can
occur after distinct mutation sequences, and unequal digest values do not say
which replay boundary or upload made the store stale.

The existing GPU handle `telemetryEpoch` is also insufficient as a CPU epoch. It
tracks persistent device-handle and cached-frontier changes. It is useful for
device-side freshness diagnostics and scheduler shape hashing, but it cannot
prove the host replay store generation unless the host store also exposes a
generation and upload links the two.

Active/stale flags are not enough either. A valid host store, a valid device
handle, or a synchronized frontier cache can prove availability, but not the
exact replay-boundary generation that should be compared.

## Candidate designs

### A. Host store generation counter

Add a `generation` field to `SimCandidateStateStore` and increment it on every
store mutation that can affect replay or handoff freshness: reset, rebuild from
summaries, upsert, prune, and any upload-affecting refresh.

Pros:
- Provides a true CPU authoritative epoch.
- Gives future shadow work a stable value to compare at replay boundaries.
- Separates freshness from content digest.

Cons:
- Requires touching safe-store mutation semantics.
- Needs careful rules for index-only rebuilds versus content mutations.
- Must be threaded into upload and invalidation telemetry to be useful.

### B. Digest-as-epoch surrogate

Use the safe-store digest plus store size and candidate count as a freshness
surrogate.

Pros:
- Cheap because the digest helper already exists.
- Avoids changing the host store data structure.

Cons:
- Not an epoch; it cannot represent mutation ordering or boundary freshness.
- Can hide distinct rebuild/upload generations with identical content.
- Should only be documented as a digest baseline, not reported as epoch
  availability.

### C. Device handle epoch

Use `SimCudaPersistentSafeStoreHandle::telemetryEpoch` as the device-side
generation for uploads, handle refreshes, and frontier-cache updates.

Pros:
- Already exists for the persistent GPU safe-store handle.
- Moves when device-handle state changes.
- Useful for locate, `safe_workset`, and scheduler diagnostics.

Cons:
- Not authoritative for the CPU host store.
- Cannot prove that an uploaded handle mirrors the intended host replay
  generation without a host epoch.
- Does not cover CPU-only replay boundaries.

### D. Combined contract

Define the future exact frontier shadow contract around separate freshness
components:

- `host_epoch`: CPU authoritative safe-store generation, if implemented.
- `host_digest`: CPU authoritative safe-store content digest.
- `device_epoch`: persistent GPU safe-store handle generation.
- `stale_generation`: generation or rejection marker for invalidated handoffs.
- `upload_generation`: host-to-device link recording which host generation was
  uploaded into which device epoch.

This is the preferred long-term design because it keeps content equality,
host freshness, device freshness, and stale invalidation separate.

## Recommended minimal contract

Future shadow work should require:

- CPU safe-store digest availability, already represented by
  `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_digest_available`.
- CPU safe-store epoch availability or an explicit unavailable field, currently
  `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available=0`.
- GPU device safe-store handle epoch reporting if a shadow backend consumes a
  persistent device handle.
- Observable stale invalidation for any path that can reuse device safe-store
  state across replay, locate, or `safe_workset`.
- No safe-store epoch mismatch counter unless there is an actual CPU-vs-shadow
  comparison over comparable epoch values.

The clean shadow gate must therefore remain:

```text
active=0
supported=0
missing_contract_counters=1
```

Safe-store digest availability and device `telemetryEpoch` do not satisfy the
epoch contract by themselves.

## Non-goals

This stage must not:

- fake `cpu_safe_store_epoch_available=1`,
- use digest alone and call it epoch,
- activate the clean shadow gate,
- route through `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY`,
- route through `ordered_segmented_v3` or produce `gpu_real` authority,
- change safe-store update, prune, upload, handoff, or stale invalidation
  behavior,
- rely on aggregate frontier mismatch as epoch proof.

## Next implementation options

If the contract needs a real epoch before shadow execution, the next PR should
design and add host safe-store epoch telemetry without changing replay
semantics. If epoch can remain an explicit design gap, the next PR can be a
minimal one-chunk GPU replay shadow design or stub that still reports the clean
gate as inactive and unsupported.
