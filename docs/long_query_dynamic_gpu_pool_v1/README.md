# Long-query dynamic GPU pool v1

## Decision

The worker-specific whole-lncRNA scheduler implementation passes its bounded
mechanism tests.  It is not an active production epoch in this checkpoint.
The canceled static GPU workers remain stopped, and the existing OpenMP queue
is outside this scheduler's ownership.

Implementation source:

```text
commit 115c3fc0002b0ae04939740d27ed69f7334db015
```

## Scheduling contract

One lncRNA is one indivisible scientific job.  Pending jobs are ranked by
descending mean predicted runtime, with worker regret as the second key.  Each
job is then assigned to the worker with the minimum predicted finish time:

```text
EFT(job, worker) = worker_available_time + predicted_runtime(job, worker)
```

The worker prediction contains a configured worker-specific model and an
online factor derived only from completed jobs on that worker.  An offline
worker is excluded from assignment.  When a worker becomes available it
recomputes the whole pending schedule, which provides whole-job tail stealing
without splitting an output across GPUs.

## Durability and exactness boundary

The pool provides:

- `flock`-protected state transitions;
- heartbeat-backed leases and monotonically increasing lease epochs;
- fencing of stale completions;
- private attempt directories;
- fail-closed receipt, input digest, binary digest, and artifact validation;
- atomic publication by directory rename;
- recovery if the process dies after publication rename but before state save;
- bounded retries and terminal failure at the attempt limit;
- optional GPU UUID and external resource locks.

The production adapter enables the existing exact F1 pipeline, writes only
inside its attempt directory, requires all success/fallback markers, and
publishes exactly one nonempty `TFOsorted` artifact.  The pool never combines
scientific rows from different jobs or GPUs.

## Test receipt

```text
manifest builder tests       6 pass
pool state-machine tests    15 pass
production adapter tests     3 pass
total                       24 pass
```

Covered failure cases include query drift, unapproved historical binaries,
tampered artifacts, ownership overlap, simultaneous claims, lease expiry,
stale epochs, conflicting publications, interrupted publication recovery, and
two concurrent mock workers completing every job exactly once.

Run the check with:

```bash
make check-long-query-dynamic-gpu-pool-v1
```

## Next production manifest audit

The two canceled static GPU manifests contain 96 jobs.  Four completed jobs
were accepted only after their old binary digest was explicitly allowlisted,
their target/query/artifact digests were verified, all 1,615,536 F1 report
rows per job had `ok=1`, continuation failures were zero, and all GPU fallback
markers were zero.  The next epoch therefore contains 92 pending jobs.

```text
pending manifest SHA-256
253db967eda6fd5bd93d0486f6f40989de7fe27410a0353b16db6b37c8dda094
```

The detailed source and completion bindings are in
`production_manifest_audit.json`.  The OpenMP manifest is a reserved ownership
input, not a source of GPU jobs.

## Activation boundary

Before starting workers, create a plan that freezes:

- the 92-row manifest path and digest;
- the exact source commit and binary digest;
- target path, length, and digest;
- both GPU UUIDs and nonoverlapping CPU affinities;
- per-GPU resource lock paths;
- result root, lease interval, heartbeat interval, and retry limit.

Initialize once with `long_query_dynamic_gpu_pool.py init`; then start one
`run-worker` process per GPU.  A plan is immutable after initialization.  This
checkpoint deliberately does not create or launch that production pool.
