# CUDA Exact Frontier One-Chunk Shadow Stub

This note defines the first clean exact-frontier shadow backend shape without
implementing GPU replay. The backend is a stub: CPU replay remains authoritative,
the clean shadow gate remains inactive, and no diagnostic result is fed into
locate, region, planner, safe-store upload, or proposal authority.

## Inventory

| Concept | Existing key/helper | Action |
| --- | --- | --- |
| clean gate requested/active | `benchmark.sim_initial_exact_frontier_shadow_gate_requested`, `benchmark.sim_initial_exact_frontier_shadow_gate_active` | Keep requested telemetry, keep `active=0`. |
| clean gate authority | `benchmark.sim_initial_exact_frontier_shadow_gate_authority=cpu` | Keep CPU authoritative. |
| existing disabled reasons | `env_off`, `missing_contract_counters` | Add backend-level `one_chunk_backend_not_implemented`; do not change gate disabled reason. |
| candidate digest baselines | `benchmark.sim_initial_exact_frontier_contract_cpu_ordered_digest_available`, `benchmark.sim_initial_exact_frontier_contract_cpu_unordered_digest_available` | Use as future final-state comparison inputs. |
| min-candidate baseline | `benchmark.sim_initial_exact_frontier_contract_cpu_min_candidate_available` | Use as future final-state comparison input. |
| first-max/tie baselines | `benchmark.sim_initial_exact_frontier_contract_cpu_first_max_available`, `benchmark.sim_initial_exact_frontier_contract_cpu_tie_available`, `benchmark.sim_initial_exact_frontier_contract_cpu_first_max_tie_available` | Use as future final-state comparison inputs. |
| safe-store digest baseline | `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_digest_available` | Use as future final-state comparison input. |
| host safe-store epoch baseline | `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch_available`, `benchmark.sim_initial_exact_frontier_contract_cpu_safe_store_epoch` | Use as future freshness comparison input, separate from digest and device telemetry epoch. |
| one-chunk backend | `benchmark.sim_initial_exact_frontier_shadow_backend`, `benchmark.sim_initial_exact_frontier_shadow_one_chunk_*` | Add unsupported stub telemetry only. |
| CPU-vs-shadow comparison backend | missing | Keep final compare support at `0`; emit no mismatch counters. |
| chunk-boundary comparison | missing | Avoid per-boundary comparison in this first backend shape. |

## One-Chunk Shape

The one-chunk backend treats the full ordered initial summary stream as a single
replay chunk. It intentionally avoids the missing default-path per-boundary
snapshot/digest contract by comparing only the final replay state in a future
backend.

The future final-state comparison must cover:

- ordered candidate digest
- unordered candidate digest
- min-candidate
- first-max/tie
- safe-store digest
- safe-store host epoch
- candidate count
- candidate value set
- replay authority remaining `cpu`

This PR only names that backend shape. It does not implement the replay backend,
does not copy GPU replay output, and does not perform CPU-vs-shadow comparison.

## Telemetry Semantics

With `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_SHADOW_GATE` unset:

```text
benchmark.sim_initial_exact_frontier_shadow_backend=none
benchmark.sim_initial_exact_frontier_shadow_backend_supported=0
benchmark.sim_initial_exact_frontier_shadow_backend_disabled_reason=env_off
benchmark.sim_initial_exact_frontier_shadow_one_chunk_supported=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_calls=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_final_compare_supported=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_missing_backend=0
```

With the clean gate requested:

```text
benchmark.sim_initial_exact_frontier_shadow_backend=one_chunk_stub
benchmark.sim_initial_exact_frontier_shadow_backend_supported=0
benchmark.sim_initial_exact_frontier_shadow_backend_disabled_reason=one_chunk_backend_not_implemented
benchmark.sim_initial_exact_frontier_shadow_one_chunk_supported=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_calls=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_final_compare_supported=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_missing_backend=1
```

The clean gate still reports `active=0`, `supported=0`, and
`missing_contract_counters=1`. The backend fields are descriptive only and do not
override gate status.

## Non-Goals

- no GPU replay kernel
- no CPU-vs-GPU comparison
- no fake zero mismatch counters
- no `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY` routing
- no `ordered_segmented_v3` routing
- no `gpu_real` authority
- no CPU replay order, running floor, first-max/tie, safe-store update, prune,
  upload, or stale-invalidation behavior change

## Future Activation Requirements

Activating a real one-chunk shadow backend requires a clean backend that replays
the ordered summary stream without entering experimental reducer authority, then
compares final CPU authoritative state against shadow final state. Only that
future comparison may introduce mismatch counters such as candidate digest,
candidate value, min-candidate, first-max/tie, safe-store digest, or safe-store
epoch mismatches.

Chunk-boundary comparison remains a later extension. It should not be inferred
from aggregate frontier transducer mismatch or from `ordered_segmented_v3` chunk
stats.
