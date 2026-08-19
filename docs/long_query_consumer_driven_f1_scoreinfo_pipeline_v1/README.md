# F1 scoreInfo and CPU/GPU pipeline spike

This checkpoint implements and measures four bounded optimizations for the
long-query F1 scheduler:

1. overlap one completed batch's CPU continuation with the next batch's GPU
   scoreInfo stage;
2. automatically use the validated legacy-byte shared-memory scoreInfo kernel
   when the query fits the device shared-memory limit;
3. retain the existing task-level continuation worker control for additional
   physical cores;
4. audit exact duplicate transformed target tasks before considering a dedup
   execution path.

It does not split one lncRNA across two GPUs. Multiple GPUs are intended to run
independent lncRNA jobs at the outer scheduler level.

## Source and controls

The implementation checkpoint is:

```text
branch: long-query-f1-scoreinfo-pipeline-v1
commit: 05fc765c3fff94ef35b09e4753e4c5950a1f7a04
binary SHA-256:
7b4a0206172b212b3b60a6f14bca90142d788dc7c6b615fefea99047701d1822
```

The pipeline remains default-off and requires the F1 scheduler:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1
FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1
FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1
FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=2
FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1
```

The pipeline keeps at most one continuation batch in flight. The sequence is:

```text
batch N F1 forward/reverse rounds finish
  -> signal the GPU-safe boundary
  -> run batch N selected CPU continuations asynchronously

main thread
  -> compute batch N+1 scoreInfo on the GPU
  -> join and commit batch N in task order
  -> submit batch N+1 F1 GPU rounds
```

It fails closed if F1 is disabled or shared phase-timing state is enabled. A
GPU/consumer failure is joined before exit and cannot fall back to a full CPU
attempt replay.

For F1, shared-memory scoreInfo selection is automatic when the query resource
requirement fits the CUDA opt-in dynamic shared-memory limit. It can be disabled
without changing other F1 behavior:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO=0
```

The duplicate audit is diagnostic only:

```text
FASIM_LONG_QUERY_TASK_DUPLICATE_AUDIT=1
```

It uses FNV bucketing only as an index and confirms equality byte-for-byte, so
a hash collision cannot be counted as an exact duplicate.

## Exactness

The final binary passed complete-output checks at three discrete query lengths:

| Query length | Selected continuations | Failures | Complete TFOsorted SHA-256 |
| ---: | ---: | ---: | --- |
| 4,006 nt | 245,422 | 0 | `a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b` |
| 8,181 nt | 214,604 | 0 | `b49e3fa33ec1ae5961032f420cfe1a60d5a5b12f8886828be997f7cd5219a578` |
| 12,397 nt | 196,292 | 0 | `714cd07a86d86eca5c2858bae5d409b569b173aca12b0db44fcda9062ad40500` |

The automatic shared-memory requirements were 24,096, 49,152, and 74,400
bytes respectively, under the measured 101,376-byte opt-in limit. Explicitly
disabling automatic shared scoreInfo on the 4,006 nt fixture produced the same
complete output and the same frozen F1 structural counts.

The final real-shard run on `LINC01501 x shard_0009` also remained exact:

```text
task rows                         48,432
scoreInfo groups               1,086,495
all four-round attempts        4,345,980
ordered forward attempts       1,735,752
reverse requests/scored        1,086,495 / 1,086,495
selected continuations         1,086,495
continuation failures                  0
threshold / best / last          870,076 / 119,878 / 96,541

complete TFOsorted SHA-256:
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075

F1 structural signature SHA-256:
6659cbdc18137d95089342c5971559d8626b0f1eff0f538282c7def4957ef036
```

The structural signature includes task identity, group/attempt accounting,
selection reason counts, ordered round vectors, continuation counts, and error
state while excluding timings and worker-count fields.

## Engineering performance

All numbers below are single-run, resource-isolated diagnostics collected
while the separate 16-thread OpenMP production queue remained active on other
logical CPUs. The spike used CPU set `0,9` and physical GPU 1.

### Shared scoreInfo

Compared with the frozen two-worker F1 run:

| Metric | Global-state scoreInfo | Shared scoreInfo |
| --- | ---: | ---: |
| End-to-end wall | 53.46 s | 41.06 s |
| scoreInfo total | 25.5579 s | 13.1215 s |
| scoreInfo main GPU call | 20.5628 s | 8.12863 s |

The scoreInfo stage improved by 1.95x and end-to-end wall improved by 1.30x.
A two-tasks-per-warp experiment was removed after its bounded main-kernel time
regressed from 3.92 s to 4.57 s.

### CPU/GPU overlap

The final source-bound real-shard run produced:

```text
wall                              32.91 s
pipeline launches / commits       13 / 13
pipeline failures                  0
scoreInfo total                   13.2569 s
scoreInfo main GPU call            8.22926 s
continuation covered              13.1268 s
join wait                          5.45197 s
```

This is 1.25x faster than the shared-scoreInfo run and 1.62x faster than the
earlier two-worker global-scoreInfo F1 run. Relative to the separately frozen
CPU authority median of 364.75 s, it is a contextual 11.08x result on this one
query/shard pair. It is not a paired-repeat or general long-query speed claim.

### Continuation workers

The prior same-binary worker sweep remains applicable:

```text
1 worker                          66.74 s
2 physical-core workers          53.46 s
4 SMT workers on those cores     52.59 s
```

Two physical workers nearly halved continuation wall. Adding two SMT siblings
provided only another 1.6% end-to-end improvement. A true 4/8 physical-core
sweep is deferred until isolated cores are available; the production queue was
not stopped for this spike.

### Duplicate audit

The real shard contains 48 transformed tasks per target window and 48,432 task
rows in total. The exact audit found:

```text
tasks                              48,432
unique byte sequences              48,432
exact duplicates                        0
cell proxy before / after     242,084,160 / 242,084,160
```

There is therefore no deduplication execution path in this checkpoint.

## Reproduction

The integrated fixture check builds the dedicated binary by default and tests
startup guards, pipeline exactness, automatic shared scoreInfo, the explicit
auto-off path, and duplicate-audit accounting:

```bash
make check-long-query-consumer-f1-scoreinfo-pipeline-v1
```

The lower-level regressions used for this checkpoint were:

```bash
make check-fasim-forward-continuation-query
make build-fasim-ssw-profile-cache-test
FASIM_SSW_PROFILE_CACHE=1 ./tests/test_fasim_ssw_profile_cache
make build-fasim-transferstring-table-test
./tests/test_fasim_transferstring_table
```

## Boundaries

```text
default pipeline:                    off
default continuation workers:        1
full-output exactness:               pass on the checked fixtures and shard
formal isolated paired performance:  pending
consumer_cuda_authorized:            false
production_authorized:               false
bioinformatics_v2_state:             unchanged
```

This validates three discrete query lengths, not a continuous 4--12 kb
envelope. A 24,137 nt probe correctly rejected shared scoreInfo and selected
the global-state scoreInfo path, but the later F1 attempt kernel failed its CUDA
launch resource envelope. This checkpoint therefore does not claim arbitrary
24--33 kb support. Full promoter concat and fresh multi-query validation also
remain pending.

