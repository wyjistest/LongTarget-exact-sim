# F1 host-stage profile

This checkpoint adds default-off timers around the host work inside each
consumer-driven F1 batch. It does not change the consumer order, DP
recurrence, selected continuation, output contract, or default execution
path.

Enable the instrumentation with:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_HOST_PROFILE=1
```

The measured binary was built from `96b4ec7664ccfb4fbec5970dcf253a8d43c0b3c7`
and has SHA-256:

```text
ab04bc72f895263de63ff99bbf36b330f47831d68bcf9ca5d4d8fd8e2837effb
```

## Real-promoter result

The profile used the same complete-output workload as the frozen F1 and
continuation-reuse gates:

```text
query:   LINC01501 / 4,006 nt
target:  promoter shard_0009 / 4,942,620 bp
CPU:     logical CPU 19
GPU:     visible GPU 1
wall:    115.62 s
```

The complete output remained byte-identical to the CPU authority and prior F1
runs:

```text
TFOsorted SHA-256:
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075

task rows:                  48,432
scoreInfo groups:        1,086,495
attempts:                4,345,980
F1 forward attempts:     1,735,752
reverse requests:        1,086,495
selected continuations:  1,086,495
continuation failures:           0
```

The target was processed in 13 global F1 batches. Summed batch timing was:

| Stage | Seconds |
| --- | ---: |
| Attempt/group construction | 0.415 |
| Score-buffer allocation | 0.034 |
| Round descriptor construction | 0.185 |
| Forward stages | 9.024 |
| Forward result application | 0.038 |
| Reverse compaction | 0.138 |
| Reverse stages | 1.757 |
| Reverse result application | 0.057 |
| Round retirement | 0.044 |
| Deferred reverse work | 0.114 |
| Selection and accounting | 0.032 |
| Selected continuation outer region | 27.549 |
| Inner unaccounted | 0.026 |
| Destruction and return | 0.100 |
| Complete F1 batch calls | 39.514 |

Attempt construction, round bookkeeping, compaction, result application, and
local-vector destruction together account for less than one second. They are
not the remaining bottleneck and do not justify a new persistent queue or a
continuation thread pool by themselves.

The whole-query scoreInfo stage took 25.625 seconds. Subtracting it and the
complete F1 batch calls from the process wall leaves approximately 50.48
seconds outside both measured regions:

```text
115.620 - 25.625 - 39.514 = 50.481 s
```

The next checkpoint must time the outer F1 caller, especially task-input
construction, report/contract handling, `write_task_triplexes`, aggregation,
and final output commit. No optimization is authorized until that time is
attributed.

## Boundaries

```text
default enabled:                    no
complete-output exactness:          pass on one query x one promoter shard
host bookkeeping bottleneck:        rejected
continuation thread pool:           not authorized by this profile
consumer_cuda_authorized:           false
production_authorized:              false
bioinformatics_v2_state:            unchanged
full promoter concat:               not measured
continuous 4-12 kb envelope:        not established
```

Machine-readable evidence is in `profile_receipt.json`. Full local artifacts
remain under
`/data/wenyujianData/linjieData/longtarget_runs/exact_long_query_hybrid_f1_host_profile_v1`.
