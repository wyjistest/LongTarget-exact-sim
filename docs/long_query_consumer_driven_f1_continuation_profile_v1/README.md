# F1 selected-continuation profile and query-profile reuse

This checkpoint profiles the selected CPU continuation after the ordered F1
scheduler gate at `371144e` and adds one default-off optimization. It does not
change the F1 consumer, the forward/reverse DP recurrence, selection order,
traceback semantics, output contract, or default path.

Enable the two independent development flags with:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_PROFILE=1
FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1
```

The first flag only records continuation phase telemetry. The second prepares
the immutable translated query and SSW query profile once per global F1 batch.
Every selected attempt still performs the exact CPU reverse-start recovery and
banded CIGAR traceback. The prepared context is bound to its creating aligner
and rejects a changed scoring matrix or gap penalties.

## Bounded exactness and profile

The 4,006 nt LINC01501 query was run against the frozen 2 Mb chr22 fixture on
CPU 19 and GPU 1 while the production OpenMP queue remained on other physical
cores. All modes produced the same complete TFOsorted SHA-256:

```text
a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b
```

| Mode | Wall seconds | Continuation seconds |
| --- | ---: | ---: |
| Default, profile off | 32.09 | not collected |
| Profile on, cache off | 32.33 | 12.001 |
| Generic profile cache | 26.38 | 6.042 |
| Prepared F1 query/profile | 24.61 | 4.317 |

The cache-off continuation spent 6.996 seconds building the same SSW query
profile 245,422 times. The generic cache removed that build, but still spent
0.500 seconds translating the query and 1.107 seconds hashing/looking up the
same cache key. Prepared reuse removed both repeated stages. Its remaining SSW
time was 4.162 seconds, including 3.383 seconds of reverse-start recovery and
0.742 seconds of banded traceback. Substring construction and reference
translation were only 0.018 and 0.015 seconds, respectively.

## Real-promoter paired result

The frozen `63c56da` binary was then run on:

```text
query:  LINC01501 / 4,006 nt
target: promoter shard_0009 / 4,942,620 bp
mode:   complete TFOsorted
```

Arm B was F1 with prepared reuse off. Arm R was the same binary with prepared
reuse on. Three balanced cycles used `B-R / R-B / B-R`.

| Cycle | B seconds | R seconds | B/R |
| --- | ---: | ---: | ---: |
| 1 | 150.08 | 115.46 | 1.300x |
| 2 | 150.16 | 115.30 | 1.302x |
| 3 | 150.01 | 115.13 | 1.303x |
| Median | 150.08 | 115.30 | 1.302x |

Prepared reuse reduced F1 wall time by 23.17%. Relative to the separately
frozen CPU authority median of 364.75 seconds from the same workload and
affinity epoch, the engineering speed is approximately 3.16x. That CPU ratio
is contextual, not a fresh paired CPU measurement in this checkpoint.

All six timed outputs and both diagnostic outputs were byte-identical:

```text
complete TFOsorted SHA-256:
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075

task rows:                  48,432
scoreInfo groups:        1,086,495
all attempts:            4,345,980
F1 forward attempts:     1,735,752
reverse requests:        1,086,495
selected continuations:  1,086,495
continuation failures:           0
fallback / CPU oracle:           0
```

## Remaining bottleneck

The real-promoter prepared-reuse diagnostic measured:

```text
whole-query scoreInfo                     25.63 s
F1 forward + reverse endpoint stages      10.85 s
selected CPU continuation                 19.98 s
  reverse-start recovery                  15.76 s
  banded traceback                         3.33 s
triplex conversion                         7.33 s
```

Total wall was 115.77 seconds. The authority stage profile attributed only
0.12 seconds to serialization and 0.20 seconds to cluster/rank sorting. After
subtracting the known GPU and consumer stages, approximately 52 seconds remain
outside the existing timers. The next checkpoint must profile F1 attempt/group
construction and host round bookkeeping before authorizing a continuation
thread pool or CPU/GPU pipeline.

## Boundaries

```text
default enabled:                    no
complete-output exactness:          pass on one query x one promoter shard
continuous 4-12 kb envelope:        not established
full promoter concat:               not measured
consumer_cuda_authorized:           false
production_authorized:              false
bioinformatics_v2_state:            unchanged
10x full-output claim:              prohibited
```

Machine-readable evidence is in `performance_receipt.json`. Full local output
artifacts remain under
`/data/wenyujianData/linjieData/longtarget_runs/exact_long_query_hybrid_f1_continuation_profile_v1`.
