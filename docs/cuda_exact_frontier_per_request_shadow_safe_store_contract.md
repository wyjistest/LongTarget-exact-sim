# CUDA exact frontier per-request shadow safe-store contract

This note records the safe-store contract decision for the default-off
per-request exact frontier shadow backend.

## Decision

The per-request backend now has a real safe-store digest contract. For each
request/window, the shadow builds a GPU pruned safe-store from the same ordered
initial summaries and GPU final frontier snapshot, downloads the pruned store
states for diagnostic comparison, and compares its digest with the CPU
request-local expected store digest. The result feeds only
`benchmark.sim_initial_exact_frontier_per_request_shadow_safe_store_digest_mismatches`
and the aggregate per-request shadow mismatch count.

The host epoch contract remains unavailable. The CPU `SimCandidateStateStore`
has a committed-state `hostEpoch`, but the comparable GPU value in this path is
only `SimCudaPersistentSafeStoreHandle::telemetryEpoch`. That device value tracks
handle/frontier-cache mutations and is not a CPU authoritative host epoch. The
backend therefore keeps:

```text
benchmark.sim_initial_exact_frontier_per_request_shadow_has_epoch_contract=0
```

and does not emit a safe-store epoch mismatch counter.

## Semantics

Safe-store digest comparison is request-local. It is not a continuous 44.8M
all-request safe-store proof and it does not prove cross-request state carry,
because request/window boundaries are semantic reset points for this replay
path.

The comparison is shadow-only:

- CPU remains authority.
- GPU safe-store output is not fed to output, locate, region, planner, upload,
  or safe-store authority.
- Clean gate remains inactive and unsupported.
- `gpu_real`, `ordered_segmented_v3`, and `EXACT_FRONTIER_REPLAY` remain out of
  this path.

## Remaining Gap

Epoch comparison needs a host-to-device generation contract that links a CPU
`hostEpoch` value to the device handle generation being compared. Until that
exists, treating GPU `telemetryEpoch` as a host epoch would be misleading.
The detailed epoch-gap inventory is recorded in
`docs/cuda_exact_frontier_per_request_shadow_epoch_contract_gap.md`.
