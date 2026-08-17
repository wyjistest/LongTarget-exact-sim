# Phase 2 CPU Oracle Trace Protocol

## Status and role

```text
record_status = preregistered_not_run
phase = 2
ssw_cpu_oracle_epoch = 2
fresh_holdout_consumed = false
promotion_role = regression_and_semantics_freeze_only
```

This protocol freezes observable modified-SSW semantics and proves that the
new trace is behaviorally inert. hq10/ht02 and hq11/ht02 are already-consumed
Phase 2 mismatch cases. They are regression evidence, never fresh promotion
evidence.

## Fixed implementation and execution boundary

The runner is `reproduce/ssw_cuda/run_phase2_oracle.py`; the plan is
`paper/ssw_cuda/cpu_oracle_attempt_plan.tsv`. Formal execution is forbidden
until the implementation, schema, contracts, runner, plan, checker, and tests
are committed and the worktree is clean.

The binary is built by:

```text
make build-ssw-cuda-phase2-oracle
```

with effective flags:

```text
-O3 -std=c++11 -pthread -msse2
```

AVX2 is not the Phase 2 authority. Runtime environment is reduced to locale,
timezone, single Fasim extend thread, and tfosorted output. Each process has a
120-second timeout, no retry, and an independent artifact root.

## Fixed matrix

For each case, five observations are executed as adjacent off/on pairs:

```text
trace_off: no oracle-trace variables; no trace directory may be created
trace_on:  fixed pre-align plus mismatch-call filter; full columns enabled
```

The paired output must equal both its mate and the frozen authority SHA-256:

```text
hq10_ht02 = c34ff3fbdb9d1a069397615e2ed695dd336eb2055ce389a8ccade83e3858cb88
hq11_ht02 = 394fe813c2e10d9340165d371255a8a54bf493e3c9da90d57db4e99dfd72cd82
```

Normalized stdout removes only the existing nondeterministic
`Running time is ...` line. All remaining stdout and complete stderr must be
identical within each off/on pair. Trace-on must produce exactly one pre-align
record and one alignment record, both byte-stable across all five observations.

## Frozen regression anchors

The runtime filters are complete stable keys already localized from the known
historical mismatch coordinates. They may not be changed after formal execution
starts. Expected alignment facts are:

```text
hq10: scoreInfo 3 / score 72 / identity round 0 / target window 512+69
      selected best_fallback / score 68 / query 1696-1751 (0-based)
      target 524-580 (0-based) / CIGAR 20M1I4M2D31M

hq11: scoreInfo 17 / score 93 / identity round 0 / target window 2169+84
      selected threshold / score 93 / query 725-790 (0-based)
      target 2191-2252 (0-based) / CIGAR 18M4I44M
```

These correspond to the one-based TFOsorted coordinates in the historical
root-cause record.

## Gate

Phase 2 passes only when:

- all 20 planned attempts return zero without timeout;
- no trace-off attempt creates trace files;
- all paired and frozen authority output digests match;
- normalized stdout and complete stderr match in every pair;
- both trace records validate and are deterministic across five observations;
- the mismatch calls retain their fixed keys, endpoints, selection reasons,
  band histories, CIGARs, and emitted L6 row identities;
- all source, binary, input, raw artifact, fixture, schema, and plan hashes are
  captured by the receipt and checker.

Any technical or semantic failure leaves Phase 2 active and preserves the
failed artifact root. There is no replacement attempt or result-driven filter,
parameter, input, or contract change.
