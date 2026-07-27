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
