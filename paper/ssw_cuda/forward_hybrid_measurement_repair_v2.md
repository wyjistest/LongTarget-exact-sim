# Phase 7 measurement repair 2

## Frozen execution outcome

Epoch v2 stopped fail-closed on its 27th receipt. The failing process exited
normally from the runner's perspective, without timeout or OOM, after the
backend detected one CPU continuation contract failure.

```text
source commit             = f3ffe9b188c43ef0bff78a903176f991c493f2b8
execution receipt SHA-256 = 8a1947ae74feed5f213df0749ff74718053100067d233e5e67d3d13b137e4042
attempt                   = p7v2p_large_h19_chr21_o01
attempt receipt SHA-256   = 24882e28bb5a80c55fff3687b33c3e28c917cb7d80c0f7f2d9ddc820dbfe53cd
wall seconds              = 5233.500341672916
return code               = 2
timed out                 = false
CPU failures              = 1
backend error             = forward-hybrid continuation contract mismatch
replacement retries       = 0
```

The GPU selected 665,582 attempts. The selected-only CPU path completed
665,562 reverse-start and banded-traceback calls before the first contract
failure stopped the workload. CPU pre-align and CPU forward call counts
remained zero. The partial output and all receipts remain immutable under
`formal-v2` and are not eligible for correctness comparison.

## Classification defect

The preregistered protocol says that failed F correctness is a Phase 7 no-go.
The original analysis code classified every incomplete epoch as
`blocked_by_environment`, including a deterministic implementation contract
failure. That contradicts the frozen rule and would leave a failed backend
eligible for an inappropriate environmental rerun.

Repair 2 changes only decision classification and future error text:

```text
technical failure with cpu_failures > 0
  -> phase7_status = no_go
  -> no_go_reason = forward_hybrid_implementation_contract_failure
  -> phase8_engineering_authorized = false
```

The frozen allowed-decision enum has no separate correctness-no-go label, so
the machine decision remains `forward_hybrid_performance_futility_stop` and
the new `no_go_reason` records the actual correctness cause. This does not
claim that the incomplete performance panel itself established a formal
speedup result.

## Boundary

This is analysis-only repair 2 of the maximum 2. It authorizes zero new
attempts, no v3 execution, no retry, no replacement, and no Phase 8 work. It
does not alter the backend, plan, inputs, contracts, thresholds, timeouts,
worker mapping, comparator, or preserved v1/v2 artifacts.
