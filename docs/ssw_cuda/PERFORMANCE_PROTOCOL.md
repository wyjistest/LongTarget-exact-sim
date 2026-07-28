# SSW-CUDA Performance Protocol

Status: Phase 0 skeleton; the CPU profile protocol is frozen in Phase 1 and
the promoted-backend protocol is frozen before Phase 12 execution.

The primary metric is independent-arm end-to-end wall time. Kernel time,
historical candidate-only timing, sequential verified timing, correctness-run
timing, and projected timing cannot substitute for safe paired performance.

Phase 1 measures the fraction of authority wall time directly addressable by
the proposed backend and applies:

```text
maximum_speedup_infinite = 1 / (1 - p_backend_addressable)
```

The original B3 thresholds remain unchanged: safe speedup at least 10x,
observed wall-time reduction at least 8 hours, or safe 24-hour capacity at
least 10x. A closed Amdahl decision cannot be reopened from downstream timing
without a separately preregistered addressable-scope profile.

Formal A/G arms run as independent processes and cannot read one another's
outputs. Execution order is preregistered; comparison happens only after both
arms finish. Failures and slow observations remain in source data.

## Phase 7 development checkpoint

Phase 7 is not the Phase 12 promoted-backend benchmark. It imports the five
frozen Phase 1 profile-off observations per development workload as an A
reference and imports the closed H2 receipt without rerunning either arm. It
executes five new independent F observations on each of the same five
development workloads. The 24 additional F processes are consumed correctness
regressions and are excluded from performance summaries.

Since A and F are not newly paired, their ratio is named
`checkpoint_reference_ratio`, never `speedup`. It supports only an engineering
futility decision. Phase 7 also reports an optimistic full-GPU wall projection
by subtracting measured selected CPU continuation from observed F wall, with F
wall itself as the conservative upper bound. Neither bound is observed G
performance.

The fixed Phase 7 limits are five F observations per primary workload, no A or
H2 rerun, no retries, 7,200 seconds per performance attempt, and 43,200 seconds
total GPU wall. The 10x B3 threshold and closed Amdahl decision remain
unchanged.
