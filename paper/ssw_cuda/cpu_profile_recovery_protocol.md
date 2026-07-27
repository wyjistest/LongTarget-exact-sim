# Phase 1 CPU Profile Recovery Protocol

Status: preregistered before recovery execution.

## Reason For A New Execution Epoch

Phase 1 profile execution v1 stopped at execution order 21 when
`p1_large_h19_chr21_o01_profile_off` reached its fixed 1,800-second timeout.
The v1 evidence remains authoritative for that failure:

```text
formal commit = 2d429866943fb77ea40648f657d922408cdc30a8
blocked receipt sha256 = 03f547123d3550961c6a3205792e6a8b4dd2524e6677ab4af5c2b8b2b968e0e5
blocked artifact manifest sha256 = 725e0f46d5a0364e3e0dd870c94060ce6aa7db9e51b9464fdbdf2811fc9e305b
attempts complete / failed / not started = 20 / 1 / 29
retries attempted = 0
```

The timeout was an outer operational safeguard, not an authority parameter or
scientific gate. Existing full-chromosome evidence predating v1 reports a
2,377.197-second median for the two-worker H19 chr21+chr22 CPU authority
workload, so 1,800 seconds was already below a known realistic execution time.

This recovery is a new complete execution epoch, not a replacement attempt in
v1. No v1 observation enters v2 source data or statistics.

## Frozen Change Scope

V2 changes only these execution-identity fields:

```text
attempt namespace = p1v2_*
artifact root = .paper-artifacts/ssw-cuda-v1/phase1/profile-runs-v2
per-attempt outer timeout = 7200 seconds
total formal wall-clock budget = 129600 seconds
```

The following remain byte-for-byte or semantically identical to v1:

- five workload inputs and all input digests;
- 50-attempt panel and execution order;
- five observations per workload in both profile-off and profile-on modes;
- cold-advisory versus steady-state definitions;
- authority command, `-r 0`, `-cn 1`, and output contract;
- sanitized environment and `FASIM_EXTEND_THREADS=1`;
- mutually exclusive timing stages and addressable-fraction definitions;
- deterministic bootstrap method and conservative Amdahl gate;
- original 10x B3 threshold;
- retry policy `none`.

The v2 attempt plan SHA-256 is:

```text
b3222feb0ab20a40b4605381e68863ee99b61b8b83f7a743d66d125ba18932b6
```

## Evidence Separation

V1 artifacts, its blocked receipt, its blocked decision, and its partial chr21
output must not be renamed, deleted, modified, or read as v2 measurements. V2
must start at attempt 1 in an absent artifact root and complete all 50 attempts
before generating any v2 source-data table or Amdahl decision.

The committed v2 outputs use distinct paths:

```text
paper/ssw_cuda/cpu_profile_v2_source_data.tsv
paper/ssw_cuda/cpu_profile_v2_statistics.json
paper/ssw_cuda/amdahl_v2_decision.json
paper/ssw_cuda/amdahl_v2_decision.md
paper/ssw_cuda/cpu_profile_v2_execution_receipt.json
```

## Stop Rules

- Any timeout, nonzero return, malformed telemetry, profile stack error,
  authority output difference, or accounting failure blocks v2 immediately.
- No failed row is retried and no replacement observation is appended.
- Reaching the fixed 36-hour total budget blocks v2 before the next attempt.
- Parameters, panel membership, order, output mode, and claim boundary cannot
  be changed after seeing v2 results.
- V1 remains blocked even if v2 passes; the Phase 1 program state may advance
  only on the separately versioned v2 result.

## Execution Boundary

The recovery protocol, attempt plan, runner, tests, checker, and in-progress
state must be committed, the v1 blocked checker must pass, the v2 artifact root
must be absent, and the worktree must be clean before formal recovery starts.
