# CUDA exact frontier shadow contract gate stub

Date: 2026-05-10

Base: `cuda-ordered-segmented-shadow-gate`

This PR adds a clean, default-off telemetry gate for future GPU exact ordered
frontier replay shadow work. It does not implement GPU replay, does not route
through `ordered_segmented_v3`, and does not allow `gpu_real` authority.

## Gate

```text
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_SHADOW_GATE=1
```

Default behavior remains unchanged. CPU ordered replay remains authoritative in
both default and opt-in runs.

| Mode | requested | active | authority | disabled_reason | calls |
| --- | --- | --- | --- | --- | --- |
| default | 0 | 0 | `cpu` | `env_off` | 0 |
| opt-in | 1 | 0 | `cpu` | `missing_contract_counters` | 0 |

The opt-in gate is intentionally inactive because there is no
contract-compliant shadow backend yet. The gate only establishes unambiguous
authority and disabled-reason telemetry for later counter gap-fill work.

## Inventory

| Existing item | Location | Why it is insufficient as this gate |
| --- | --- | --- |
| `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1` | `sim.h`, `README.md` | It can report `benchmark.sim_initial_replay_authority=gpu_real` with the experimental reducer. |
| `LONGTARGET_SIM_CUDA_INITIAL_ORDERED_SEGMENTED_V3_SHADOW=1` | `sim.h`, `longtarget.cpp` | It is a diagnostic compare tied to experimental `ordered_segmented_v3` reduce output. |
| `LONGTARGET_SIM_CUDA_INITIAL_FRONTIER_TRANSDUCER_SHADOW=1` | `sim.h`, `longtarget.cpp` | It keeps CPU authority but only reports aggregate mismatch telemetry. |
| `benchmark.sim_initial_replay_authority` | `longtarget.cpp` | Useful global authority label, but it cannot distinguish a clean inactive shadow contract gate. |

## New telemetry

```text
benchmark.sim_initial_exact_frontier_shadow_gate_requested
benchmark.sim_initial_exact_frontier_shadow_gate_active
benchmark.sim_initial_exact_frontier_shadow_gate_authority
benchmark.sim_initial_exact_frontier_shadow_gate_disabled_reason
benchmark.sim_initial_exact_frontier_shadow_gate_calls
benchmark.sim_initial_exact_frontier_shadow_gate_supported
benchmark.sim_initial_exact_frontier_shadow_gate_missing_contract_counters
```

The stable disabled reasons used by this stub are:

```text
env_off
missing_contract_counters
```

Future implementations may add stable reasons such as
`missing_shadow_backend`, `unsupported_reducer_real_path`,
`ordered_segmented_v3_not_shadow_only`, or
`frontier_transducer_aggregate_only` without changing the default authority
model.

## Missing contract counters

This gate stays inactive until these comparison gaps are closed:

| Counter gap | Status |
| --- | --- |
| first-max / tie mismatch | missing |
| min-candidate mismatch | missing |
| ordered candidate digest | missing |
| unordered candidate digest | missing |
| safe-store digest mismatch | missing |
| safe-store epoch mismatch | missing |
| chunk-boundary mismatch | missing |

These gaps are reported as
`benchmark.sim_initial_exact_frontier_shadow_gate_missing_contract_counters=1`.
The field is not an exactness result and must not be read as a zero-mismatch
claim.

## Non-goals

This PR does not add a GPU replay kernel, does not default
`ordered_segmented_v3`, does not use unordered top-K reduction, does not change
CPU replay order, and does not feed shadow state into locate, region,
safe-store handoff, frontier state, planner authority, or final output.

## Recommendation

Use this gate as the only future activation point for exact frontier replay
shadow contract work. The next PR should fill one contract gap, preferably
first-max/tie mismatch or ordered/unordered candidate digest telemetry, before
adding any minimal CUDA replay shadow backend.
