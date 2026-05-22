# Fasim Whole-Genome Shard Balance

This is a plan-only shard balance checkpoint for whole-genome readiness. It
does not run Fasim, validate digest equality, or claim runtime scaling. The
goal is to expose likely contig-level stragglers before launching expensive
primary-chromosome or whole-genome runs.

## Scope

Validated in this PR:

- FASTA contigs are converted into contig-level shard plans.
- Worker assignments use the same largest-first policy as
  `scripts/fasim_sharded_runner.py`.
- CPU ranges can be derived for each analyzed worker count.
- Reports include predicted makespan, imbalance, idle fraction, and straggler
  shards.

Out of scope:

- chunk splitting or overlap
- in-process multi-GPU
- Fasim C++ runtime or output semantic changes
- digest or wall-clock scaling claims
- default worker policy changes

## Command

```bash
python3 scripts/analyze_fasim_shard_balance.py \
  --target .tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa \
  --workload-name rheMac10_nonchrom_top8_H19 \
  --workers 1,2,4,6,8 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-15 \
  --cpu-cores-per-worker 2 \
  --output .tmp/fasim_whole_genome_shard_balance_rheMac10_top8.json
```

The local checkout also has `hg38_chr21_chr22.fa` under
`.tmp/fasim_sharded_worker_workload_matrix_real/inputs/`. A full hg38 primary
FASTA was not present in the repo-local inputs when this report was written.

## Metrics

The analyzer uses `estimated_cells` when available and falls back to contig
length otherwise. Current contig shards expose length only, so the metric below
is estimated length.

| workload | contigs | workers | predicted makespan length | load imbalance | idle estimate | straggler shards |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| rheMac10_nonchrom_top8_H19 | 8 | 1 | 7,181,742 | 1.0000 | 0.0000 | all shards |
| rheMac10_nonchrom_top8_H19 | 8 | 2 | 3,595,187 | 1.0012 | 0.0012 | ML143124.1, ML143121.1, ML143117.1, ML143122.1 |
| rheMac10_nonchrom_top8_H19 | 8 | 4 | 1,899,872 | 1.0582 | 0.0550 | QNVO02000334.1, ML143118.1 |
| rheMac10_nonchrom_top8_H19 | 8 | 6 | 1,493,839 | 1.2480 | 0.1987 | ML143120.1, ML143118.1 |
| rheMac10_nonchrom_top8_H19 | 8 | 8 | 1,229,889 | 1.3700 | 0.2701 | QNVO02000334.1 |

The same analyzer shows why a two-contig workload should not be used to reason
about 4/6/8 worker scaling:

| workload | contigs | workers | predicted makespan length | load imbalance | idle estimate | empty workers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hg38_chr21_chr22_H19 | 2 | 1 | 97,528,451 | 1.0000 | 0.0000 | 0 |
| hg38_chr21_chr22_H19 | 2 | 2 | 50,818,468 | 1.0421 | 0.0404 | 0 |
| hg38_chr21_chr22_H19 | 2 | 4 | 50,818,468 | 2.0843 | 0.5202 | 2 |
| hg38_chr21_chr22_H19 | 2 | 6 | 50,818,468 | 3.1264 | 0.6801 | 4 |
| hg38_chr21_chr22_H19 | 2 | 8 | 50,818,468 | 4.1685 | 0.7601 | 6 |

## Interpretation

For `rheMac10_nonchrom_top8_H19`, the two-worker length plan is nearly balanced.
The 4-worker plan also has modest imbalance. At 6 and 8 workers, the plan begins
to expose contig granularity as the limiting factor: total parallelism rises,
but the largest remaining contig groups set the predicted makespan.

For `hg38_chr21_chr22_H19`, workers above the contig count are idle by design.
This is expected for contig-level sharding and is not a scheduler failure.

## Decision

Use this tool before a large primary-chromosome or whole-genome run:

- If load imbalance is acceptable, run the actual matrix with manifest/resume
  and CPU affinity.
- If one or two large contigs dominate the plan, first improve cost estimation
  or document the straggler risk.
- If contig-level granularity blocks scaling, start a separate safe-overlap
  chunking design PR.
- Do not implement chunking from this analysis PR.
