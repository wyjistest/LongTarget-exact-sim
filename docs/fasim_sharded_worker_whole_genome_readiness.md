# Fasim Sharded Worker Whole-Genome Readiness

This note characterizes the current process-level sharded runner stack on a
larger multi-contig workload. It is a readiness checkpoint for whole-genome
execution, not a new runtime optimization.

## Scope

This characterization uses:

- contig-level sharding
- deterministic merge and digest validation
- manifest-backed runs
- explicit CPU affinity
- local 2-GPU worker density

It does not add chunking, overlap, in-process multi-GPU execution, a default
worker policy, or Fasim C++ runtime/output semantic changes.

## Workload

```text
workload: rheMac10_nonchrom_top8_H19
target: .tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa
rna: H19.fa
rule: 1
shards: 8
GPUs: 0,1
CPU pool: 0-17
CPU cores per worker: 3
auto CPU ranges: enabled
output mode: lite
```

Per-worker environment:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Run command:

```bash
timeout 1800s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload rheMac10_nonchrom_top8_H19:.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_whole_genome_sharded_readiness/top8_2gpu_cpu_affinity \
  --output-mode lite \
  --workers 1,2,4,6 \
  --gpu-ids 0,1 \
  --manifest \
  --auto-cpu-core-ranges \
  --cpu-pool 0-17 \
  --cpu-cores-per-worker 3 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

## Result

Digest equality was clean for all runs:

```text
merged_digest = fbc012361b80491e4b4ecca6a04735b8657b49f6b9d167763ecb9139e300ef15
single_digest = fbc012361b80491e4b4ecca6a04735b8657b49f6b9d167763ecb9139e300ef15
merged_records = 1184
duplicate_removed = 5
failed_shards = []
resumed_shards = []
```

| workers | workers/GPU | CPU ranges | wall seconds | speedup vs 1 worker | digest |
|---:|---:|---|---:|---:|---|
| 1 | 0.5 | 0-2 | 21.8887 | 1.0000x | clean |
| 2 | 1.0 | 0-2,3-5 | 11.2174 | 1.9513x | clean |
| 4 | 2.0 | 0-2,3-5,6-8,9-11 | 5.7886 | 3.7814x | clean |
| 6 | 3.0 | 0-2,3-5,6-8,9-11,12-14,15-17 | 5.0348 | 4.3475x | clean |

The best local row is 6 workers on 2 GPUs, equivalent to
`workers_per_gpu=3`. This remains a local 2-GPU candidate, not a default policy
and not evidence for 4-GPU scaling.

## Per-Shard Timing

The 1-worker run shows a long-tail shape even on this 8-contig workload:

```text
5.7441s, 4.4548s, 2.9755s, 2.3129s, 2.2661s, 2.1784s, 0.9700s, 0.9176s
```

The 6-worker run keeps the slowest worker near the largest single-shard time:

```text
per_worker_seconds:
  5.0348s, 4.6415s, 4.0370s, 3.8473s, 2.4849s, 2.3752s
```

This supports process-level contig sharding as the next whole-genome execution
strategy. If larger primary-chromosome workloads show a single large contig
dominating the tail, the next step should be straggler analysis before any
chunking design.

## Decision

```text
validated:
  manifest-backed readiness matrix
  auto CPU affinity with taskset
  digest equality
  local 2-GPU 6-worker candidate

not claimed:
  4-GPU scaling
  default workers_per_gpu policy
  chunking / overlap safety
  single-contig parallelism
```

Next step: run a broader primary-chromosome matrix. If contig-level stragglers
limit scaling there, start a separate straggler/load-balance PR before any
safe-overlap chunking design.
