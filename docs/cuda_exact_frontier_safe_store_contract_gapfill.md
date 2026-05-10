# CUDA exact frontier safe-store contract gap-fill

Date: 2026-05-10

Base: `cuda-exact-frontier-digest-contract-gapfill`

This PR adds safe-store baseline availability telemetry for the future GPU
exact ordered frontier replay shadow contract. It does not implement GPU
replay, does not route through `ordered_segmented_v3`, does not report
`gpu_real` authority, and does not make the clean shadow gate active.

## Inventory

| Concept | Existing key/helper | Action |
| --- | --- | --- |
| CPU safe-store digest | `simCandidateStateStoreFingerprint(context.safeCandidateStateStore)` | Exposed as baseline availability when the authoritative host safe-store is valid. |
| CPU safe-store epoch | none on `SimCandidateStateStore` | Reported unavailable. Do not borrow GPU telemetry epoch. |
| GPU safe-store handle epoch | `SimCudaPersistentSafeStoreHandle::telemetryEpoch` | Documented as related device-handle telemetry, not CPU authoritative epoch. |
| stale safe-store invalidation | `benchmark.sim_initial_safe_store_handoff_rejected_stale_epoch` | Existing handoff diagnostic, not exact frontier contract coverage. |
| existing safe-store mismatch counters | safe-store precombine/prune/index shadows | Related diagnostics only; not clean contract-gate CPU-vs-shadow comparison. |
| clean gate support flag | `sim_initial_exact_frontier_shadow_gate_supported=0` | Unchanged. |
| missing CPU-vs-shadow safe-store comparison | no contract-compliant backend | Keep `has_safe_store_*_check=0`; do not emit mismatch counters. |

## Added fields

| Field | Meaning |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_digest_available` | CPU authoritative safe-store digest baseline was computable at the final baseline point. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available` | CPU authoritative safe-store epoch baseline is locally observable. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_safe_store_digest_check` | Actual CPU-vs-shadow safe-store digest compare exists. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_safe_store_epoch_check` | Actual CPU-vs-shadow safe-store epoch compare exists. Currently `0`. |

No safe-store digest or epoch mismatch counters are emitted here. The new
`contract_cpu_*` fields are availability fields only, not zero-mismatch
claims.

## Gate state

The clean gate remains:

```text
active=0
supported=0
missing_contract_counters=1
```

Safe-store digest availability alone is not enough to activate the gate. The
contract still lacks an actual CPU-vs-shadow backend, first-max/tie coverage,
chunk-boundary coverage, and safe-store epoch coverage.

## Interpretation

The authoritative host safe-store already has a local digest helper, so future
shadow work can compare against that baseline when the host safe-store is still
valid. The host safe-store has no authoritative epoch field; the existing GPU
safe-store `telemetryEpoch` tracks persistent device handles and should not be
reported as a CPU epoch baseline.
