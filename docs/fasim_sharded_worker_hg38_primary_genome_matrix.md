# Fasim Sharded Worker hg38 Primary Genome Matrix

This note records a full hg38 primary-chromosome sharded run using the
whole-genome readiness stack: manifest-backed execution, automatic CPU affinity,
explicit GPU assignment, and deterministic merge. It is a local 2-GPU
characterization, not a 4-GPU scaling claim or a default scheduler policy.

## Scope

Validated here:

- full hg38 primary chromosomes, `chr1-22,chrX,chrY`
- 24 contig-level shards
- manifest-backed sharded runs
- automatic CPU core ranges
- 4-worker and 6-worker deterministic merge equality
- completed run manifests with no failed shards

Out of scope:

- UCSC alt, random, and unplaced contigs
- single whole-target full-genome audit
- 4-GPU scaling
- chunk splitting or overlap
- in-process multi-GPU
- Fasim C++ runtime or output semantic changes
- default worker policy changes

## Workload

```text
workload: hg38_primary_chromosomes_H19
target: .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa
source: UCSC hg38 per-chromosome FASTA, chr1-22 + chrX + chrY
contigs: 24
target_fasta_digest: d4b32d0c8e45e9c242fcada11025f73ff65275a7f0b01d4b8b26a70425f293ae
rna: H19.fa
rule: 1
binary: ./fasim_longtarget_cuda
GPUs: 0,1
CPU pool: 0-17
CPU cores per worker: 3
auto CPU ranges: enabled
output mode: lite
```

Input preparation stayed under `.tmp/` and is not committed:

```bash
mkdir -p .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes
for chrom in $(seq 1 22) X Y; do
  wget -q -O ".tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr${chrom}.fa.gz" \
    "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr${chrom}.fa.gz"
done

: > .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa.tmp
for chrom in $(seq 1 22) X Y; do
  gzip -cd ".tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr${chrom}.fa.gz" \
    >> .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa.tmp
done
mv .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa.tmp \
  .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa
```

Per-worker environment:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

## Shard Balance Plan

The plan-only analyzer used length as the cost metric because estimated cells
are not available for FASTA-only contig plans.

```bash
python3 scripts/analyze_fasim_shard_balance.py \
  --target .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa \
  --workload-name hg38_primary_chromosomes_H19 \
  --workers 1,2,4,6 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-17 \
  --cpu-cores-per-worker 3 \
  --output .tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_shard_balance_cpu0_17.json
```

| workers | predicted makespan length | load imbalance | idle estimate | straggler shards |
| ---: | ---: | ---: | ---: | --- |
| 1 | 3,088,269,832 | 1.0000 | 0.0000 | all shards |
| 2 | 1,546,288,544 | 1.0014 | 0.0014 | chr1, chr4, chr5, chr9, chr11, chr13, chr14, chr16, chr18, chr21, chrX, chrY |
| 4 | 776,170,262 | 1.0053 | 0.0053 | chr3, chr6, chr8, chr13, chr16, chrY |
| 6 | 520,654,676 | 1.0115 | 0.0114 | chr6, chr7, chr12, chrY |

The plan does not predict a severe contig-level straggler for 4 or 6 workers.

## Run Commands

Four-worker cross-check:

```bash
timeout 21600s python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4 \
  --output-mode lite \
  --workers 4 \
  --gpu-ids 0,1 \
  --manifest .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/run_manifest.json \
  --auto-cpu-core-ranges \
  --cpu-pool 0-17 \
  --cpu-cores-per-worker 3 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Six-worker local density candidate:

```bash
timeout 21600s python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target .tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6 \
  --output-mode lite \
  --workers-per-gpu 3 \
  --gpu-ids 0,1 \
  --manifest .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/run_manifest.json \
  --auto-cpu-core-ranges \
  --cpu-pool 0-17 \
  --cpu-cores-per-worker 3 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

The full single whole-target audit was not run. A 1-worker sharded baseline was
started and stopped during the first large shard after it proved to be a long
blocking job. The correctness gate for this PR is therefore cross-worker
sharded deterministic equality: 4-worker and 6-worker merged digests must match.

## Results

| workers | GPUs | CPU ranges | wall seconds | merged records | duplicate removed | failed shards | resumed shards | merged digest |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 0,1 | 0-2,3-5,6-8,9-11 | 2,898.2267 | 178,425 | 1,116 | 0 | 0 | `8dc08e4174c8174b816bd3f003b1c55314765a5df744940305bb6876880b7856` |
| 6 | 0,1 | 0-2,3-5,6-8,9-11,12-14,15-17 | 2,949.7175 | 178,425 | 1,116 | 0 | 0 | `8dc08e4174c8174b816bd3f003b1c55314765a5df744940305bb6876880b7856` |

Digest equality:

```text
4-worker merged_digest == 6-worker merged_digest
8dc08e4174c8174b816bd3f003b1c55314765a5df744940305bb6876880b7856
```

Both runs produced:

```text
sharded_records: 179,541
sharded_unique_records: 178,946
merged_raw_records: 178,946
merged_records: 178,425
duplicate_records_removed: 1,116
failed_shards: []
resumed_shards: []
```

## Worker Timing

| workers | worker | GPU | CPU range | wall seconds | records | shards |
| ---: | ---: | --- | --- | ---: | ---: | --- |
| 4 | 0 | 0 | 0-2 | 2,898.2267 | 47,862 | chr1, chr10, chr15, chr17, chr21, chrX |
| 4 | 1 | 1 | 3-5 | 2,863.7736 | 52,430 | chr2, chr7, chr11, chr14, chr19, chr20 |
| 4 | 2 | 0 | 6-8 | 2,747.4075 | 38,066 | chr3, chr6, chr8, chr13, chr16, chrY |
| 4 | 3 | 1 | 9-11 | 2,835.8453 | 40,588 | chr4, chr5, chr9, chr12, chr18, chr22 |
| 6 | 0 | 0 | 0-2 | 2,265.8391 | 39,186 | chr1, chr10, chr17, chr22 |
| 6 | 1 | 1 | 3-5 | 2,610.5911 | 34,027 | chr2, chr11, chr16, chr21 |
| 6 | 2 | 0 | 6-8 | 2,887.2691 | 27,882 | chr3, chr9, chr14, chr20 |
| 6 | 3 | 1 | 9-11 | 2,213.7786 | 27,385 | chr4, chr8, chr13, chr19 |
| 6 | 4 | 0 | 12-14 | 2,698.5156 | 23,406 | chr5, chr15, chr18, chrX |
| 6 | 5 | 1 | 15-17 | 2,949.7175 | 27,060 | chr6, chr7, chr12, chrY |

The observed 4-worker wall time was slightly better than 6 workers on this run.
This is not enough to change the local density candidate or default policy. It
does show that full-genome density should remain workload and host dependent.

## Per-Shard Timing

Per-shard digests were identical between the 4-worker and 6-worker runs. The
table below lists the 4-worker timing, which was the faster of the two runs.

| contig | seconds | records |
| --- | ---: | ---: |
| chr1 | 848.4321 | 15,431 |
| chr2 | 854.8982 | 13,697 |
| chr3 | 684.9949 | 8,453 |
| chr4 | 650.3795 | 6,957 |
| chr5 | 697.7316 | 8,194 |
| chr6 | 658.3969 | 8,142 |
| chr7 | 610.4762 | 10,241 |
| chr8 | 554.8234 | 8,088 |
| chr9 | 456.9945 | 8,492 |
| chr10 | 543.9636 | 9,236 |
| chr11 | 517.5338 | 9,347 |
| chr12 | 541.9033 | 7,400 |
| chr13 | 395.5495 | 4,132 |
| chr14 | 382.0449 | 5,430 |
| chr15 | 330.8939 | 5,624 |
| chr16 | 340.3792 | 7,974 |
| chr17 | 361.1243 | 9,059 |
| chr18 | 341.4968 | 4,085 |
| chr19 | 251.3893 | 8,208 |
| chr20 | 245.9755 | 5,507 |
| chr21 | 180.0556 | 3,009 |
| chr22 | 146.0398 | 5,460 |
| chrX | 632.3636 | 5,503 |
| chrY | 112.1640 | 1,277 |

## Interpretation

The result validates whole-genome sharded execution readiness for the hg38
primary chromosomes on the local 2-GPU machine:

```text
manifest-backed execution: exercised
CPU affinity: exercised
workers_per_gpu option: exercised by the 6-worker run
deterministic merge: clean across 4 and 6 workers
failed shards: none
```

The run should not be read as a full scheduler policy. The 4-worker row was
slightly faster than the 6-worker row in this environment, while previous
smaller 8-contig runs favored 6 workers. That means `workers_per_gpu=3` remains
a local candidate, not a default. Broader repeated full-genome runs would be
needed before making a recommendation.

Runtime telemetry also showed a persistent unrelated GPU compute process during
the run. The digest result is unaffected, but the wall-clock comparison should
be treated as local characterization rather than a clean benchmark.

## Decision

```text
validated:
  hg38 primary chromosomes can run as 24 contig-level shards
  4-worker and 6-worker merged digests match
  manifest-backed execution completes with no failed shards
  CPU affinity and GPU assignment are recorded in manifests

not claimed:
  single whole-target full-genome digest equality
  4-GPU scaling
  default workers_per_gpu policy
  alt/random/unplaced hg38 contig coverage
  chunking / overlap safety
```

Next useful step is either a repeated hg38 primary run under a quieter GPU
environment or a broader full-genome workload with additional RNA inputs. Do
not start chunking unless contig-level stragglers become the limiting factor.
