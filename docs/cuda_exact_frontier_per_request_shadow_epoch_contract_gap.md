# CUDA exact frontier per-request shadow epoch contract gap

This note records the epoch-contract decision for the default-off per-request
exact frontier shadow backend after safe-store digest comparison became
available.

## Current contract state

| Contract item | Status |
| --- | --- |
| Candidate digest | Compared CPU-vs-GPU. |
| Candidate values | Compared CPU-vs-GPU. |
| Min candidate / runningMin | Compared CPU-vs-GPU. |
| First-max / tie | Compared CPU-vs-GPU. |
| Safe-store digest | Compared CPU-vs-GPU. |
| Safe-store epoch | Unavailable as a CPU-vs-GPU comparison. |

The backend must therefore keep:

```text
benchmark.sim_initial_exact_frontier_per_request_shadow_has_epoch_contract=0
```

and must not emit an epoch mismatch counter.

## Inventory

| Item | Location | Meaning |
| --- | --- | --- |
| CPU host epoch | `SimCandidateStateStore::hostEpoch` | Host committed-state generation. |
| Host epoch bump | `resetSimCandidateStateStore`, `bumpSimCandidateStateStoreHostEpoch` | Advances on host safe-store commit points such as reset, update, prune, or replacement. |
| CPU epoch telemetry | `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch*` | CPU baseline availability/value only; not a shadow mismatch counter. |
| GPU device epoch | `SimCudaPersistentSafeStoreHandle::telemetryEpoch` | Device handle/frontier-cache mutation telemetry. |
| GPU upload | `sim_scan_cuda_upload_persistent_safe_candidate_state_store` | Bumps device telemetry but does not carry a CPU host epoch. |
| Per-request shadow safe-store | `runSimInitialExactFrontierPerRequestShadowIfRequested` | Builds a request-local GPU safe-store from summaries, downloads states, and compares content digest. |

## Decision

Do not add a per-request epoch mismatch counter in this PR.

The CPU value available here is a host committed-state generation. The GPU value
available here is device-handle telemetry. The per-request diagnostic shadow
does not upload a CPU store generation into the GPU handle and does not bind the
GPU safe-store snapshot to a specific CPU `hostEpoch`. Comparing those two
numbers would be a false epoch contract even when their values happened to
match.

The existing safe-store digest comparison remains valid because both sides
materialize and hash comparable store contents at the request boundary. Epoch is
different: it represents freshness and mutation ordering, not only final
content.

## Required future mapping

A real epoch contract needs an explicit host-to-shadow generation link, for
example:

| Component | Requirement |
| --- | --- |
| `host_epoch` | CPU authoritative `SimCandidateStateStore::hostEpoch` at the replay boundary. |
| `shadow_epoch` | A shadow-side value that represents the same host generation, not just device handle mutation count. |
| `upload_generation` | A record that host epoch N was uploaded or synthesized into the compared GPU snapshot. |
| `epoch_mismatches` | Emitted only after the compared values share this contract. |

Until that mapping exists, the honest state is:

```text
has_candidate_contract=1
has_safe_store_contract=1
has_epoch_contract=0
```

## Gate impact

This does not activate the clean gate. The per-request shadow remains:

- default-off,
- CPU-authoritative,
- diagnostic only,
- not a production output path,
- unrelated to `gpu_real`, `ordered_segmented_v3`, or
  `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY`.

The next implementation step should either add an explicit host-to-shadow epoch
mapping or leave epoch as a documented clean-gate blocker.
