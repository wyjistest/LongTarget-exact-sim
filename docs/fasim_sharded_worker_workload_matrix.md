# Fasim Sharded Worker Workload Matrix

This note describes the workload-matrix characterization step for process-level
contig sharding. It runs the existing sharded worker scaling wrapper across one
or more multi-contig workloads and summarizes digest equality, worker balance,
and wall-clock scaling fields.

## Scope

This PR is characterization only:

- No chunk splitting is added.
- No overlap heuristic is added.
- No in-process multi-GPU runtime is added.
- No Fasim C++ runtime or output semantics are changed.
- Speed environment variables remain explicit.
- Validation mode is used for digest audit, not as a performance setting.

Contig-level sharding only scales workloads with multiple FASTA records. A
single chromosome FASTA remains one shard and should not be expected to scale
until a separate chunking and safe-overlap design exists.

## Local Contract Check

Run:

```bash
make benchmark-fasim-sharded-worker-workload-matrix
```

The target creates a deterministic two-contig fixture from `testDNA.fa`, runs
1/2/4 worker modes, and verifies the matrix report contract and digest equality.
It is a smoke check, not a production scaling claim.

## Production-Like Workloads

Use `--workload NAME:TARGET_FASTA:RNA_FASTA:RULE` once per workload. The target
FASTA should contain multiple contigs or chromosomes.

Example for a real multi-contig hg38 subset:

```bash
python3 ./scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_sharded_worker_workload_matrix \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1,2,3 \
  --cpu-core-ranges 0-7,8-15,16-23,24-31 \
  --workload hg38_chr11_chr21:hg38_chr11_chr21.fa:H19.fa:1 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional add-ons remain explicit:

```bash
--env FASIM_SSW_AVX2=1 \
--env FASIM_SSW_PROFILE_CONTEXT=1
```

## Report Fields

The matrix report writes `report.json` with one entry per workload. Each workload
entry includes:

```text
name
target
rna
rule
shard_count
all_digest_match
baseline
runs[*].worker_count
runs[*].gpu_ids
runs[*].cpu_core_ranges
runs[*].per_worker_seconds
runs[*].per_worker_estimated_cells
runs[*].per_worker_records
runs[*].per_shard_seconds
runs[*].per_shard_records
runs[*].per_shard_digest
runs[*].merged_records
runs[*].merged_digest
runs[*].single_digest
runs[*].single_vs_sharded_digest_match
runs[*].duplicate_records_removed
runs[*].wall_seconds
runs[*].runner_total_seconds
runs[*].speedup_vs_single_worker
runs[*].speedup_vs_single_whole_run
runs[*].fallbacks
runs[*].mismatches
```

The top-level `summary.all_digest_match` is true only when every workload and
worker count passes the digest gate.

## Decision Rules

If digest equality holds and multi-contig workloads scale, document
process-level sharding as the recommended outer-parallel execution strategy for
large multi-contig runs.

If scaling is limited by imbalance, improve estimated-cells planning before
changing runtime behavior.

If a workload is a single FASTA record, keep chunking as a future separate
safe-overlap design. Do not add chunking to this matrix PR.
