# Fasim Sharded Worker Density on 2 GPUs

This note characterizes process-level worker density on the local 2-GPU machine.
It uses the existing workload-matrix wrapper and does not change scheduler or
runtime behavior.

## Scope

This is a docs/result PR only:

- No chunk splitting is added.
- No overlap heuristic is added.
- No in-process multi-GPU runtime is added.
- No Fasim C++ runtime or output semantics are changed.
- No default worker policy is changed.
- No 4-GPU scaling is claimed.

The goal is to determine whether the local 2-GPU machine benefits from more than
one worker per GPU for multi-contig workloads.

## Workload

This run uses the top 8 contigs from a real local `rheMac10NonChromosome.fa`
FASTA:

```text
workload: rheMac10_nonchrom_top8_H19
target:   top 8 contigs from rheMac10NonChromosome.fa
contigs:  8
RNA:      H19.fa
rule:     1
binary:   fasim_longtarget_cuda
GPU ids:  0,1
```

Contigs:

| contig | bases |
|---|---:|
| QNVO02000334.1 | 1,229,889 |
| ML143124.1 | 1,117,261 |
| ML143121.1 | 1,005,795 |
| ML143119.1 | 862,827 |
| ML143120.1 | 823,856 |
| ML143117.1 | 738,392 |
| ML143122.1 | 733,739 |
| ML143118.1 | 669,983 |

## Command

```bash
timeout 1800s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload rheMac10_nonchrom_top8_H19:.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_sharded_worker_density_2gpu/run \
  --output-mode lite \
  --workers 1,2,3,4,6,8 \
  --gpu-ids 0,1 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional SSW AVX2/ProfileContext add-ons were not enabled for this run.

Reconciliation note: this historical run recorded final-speed-stack environment
labels. The current repo-local Fasim binary now reads
`FASIM_TRANSFERSTRING_TABLE`, `FASIM_GPU_DP_COLUMN_AUTO`,
`FASIM_SSW_PROFILE_CACHE`, and `FASIM_EXACT_COLUMN_EXTEND_BATCH` as default-off
opt-ins, but this document was not rerun after that integration. Treat the
timings as historical telemetry, not fresh evidence for the reconciled binary.

## Correctness

Digest equality held for every worker count:

```text
all_digest_match:              true
merged_records:                1184
duplicate_records_removed:     5
digest:                        fbc012361b80491e4b4ecca6a04735b8657b49f6b9d167763ecb9139e300ef15
```

## Density Results

`wall_seconds` is the sharded worker wall time reported by the scaling wrapper.
`runner_total_seconds` includes the validation single-run audit for that worker
count and is not the speedup numerator.

| workers | workers/GPU | GPU sharing | wall seconds | speedup vs 1 worker | speedup vs 2 workers | runner total seconds | digest |
|---:|---:|---|---:|---:|---:|---:|---|
| 1 | 0.5 | no | 23.4301 | 1.0000x | 0.4961x | 45.9326 | clean |
| 2 | 1.0 | no | 11.6237 | 2.0157x | 1.0000x | 33.6160 | clean |
| 3 | 1.5 | yes | 8.5491 | 2.7406x | 1.3596x | 34.3556 | clean |
| 4 | 2.0 | yes | 8.7590 | 2.6750x | 1.3271x | 30.4185 | clean |
| 6 | 3.0 | yes | 5.0676 | 4.6235x | 2.2937x | 29.2841 | clean |
| 8 | 4.0 | yes | 6.2190 | 3.7675x | 1.8691x | 29.4308 | clean |

The best result in this run is 6 workers on 2 GPUs. The 8-worker run regresses,
so oversubscription has a visible limit on this workload.

## Worker Assignment

The scheduler assigns GPU ids round-robin when there are more workers than GPUs.

| workers | max worker seconds | per-worker records |
|---:|---:|---|
| 1 | 23.4301 | 1184 |
| 2 | 11.6237 | 552, 632 |
| 3 | 8.5491 | 215, 551, 418 |
| 4 | 8.7590 | 168, 366, 266, 384 |
| 6 | 5.0676 | 94, 294, 145, 201, 257, 193 |
| 8 | 6.2190 | 94, 294, 145, 201, 183, 121, 72, 74 |

The 6-worker result benefits from splitting the workload while still keeping
enough work per process. The 8-worker result maps one worker per shard, which
increases sharing overhead and slows the largest shards relative to 6 workers.

## Interpretation

This run confirms that `workers = gpu_count` is not always the best local policy.
The current final stack still has enough CPU-side work around each Fasim worker
that running multiple worker processes per GPU can improve wall time.

For this workload and host:

```text
validated:
  digest-clean worker density on a real 8-contig workload
  2-GPU process-level scaling
  local oversubscription benefit up to 6 workers / 2 GPUs

candidate:
  workers_per_gpu = 3 for this local 2-GPU workload

not validated:
  general default worker policy
  4-GPU scaling
  single-contig chunking
  safe-overlap chunk mode
```

This is not enough to change defaults. It is enough to justify a future
default-off scheduler option such as `--workers-per-gpu`, followed by broader
workload validation.

## Decision

For local 2-GPU multi-contig workloads, `workers_per_gpu=2` is no longer the only
interesting candidate. This run suggests testing `workers_per_gpu=3` as well.

Before adding a default or auto policy:

```text
1. Repeat on a larger 8+ contig workload.
2. Repeat on hg38 multi-chromosome data when enough contigs are available.
3. Compare workers_per_gpu=1,2,3 across workloads.
4. Keep digest equality as the gate.
```

If density gains disappear on larger workloads, keep `workers_per_gpu=1` as the
safer default. If density gains hold, add a default-off scheduler option rather
than changing runtime behavior.
