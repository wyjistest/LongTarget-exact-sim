# F1 selected-continuation task workers

This default-off engineering spike parallelizes selected CPU continuation at
the task boundary. Each worker owns one task at a time, processes that task's
selected attempts in the frozen order, performs the existing sort/filter
sequence locally, and writes only that task's result slot. The caller still
commits tasks in original order.

Enable it with both prerequisites:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1
FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=<workers>
```

The default worker count is one. Values above 64 are capped. A request for
multiple workers fails closed if prepared profile reuse is inactive or if the
thread-local detailed continuation profiler is enabled.

Remote implementation commit:

```text
f650d38bd08211f7e1bbc418eeff748495fe6d8d
```

## Exactness

The frozen 2 Mb scheduler fixture passed with 1, 2, and 4 workers:

```text
complete TFOsorted SHA-256:
a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b

task rows:                 10,368
scoreInfo groups:         245,422
attempts:                 981,688
F1 forward attempts:      389,089
reverse requests:         245,422
continuation failures:          0
row contract failures:          0
```

Both invalid configurations terminated before output materialization:

```text
multiple workers without reuse:
f1_parallel_continuation_requires_profile_reuse

multiple workers with TLS detail profile:
f1_parallel_continuation_profile_unsupported
```

The real LINC01501 x shard_0009 runs at 1, 2, and 4 workers all produced:

```text
complete TFOsorted SHA-256:
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075

scheduler structural signature SHA-256:
6659cbdc18137d95089342c5971559d8626b0f1eff0f538282c7def4957ef036
```

The structural signature covers every task's group, attempt, round,
selection, fallback, continuation-count, and error fields while excluding
timing and worker-count columns.

## Resource-isolated diagnostic

The 16-thread production OpenMP queue remained active on logical CPUs
`1-8,11-18`. The spike used only the two otherwise idle physical cores:

```text
1 worker:  CPU 19
2 workers: CPUs 0,9
4 workers: CPUs 0,9,10,19 (SMT siblings on the same two physical cores)
GPU:       visible GPU 1
```

Same-binary results were:

| Workers | Wall seconds | F1 batch wall | Continuation wall |
| ---: | ---: | ---: | ---: |
| 1 | 66.74 | 39.368 | 27.393 |
| 2 | 53.46 | 26.118 | 14.171 |
| 4 | 52.59 | 25.274 | 13.327 |

Relative to one worker:

```text
2 workers:
  end-to-end gain                 1.248x
  wall reduction                 19.90%
  continuation wall reduction    48.27%

4 workers on two SMT cores:
  end-to-end gain                 1.269x
  wall reduction                 21.20%
  continuation wall reduction    51.35%

4 vs 2 workers:
  additional gain                 1.017x

contextual frozen CPU / 4 workers 6.94x
```

Per-task traceback and conversion seconds are additive CPU-time proxies once
tasks execute concurrently. End-to-end decisions use process wall and the
host batch/continuation wall timers.

## Next bottleneck

At four workers the major stages are now approximately balanced:

```text
whole-query scoreInfo             25.54 s
complete F1 batches               25.27 s
  continuation wall              13.33 s
  forward/reverse and host work  11.95 s
outer transform/output             1.78 s
```

The largest single remaining stage is whole-query scoreInfo. Further
continuation worker expansion is not justified on this host: two extra SMT
workers improve total wall by only 1.6%. CPU/GPU pipelining and scoreInfo
kernel work require separate checkpoints.

## Boundaries

```text
default worker count:               1
complete-output exactness:          pass on one query x one promoter shard
formal uncontaminated performance:  not measured
consumer_cuda_authorized:           false
production_authorized:              false
bioinformatics_v2_state:            unchanged
full promoter concat:               not measured
continuous 4-12 kb envelope:        not established
```

Machine-readable evidence is in `performance_receipt.json`. Full artifacts
remain under
`/data/wenyujianData/linjieData/longtarget_runs/exact_long_query_hybrid_f1_cont_threads_spike_v1`.
