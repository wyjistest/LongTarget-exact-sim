# CUDA exact frontier host safe-store epoch telemetry

Date: 2026-05-10

Base: `cuda-exact-frontier-safe-store-epoch-design`

This PR adds telemetry-only host safe-store epoch coverage for the future GPU
exact ordered frontier replay shadow contract. It does not implement GPU
replay, does not route through `ordered_segmented_v3`, does not report
`gpu_real` authority, and does not make the clean shadow gate active.

## Inventory

| Concept | Existing key/helper | Action |
| --- | --- | --- |
| CPU safe-store digest | `simCandidateStateStoreFingerprint(context.safeCandidateStateStore)` | Unchanged; remains content fingerprint baseline. |
| CPU host epoch field | `SimCandidateStateStore::hostEpoch` | Added as host committed-state generation. |
| host reset / clear point | `resetSimContextSafeCandidateStateStoreAndRecordEpoch` | Bumps epoch for authoritative host-store reset/clear commits. |
| host update commit point | initial safe-store merge, chunked/pinned apply finalize, safe-workset refresh/merge | Bumps epoch after logical host-store update commits. |
| host prune commit point | `pruneSimSafeCandidateStateStore` callers on authoritative paths | Bumps epoch after prune commits. |
| host replacement / swap point | initial reducer safe-store rebuild from `allCandidateStates` | Bumps epoch after replacement commit. |
| device telemetryEpoch | `SimCudaPersistentSafeStoreHandle::telemetryEpoch` | Unchanged; remains device-handle telemetry, not CPU host epoch. |
| stale invalidation | `benchmark.sim_initial_safe_store_handoff_rejected_stale_epoch` | Unchanged diagnostic; not a CPU-vs-shadow comparison. |
| upload generation | GPU upload/handle telemetry | Still separate from host epoch. |
| clean gate epoch support | `benchmark.sim_initial_exact_frontier_shadow_has_safe_store_epoch_check=0` | Unchanged; no shadow epoch comparison exists. |
| CPU-vs-shadow epoch comparison | none | Missing; no mismatch counter emitted. |

## Added fields

| Field | Meaning |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available` | CPU authoritative safe-store epoch baseline was observable at the final baseline point. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch` | Host safe-store `hostEpoch` value observed at the final CPU baseline point. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_bumps` | Process benchmark count of recorded host safe-store epoch commit bumps. |
| `benchmark.sim_safe_store_host_epoch` | Alias for the final CPU baseline host safe-store epoch value. |
| `benchmark.sim_safe_store_host_epoch_bumps` | Alias for the recorded host safe-store epoch commit bump count. |

No safe-store epoch mismatch counter is emitted. These fields are CPU baseline
and telemetry availability fields only.

## Epoch semantics

`hostEpoch` is a logical committed-state generation on the host
`SimCandidateStateStore`. It is not incremented inside every summary replay or
candidate upsert loop. It advances when the host safe-store reaches a committed
state: reset/clear, update, prune, or replacement.

The epoch remains separate from:

- safe-store digest, which fingerprints contents at one observation point,
- GPU persistent safe-store `telemetryEpoch`, which tracks device handle and
  cached-frontier mutations,
- upload generation, which would link a host generation to a device handle,
- stale invalidation telemetry, which reports reuse rejection.

## Gate state

The clean exact frontier shadow gate remains:

```text
active=0
supported=0
missing_contract_counters=1
```

Host epoch availability alone does not activate the gate. The contract still
lacks CPU-vs-shadow epoch comparison, chunk-boundary snapshots/digests, and a
clean shadow backend.

## Remaining contract gaps

- `benchmark.sim_initial_exact_frontier_shadow_has_safe_store_epoch_check`
  remains `0` because no CPU-vs-shadow epoch comparison exists.
- No `safe_store_epoch_mismatches` counter is emitted.
- GPU `telemetryEpoch` is not treated as CPU host epoch.
- Chunk-boundary state remains missing on the default CPU path.

The next PR should be a minimal one-chunk GPU replay shadow design/stub or a
chunk-boundary host snapshot design. Gate activation should wait until the
remaining comparison contract is explicit.
