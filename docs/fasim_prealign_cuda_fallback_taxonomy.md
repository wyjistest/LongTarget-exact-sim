# Fasim PreAlign CUDA Fallback Taxonomy

This note characterizes why fallback-heavy tiny-region workloads fall back from
the current preAlign CUDA path.

## Scope

This is a telemetry/docs/result checkpoint:

- No output, scoring, threshold, endpoint, CIGAR, traceback, merge semantics,
  scheduler default, chunking, overlap, or in-process multi-GPU behavior is
  changed.
- CPU Fasim output remains authoritative.
- The only runtime code change is benchmark telemetry that classifies existing
  preAlign CUDA fallback events into reason buckets.
- `--group-target-records` remains default-off.

## Telemetry

Fallback events are still counted by the existing total:

```text
benchmark.fasim_prealign_cuda_fallbacks
```

This PR adds reason counters:

```text
benchmark.fasim_prealign_cuda_fallback_unsupported_rule
benchmark.fasim_prealign_cuda_fallback_unsupported_sequence_alphabet
benchmark.fasim_prealign_cuda_fallback_too_few_tasks
benchmark.fasim_prealign_cuda_fallback_too_many_tasks
benchmark.fasim_prealign_cuda_fallback_target_too_short
benchmark.fasim_prealign_cuda_fallback_query_too_long_or_unsupported
benchmark.fasim_prealign_cuda_fallback_cuda_allocation_or_launch
benchmark.fasim_prealign_cuda_fallback_empty_candidate_set
benchmark.fasim_prealign_cuda_fallback_unknown
```

The reason counters sum to `fasim_prealign_cuda_fallbacks`.

## Runtime

Runs used the current-base local opt-in candidate:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_VERBOSE=0
```

The runner used process-level GPU assignment:

```text
--gpu-ids 0,1
--auto-cpu-core-ranges
--cpu-pool 0-19
--cpu-cores-per-worker 3
```

## Script

`scripts/benchmark_fasim_prealign_cuda_fallback_taxonomy.py` runs the real
`scripts/fasim_sharded_runner.py` path and writes:

```text
report.json
raw.tsv
```

It collects:

```text
workload
target_record_count
group_target_records
grouped_shard_count
worker_count
wall_seconds
digest_match
merged_records
duplicate_removed
prealign_cuda_requested
prealign_cuda_active
prealign_cuda_fallbacks
fallback reason counters
prealign_cuda_tasks
prealign_cuda_batches
topK
max_tasks
suppress_bp
profile_cache_hit_rate
```

## Commands

NEAT1 first64:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=64{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa \
  > .tmp/fasim_prealign_cuda_fallback_taxonomy_inputs/NEAT1_DNAseq_first64.fa

timeout 1200s python3 scripts/benchmark_fasim_prealign_cuda_fallback_taxonomy.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_fallback_taxonomy_neat1_first64 \
  --output-mode lite \
  --group-target-records none,8,16,32 \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload NEAT1_first64:.tmp/fasim_prealign_cuda_fallback_taxonomy_inputs/NEAT1_DNAseq_first64.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa:0
```

The NEAT1 full matrix timed out while attempting `group=32` after completing
default, group=8, and group=16 rows for workers 1/2/4. Those completed rows are
enough to classify the fallback reason.

MALAT1 first8:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=8{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa \
  > .tmp/fasim_prealign_cuda_fallback_taxonomy_inputs/MALAT1_DNAseq_first8.fa

timeout 240s python3 scripts/benchmark_fasim_prealign_cuda_fallback_taxonomy.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_fallback_taxonomy_malat1_default_w4 \
  --output-mode lite \
  --group-target-records none \
  --workers 4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MALAT1_first8:.tmp/fasim_prealign_cuda_fallback_taxonomy_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0
```

MEG3 fallback-clean comparison:

```bash
timeout 360s python3 scripts/benchmark_fasim_prealign_cuda_fallback_taxonomy.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_fallback_taxonomy_meg3_group32_w4 \
  --output-mode lite \
  --group-target-records none,32 \
  --workers 4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MEG3_full:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0
```

## Results

### NEAT1 First64

Input:

```text
target records: 64
merged records: 2,838
duplicate removed: 0
```

All completed NEAT1 rows were digest-clean. Every fallback was classified as
`cuda_allocation_or_launch`, with `unknown=0`.

| group | shards | workers | wall s | digest | fallbacks | cuda allocation/launch | unknown | tasks | batches |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| default | 64 | 1 | 93.718 | clean | 64 | 64 | 0 | 0 | 0 |
| default | 64 | 2 | 48.487 | clean | 64 | 64 | 0 | 0 | 0 |
| default | 64 | 4 | 26.509 | clean | 64 | 64 | 0 | 0 | 0 |
| 8 | 8 | 1 | 77.323 | clean | 8 | 8 | 0 | 0 | 0 |
| 8 | 8 | 2 | 40.300 | clean | 8 | 8 | 0 | 0 | 0 |
| 8 | 8 | 4 | 21.572 | clean | 8 | 8 | 0 | 0 | 0 |
| 16 | 4 | 1 | 76.276 | clean | 4 | 4 | 0 | 0 | 0 |
| 16 | 4 | 2 | 39.300 | clean | 4 | 4 | 0 | 0 | 0 |
| 16 | 4 | 4 | 21.143 | clean | 4 | 4 | 0 | 0 | 0 |

### MALAT1 First8

Input:

```text
target records: 8
merged records: 796
duplicate removed: 3
```

The workers=4 default row was digest-clean. Every fallback was classified as
`cuda_allocation_or_launch`, with `unknown=0`.

| group | shards | workers | wall s | digest | fallbacks | cuda allocation/launch | unknown | tasks | batches |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| default | 8 | 4 | 7.867 | clean | 8 | 8 | 0 | 0 | 0 |

### MEG3 Full

Input:

```text
target records: 532
merged records: 4,914
duplicate removed: 1
```

MEG3 remains fallback-clean.

| group | shards | workers | wall s | digest | fallbacks | top reason | tasks | batches |
|---:|---:|---:|---:|---|---:|---|---:|---:|
| default | 532 | 4 | 97.976 | clean | 0 | none | 25,536 | 532 |
| 32 | 17 | 4 | 10.008 | clean | 0 | none | 25,536 | 522 |

## Decision

NEAT1/MALAT1 sampled fallback events are not explained by rule, alphabet,
target length, task count, or empty-candidate buckets in this matrix. They are
classified as CUDA allocation/launch/resource-path failures before any preAlign
CUDA tasks complete:

```text
prealign_cuda_active = 0
prealign_cuda_tasks = 0
prealign_cuda_batches = 0
fallback_cuda_allocation_or_launch = fallbacks
fallback_unknown = 0
```

Grouping reduces fallback event count by reducing the number of Fasim
invocations:

```text
NEAT1 first64:
  default: 64 fallback events
  group=8: 8 fallback events
  group=16: 4 fallback events
```

Grouping does not fix the underlying CUDA resource-path failure. It only changes
how many times the fallback is encountered.

Recommended next step:

```text
Do not change grouping defaults.
Do not claim NEAT1/MALAT1 are on the preAlign CUDA fast path.
If this fallback needs to be fixed, investigate the preAlign CUDA launch/resource
requirements for these RNA/query shapes in a separate narrow PR.
```
