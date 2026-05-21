# Fasim Sharded Worker 4-Contig 2-GPU Characterization

This note records a local 2-GPU characterization of process-level contig
sharding on a real 4-contig workload. The 2-worker mode validates local 2-GPU
process-level scaling. The 4-worker mode shares the same 2 GPUs and is
diagnostic oversubscription only; it is not a 4-GPU scaling result.

## Scope

This is a docs/result PR only:

- No chunk splitting is added.
- No overlap heuristic is added.
- No in-process multi-GPU runtime is added.
- No Fasim C++ runtime or output semantics are changed.
- Speed environment variables remain explicit.
- 4-worker mode on this machine shares 2 GPUs and is not a 4-GPU claim.

## Workload

The local hg38 data available for large chromosome-scale runs currently covers
chr11, chr21, and chr22. To exercise 4-contig scheduling on this 2-GPU machine,
this run uses the top 4 contigs from a real local `rheMac10NonChromosome.fa`
FASTA:

```text
workload: rheMac10_nonchrom_top4_H19
target:   top 4 contigs from rheMac10NonChromosome.fa
contigs:  4
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

## Command

```bash
timeout 900s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload rheMac10_nonchrom_top4_H19:.tmp/fasim_sharded_worker_4contig_2gpu/inputs/rheMac10_nonchrom_top4.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_sharded_worker_4contig_2gpu/run \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional SSW AVX2/ProfileContext add-ons were not enabled for this run.

## Correctness

Digest equality held for every worker count:

```text
all_digest_match:              true
merged_records:                734
duplicate_records_removed:     4
digest:                        ab964cc85c7e8d3e7015e8351ad6c5a0afb4c595e664f7f6795808ce774ad755
```

## Timing

`wall_seconds` is the sharded worker wall time reported by the scaling wrapper.
`runner_total_seconds` includes the validation single-run audit for that worker
count and is not the speedup numerator.

| mode | workers | GPUs used | GPU sharing | wall seconds | speedup vs 1 worker | speedup vs single whole run | runner total seconds | digest |
|---|---:|---|---|---:|---:|---:|---:|---|
| sharded | 1 | 0,1 configured | no effective sharing | 13.7715 | 1.0000x | 1.0004x | 27.6812 | clean |
| sharded | 2 | 0,1 | no | 7.7348 | 1.7805x | 1.7812x | 21.2285 | clean |
| sharded | 4 | 0,1 | yes | 5.3810 | 2.5593x | 2.5604x | 19.5026 | clean |

The 4-worker row is a scheduler/GPU-sharing stress result. It should not be
described as 4-GPU scaling because this machine has 2 GPUs.

## Per-Worker Balance

| workers | per-worker seconds | per-worker records |
|---:|---|---|
| 1 | 13.7715 | 734 |
| 2 | 7.7348, 7.2169 | 295, 439 |
| 4 | 5.3810, 4.8556, 2.6142, 2.6565 | 94, 294, 145, 201 |

The 2-worker run validates local 2-GPU process-level scaling. The 4-worker run
shows the scheduler and deterministic merge remain clean under oversubscription,
but it also exposes the expected shard-size imbalance: the largest shard
dominates wall time.

## Per-Shard Timing

| workers | QNVO02000334.1 | ML143124.1 | ML143121.1 | ML143119.1 |
|---:|---:|---:|---:|---:|
| 1 | 5.0185 | 4.2999 | 2.2025 | 2.2314 |
| 2 | 5.4680 | 4.9769 | 2.2251 | 2.2497 |
| 4 | 5.3772 | 4.8484 | 2.6021 | 2.6506 |

## Interpretation

This run extends the previous two-contig result to a real 4-contig workload:

```text
validated:
  1 vs 2 GPU-backed workers on the local 2-GPU machine
  digest-clean deterministic merge on a 4-contig workload
  scheduler/report stability for 1/2/4 worker modes

diagnostic only:
  4 workers sharing 2 GPUs

not validated:
  4-GPU scaling
  single-chromosome chunking
  safe-overlap chunk mode
```

The local 2-worker result is positive. The 4-worker result is useful as an
oversubscription stress check, but a real 4-GPU claim requires a 4-GPU machine
with workers pinned to `--gpu-ids 0,1,2,3`.

## Next Steps

For a real 4-GPU characterization, rerun a 4+ contig workload on a 4-GPU host:

```bash
--workers 1,2,4
--gpu-ids 0,1,2,3
```

If scaling is limited by imbalance, improve estimated-cells assignment before
changing runtime behavior. Single-chromosome scaling remains a separate
chunking and safe-overlap design problem.
