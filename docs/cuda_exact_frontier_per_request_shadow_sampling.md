# CUDA exact frontier per-request shadow sampling

This PR adds request selection to the default-off per-request exact frontier
shadow backend. It is a cost-control policy only; it does not change replay
semantics or the comparison contract.

## Runtime controls

| Env | Meaning |
| --- | --- |
| `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_REQUEST_INDEX=<n>` | Compare exactly request/window index `n`. |
| `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_MAX_REQUESTS=<n>` | Compare the first `n` request/window indexes. |
| `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_REQUEST_LIST=0,24,47` | Compare the listed request/window indexes. |

Default behavior is unchanged. With no selection env, the opt-in shadow compares
all request/window indexes.

Selection precedence is:

```text
REQUEST_LIST > REQUEST_INDEX > MAX_REQUESTS > all
```

Invalid selection does not run shadow comparison. It reports explicit selection
telemetry instead of silently falling back to full mode.

## Make smoke targets

| Target | Selection | Purpose |
| --- | --- | --- |
| `make check-sim-initial-exact-frontier-per-request-shadow-smoke` | `REQUEST_INDEX=47` | Cheap single-request contract smoke. |
| `make check-sim-initial-exact-frontier-per-request-shadow-sampled` | `REQUEST_LIST=0,24,47` | Broader deterministic sampled check. |
| `make check-sim-initial-exact-frontier-per-request-shadow-invalid` | `REQUEST_INDEX=999` | Invalid-selection guard. |
| `make check-sim-initial-exact-frontier-per-request-shadow-full` | all requests | Manual expensive all-request audit. |

The first three targets are intended as low-cost review/regression gates. The
full target preserves the heavy audit entry point but should not be added to
default checks.

## Telemetry

| Field | Meaning |
| --- | --- |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_selection_mode` | `all`, `request_index`, `max_requests`, or `request_list`. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_requested_request_index` | The selected request index, or `none`. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_requested_max_requests` | The requested first-N limit, or `0`. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_requests_selected` | Requests selected for shadow comparison. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_requests_skipped` | Requests skipped by selection policy. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_selection_invalid` | `1` when selection cannot be honored. |
| `benchmark.sim_initial_exact_frontier_per_request_shadow_selection_disabled_reason` | `env_off`, `none`, `invalid_selection`, `request_index_out_of_range`, or `request_list_out_of_range`. |

Existing mismatch and contract fields keep their meaning. `requests_total` is
the number of request/window inputs seen by the requested diagnostic backend,
while `requests_compared` is the number actually replayed and compared.

## Contract boundary

Selected and full modes use the same candidate plus safe-store digest contract:

```text
contract_level=candidate_safe_store
contract_epoch_supported=0
full_contract_supported=0
full_contract_disabled_reason=missing_epoch_contract
```

The clean gate remains inactive and unsupported. This path is still
CPU-authoritative, default-off, diagnostic-only, and intentionally expensive. It
does not feed output, safe-store authority, locate, region, planner authority,
`gpu_real`, `ordered_segmented_v3`, or
`LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY`.
