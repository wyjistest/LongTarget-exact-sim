# CUDA exact frontier digest contract gap-fill

Date: 2026-05-10

Base: `cuda-exact-frontier-shadow-contract-stub`

This PR adds baseline availability telemetry for future GPU exact ordered
frontier replay shadow comparison. It does not implement GPU replay, does not
route through `ordered_segmented_v3`, and does not make the clean shadow gate
active.

## Added Fields

| Field | Meaning |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_contract_cpu_ordered_digest_available` | CPU final frontier ordered digest baseline was computed. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_unordered_digest_available` | CPU final frontier unordered digest baseline was computed after existing shadow sort order. |
| `benchmark.sim_initial_exact_frontier_contract_cpu_min_candidate_available` | CPU min-candidate baseline is locally observable. |
| `benchmark.sim_initial_exact_frontier_shadow_has_ordered_digest_check` | Actual CPU-vs-shadow ordered digest compare exists. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_unordered_digest_check` | Actual CPU-vs-shadow unordered digest compare exists. Currently `0`. |
| `benchmark.sim_initial_exact_frontier_shadow_has_min_candidate_check` | Actual CPU-vs-shadow min-candidate compare exists. Currently `0`. |

No digest or min-candidate mismatch counters are emitted here, because there is
still no independent contract-compliant shadow backend. The new `cpu_*`
fields are availability fields only, not zero-mismatch claims.

## Gate State

The clean gate remains:

```text
active=0
supported=0
missing_contract_counters=1
```

Remaining blockers are first-max/tie, safe-store digest/epoch, chunk-boundary,
and real CPU-vs-shadow ordered digest, unordered digest, and min-candidate
comparisons. The next PR should fill one of those gaps without activating the
gate.
