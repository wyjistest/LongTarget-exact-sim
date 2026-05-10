# CUDA exact frontier first-max/tie contract gap-fill

Date: 2026-05-10

Base: `cuda-exact-frontier-safe-store-contract-gapfill`

This PR adds first-max/tie baseline availability telemetry for the future GPU
exact ordered frontier replay shadow contract. It does not implement GPU
replay, does not route through `ordered_segmented_v3`, does not report
`gpu_real` authority, and does not make the clean shadow gate active.

## Inventory

| Concept | Existing key/helper | Action |
| --- | --- | --- |
| CPU first-max state | final `SimCandidate` fields `SCORE`, `ENDI`, `ENDJ`; converted by `makeSimScanCudaCandidateState` | Exposed as CPU baseline availability. |
| CPU tie state | final candidate range fields `TOP`, `BOT`, `LEFT`, `RIGHT` plus preserved first max endpoint | Exposed as CPU baseline availability. |
| CPU first-max/tie digest | candidate digests already include `score`, `endI`, `endJ`, and range fields | Documented as covered by candidate-state baseline digest. |
| diagnostic first-max state | `ordered_segmented_v3` candidate value compare uses `memcmp` on full `SimScanCudaCandidateState` | Related diagnostic only; not clean gate coverage. |
| diagnostic tie state | same full candidate-state compare includes range fields | Related diagnostic only; not clean gate coverage. |
| existing candidate value mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_value_mismatches` | Covers final candidate fields on the experimental diagnostic path, but it is not the clean shadow contract gate. |
| clean gate support flag | `sim_initial_exact_frontier_shadow_gate_supported=0` | Unchanged. |
| missing CPU-vs-shadow comparison | no contract-compliant backend | Keep `has_first_max*_check=0` and `has_tie*_check=0`; do not emit mismatch counters. |

## Added fields

| Field | Meaning |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_contract_cpu_first_max_available` | CPU final candidate state exposes first-max outcome fields. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_tie_available` | CPU final candidate state exposes tie/range outcome fields. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_first_max_tie_available` | CPU final candidate state exposes both first-max and tie/range outcome fields. |
| `benchmark.sim_initial_exact_frontier_shadow_has_first_max_check` | Actual CPU-vs-shadow first-max compare exists. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_tie_check` | Actual CPU-vs-shadow tie compare exists. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_first_max_tie_check` | Actual CPU-vs-shadow combined first-max/tie compare exists. Currently `0`. |

No first-max or tie mismatch counters are emitted here. The new
`contract_cpu_*` fields are availability fields only, not zero-mismatch
claims.

## Existing candidate value mismatch coverage

`benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_value_mismatches`
compares full `SimScanCudaCandidateState` values on the experimental
`ordered_segmented_v3` diagnostic path. Because that struct contains `score`,
`endI`, `endJ`, `top`, `bot`, `left`, and `right`, that existing diagnostic
would catch final candidate first-max/tie field drift on that path.

It is not reused as the clean contract mismatch counter because it is tied to
the experimental reducer/diagnostic route rather than the inactive
`LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_SHADOW_GATE=1` contract gate.

## Gate state

The clean gate remains:

```text
active=0
supported=0
missing_contract_counters=1
```

First-max/tie availability alone is not enough to activate the gate. The
contract still lacks an actual CPU-vs-shadow backend, chunk-boundary coverage,
and safe-store epoch coverage.
