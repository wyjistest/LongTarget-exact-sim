# Fasim hg38 Primary Sharded Straggler Analysis

This note analyzes completed sharded runner telemetry from the hg38 primary
chromosome matrix. It explains the observed 4-worker versus 6-worker behavior
using actual per-shard and per-worker timings. This is a post-run analysis only:
it does not run Fasim, change scheduling policy, or validate single whole-target
full-genome digest equality.

## Scope

Validated here:

- completed hg38 primary chromosome sharded reports from the 4-worker and
  6-worker runs
- per-worker actual seconds, assigned shards, GPU ids, and CPU ranges
- per-shard seconds, records, digests, and length-derived work estimates
- cross-run merged digest and per-shard digest consistency
- observed-time greedy reassignment simulation for 1/2/3/4/5/6/8 workers

Out of scope:

- new Fasim execution
- single whole-target full-genome digest equality
- 4-GPU scaling
- default scheduler policy changes
- chunk splitting or overlap
- in-process multi-GPU
- Fasim C++ runtime or output semantic changes

## Inputs

```text
workload: hg38_primary_chromosomes_H19
source result note: docs/fasim_sharded_worker_hg38_primary_genome_matrix.md
4-worker report: .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/report.json
6-worker report: .tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/report.json
analysis output: .tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_straggler_analysis.json
```

The input reports came from the same manifest-backed, CPU-affinity-enabled,
explicit-GPU sharded execution stack:

```text
GPUs: 0,1
CPU pool: 0-17
CPU cores per worker: 3
output mode: lite
legacy recorded env labels:
  FASIM_TRANSFERSTRING_TABLE=1
  FASIM_GPU_DP_COLUMN_AUTO=1
  FASIM_SSW_PROFILE_CACHE=1
  FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Reconciliation note: these are historical run-config labels. The current
repo-local Fasim binary now reads `FASIM_TRANSFERSTRING_TABLE`,
`FASIM_GPU_DP_COLUMN_AUTO`, `FASIM_SSW_PROFILE_CACHE`, and
`FASIM_EXACT_COLUMN_EXTEND_BATCH` as default-off opt-ins, but this straggler
analysis was not rerun after that integration. Treat the timings as historical
telemetry, not fresh evidence for the reconciled binary.

## Analyzer Command

```bash
python3 scripts/analyze_fasim_sharded_run_stragglers.py \
  --workload-name hg38_primary_chromosomes_H19 \
  --run workers_4=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/report.json \
  --run workers_6=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/report.json \
  --simulate-workers 1,2,3,4,5,6,8 \
  --output .tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_straggler_analysis.json
```

The analyzer reads completed reports only. The observed-time simulation uses
completed per-shard durations as fixed costs and greedily assigns the largest
observed durations first. It does not model GPU sharing, CPU contention, cache
effects, or I/O overlap, so it is a balance diagnostic rather than a runtime
prediction.

## Digest Consistency

```text
merged_digest_consistent: true
per_shard_digest_consistent: true
merged_digest:
  8dc08e4174c8174b816bd3f003b1c55314765a5df744940305bb6876880b7856
best_observed_run: workers_4
```

Both completed runs produced the same merged digest and matching per-shard
digests. This supports deterministic merge consistency across these worker
counts, but it is not a single whole-target full-genome digest audit.

## Run Summary

| run | workers | GPU mode | wall seconds | total shard seconds | ideal makespan | scheduler efficiency | idle estimate | straggler worker |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| workers_4 | 4 | shared | 2,898.2267 | 11,340.0046 | 2,835.0012 | 0.9782 | 0.0218 | 0 |
| workers_6 | 6 | shared | 2,949.7175 | 15,617.7752 | 2,602.9625 | 0.8824 | 0.1176 | 5 |

The 4-worker run was faster even though the plan-only length balance for 4 and
6 workers looked acceptable. The actual telemetry shows two signals:

1. The 6-worker run had lower scheduler efficiency: about 88.2% versus 97.8%.
2. The 6-worker run accumulated substantially more total shard seconds than the
   4-worker run, which points to resource contention or oversubscription cost,
   not only contig assignment imbalance.

## Per-Worker Timing

| run | worker | GPU | CPU range | actual seconds | sum shard seconds | records | shards |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| workers_4 | 0 | 0 | 0-2 | 2,898.2267 | 2,896.8331 | 47,862 | chr1, chr10, chr15, chr17, chr21, chrX |
| workers_4 | 1 | 1 | 3-5 | 2,863.7736 | 2,862.3180 | 52,430 | chr2, chr7, chr11, chr14, chr19, chr20 |
| workers_4 | 2 | 0 | 6-8 | 2,747.4075 | 2,746.3079 | 38,066 | chr3, chr6, chr8, chr13, chr16, chrY |
| workers_4 | 3 | 1 | 9-11 | 2,835.8453 | 2,834.5456 | 40,588 | chr4, chr5, chr9, chr12, chr18, chr22 |
| workers_6 | 0 | 0 | 0-2 | 2,265.8391 | 2,264.3365 | 39,186 | chr1, chr10, chr17, chr22 |
| workers_6 | 1 | 1 | 3-5 | 2,610.5911 | 2,609.2340 | 34,027 | chr2, chr11, chr16, chr21 |
| workers_6 | 2 | 0 | 6-8 | 2,887.2691 | 2,886.1362 | 27,882 | chr3, chr9, chr14, chr20 |
| workers_6 | 3 | 1 | 9-11 | 2,213.7786 | 2,212.5179 | 27,385 | chr4, chr8, chr13, chr19 |
| workers_6 | 4 | 0 | 12-14 | 2,698.5156 | 2,697.2561 | 23,406 | chr5, chr15, chr18, chrX |
| workers_6 | 5 | 1 | 15-17 | 2,949.7175 | 2,948.2945 | 27,060 | chr6, chr7, chr12, chrY |

The 6-worker straggler was worker 5 with chr6, chr7, chr12, and chrY. Its
assigned length was close to other 6-worker assignments, so the long tail is not
explained by length balance alone.

## Per-Shard Timing Signals

Top 4-worker shard times:

| contig | seconds | length | records | worker |
| --- | ---: | ---: | ---: | ---: |
| chr2 | 854.8982 | 242,193,529 | 13,697 | 1 |
| chr1 | 848.4321 | 248,956,422 | 15,431 | 0 |
| chr5 | 697.7316 | 181,538,259 | 8,194 | 3 |
| chr3 | 684.9949 | 198,295,559 | 8,453 | 2 |
| chr6 | 658.3969 | 170,805,979 | 8,142 | 2 |
| chr4 | 650.3795 | 190,214,555 | 6,957 | 3 |
| chrX | 632.3636 | 156,040,895 | 5,503 | 0 |
| chr7 | 610.4762 | 159,345,973 | 10,241 | 1 |
| chr8 | 554.8234 | 145,138,636 | 8,088 | 2 |
| chr10 | 543.9636 | 133,797,422 | 9,236 | 0 |

Top 6-worker shard times:

| contig | seconds | length | records | worker |
| --- | ---: | ---: | ---: | ---: |
| chr2 | 1,384.7299 | 242,193,529 | 13,697 | 1 |
| chr3 | 1,213.2571 | 198,295,559 | 8,453 | 2 |
| chr1 | 1,104.6514 | 248,956,422 | 15,431 | 0 |
| chr5 | 1,073.3310 | 181,538,259 | 8,194 | 4 |
| chr6 | 1,043.6235 | 170,805,979 | 8,142 | 5 |
| chr7 | 984.2144 | 159,345,973 | 10,241 | 5 |
| chr4 | 889.4130 | 190,214,555 | 6,957 | 3 |
| chr12 | 803.1983 | 133,275,309 | 7,400 | 5 |
| chr9 | 753.9633 | 138,394,717 | 8,492 | 2 |
| chr11 | 708.3744 | 135,086,622 | 9,347 | 1 |

Estimated length still correlates strongly with shard runtime:

```text
workers_4 estimated_length_vs_seconds correlation: 0.9779
workers_6 estimated_length_vs_seconds correlation: 0.9507
```

Record count is weaker:

```text
workers_4 records_vs_seconds correlation: 0.7604
workers_6 records_vs_seconds correlation: 0.7170
```

This suggests length is a useful first-order assignment cost for whole-primary
contig shards, but 6-worker oversubscription changes absolute shard durations.

## Observed-Time Greedy Simulation

Using the 4-worker observed shard durations as fixed costs:

| simulated workers | predicted makespan | efficiency | idle estimate | straggler shards |
| ---: | ---: | ---: | ---: | --- |
| 1 | 11,340.0046 | 1.0000 | 0.0000 | all shards |
| 2 | 5,681.5734 | 0.9980 | 0.0020 | chr2, chr3, chr6, chr7, chr8, chr12, chr13, chr14, chr18, chr15, chr21, chr22 |
| 3 | 3,799.4853 | 0.9949 | 0.0051 | chr5, chr3, chrX, chr10, chr9, chr16, chr15, chrY |
| 4 | 2,877.7393 | 0.9851 | 0.0149 | chr1, chrX, chr11, chr14, chr19, chr20 |
| 5 | 2,347.4761 | 0.9661 | 0.0339 | chr5, chr7, chr12, chr19, chr20 |
| 6 | 1,968.1387 | 0.9603 | 0.0397 | chr5, chr10, chr13, chr15 |
| 8 | 1,496.1935 | 0.9474 | 0.0526 | chr7, chr8, chr15 |

The simulation says the contig set has enough shards to balance beyond 4
workers if shard durations stayed fixed. The real 6-worker run was slower than
4 workers because shard durations did not stay fixed under 6-worker / 2-GPU
oversubscription.

Using the 6-worker observed shard durations as fixed costs gives the same
qualitative balance result: more workers can reduce the simulated makespan, but
the absolute shard costs are inflated under the 6-worker run.

## Interpretation

The next bottleneck is not an obvious single-contig straggler. For hg38 primary
chromosomes on this local 2-GPU machine, the current evidence points to
workload-dependent worker density:

```text
rheMac10 top8:
  6 workers / 2 GPUs was the stable local winner.

hg38 primary chromosomes:
  4 workers / 2 GPUs was slightly faster than 6 workers.
```

The hg38 primary 6-worker run uses three workers per GPU and 18 CPU cores. That
configuration can expose GPU sharing, CPU contention, cache pressure, memory
bandwidth pressure, or I/O/output overhead. This PR does not isolate those
effects; it only shows that the 6-worker slowdown is not explained by a severe
plan-only contig imbalance.

## Decision

For hg38 primary chromosomes on this local 2-GPU machine:

```text
current candidate:
  4 workers / 2 GPUs

still manual:
  worker density remains workload-dependent

not recommended:
  default workers_per_gpu=3
```

Recommended next step:

```text
run a focused hg38 primary density follow-up:
  3 workers / 2 GPUs
  4 workers / 2 GPUs
  5 workers / 2 GPUs
  6 workers / 2 GPUs

keep:
  manifest/resume
  CPU affinity
  digest consistency gate
```

Do not start chunking from this evidence alone. Chunking should wait for a case
where contig-level sharding is clearly limited by one or a few dominant
chromosomes after resource contention is controlled.

## Hygiene

This PR is a docs/script analysis checkpoint. It does not modify Fasim C++
runtime files, output semantics, scoring, thresholds, non-overlap behavior,
chunking, overlap, in-process multi-GPU behavior, or default scheduler policy.
