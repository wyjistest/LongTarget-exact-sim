# CUDA exact frontier per-request shadow contract status

This note records the supported contract level for the default-off per-request
exact frontier shadow backend.

## Status

| Field | Value |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_contract_level` | `candidate_safe_store` |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_contract_candidate_supported` | `1` |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_contract_safe_store_supported` | `1` |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_contract_epoch_supported` | `0` |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_full_contract_supported` | `0` |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_full_contract_disabled_reason` | `missing_epoch_contract` |

The backend is supported as a candidate plus safe-store content diagnostic
shadow. It is not a full clean-gate contract because the epoch/freshness
contract is still unavailable.

## Meaning

The per-request shadow compares:

- candidate digest,
- candidate values,
- min-candidate / runningMin,
- first-max / tie,
- pruned safe-store digest.

It does not compare a safe-store epoch. CPU `SimCandidateStateStore::hostEpoch`
is a host committed-state generation, while GPU
`SimCudaPersistentSafeStoreHandle::telemetryEpoch` is device handle/frontier-cache
telemetry. The current per-request path does not bind a CPU host generation to
the GPU snapshot being compared.

## Gate policy

This status telemetry does not activate the clean gate. The clean gate remains:

```text
active=0
supported=0
authority=cpu
disabled_reason=missing_contract_counters
```

The per-request shadow remains default-off, intentionally expensive, and
diagnostic-only. It does not feed output, safe-store authority, locate, region,
planner authority, `gpu_real`, `ordered_segmented_v3`, or
`LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY`.
