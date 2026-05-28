# Fasim Grouped Target-Record Option Characterization

This note characterizes the real sharded-runner option:

```text
--group-target-records N
```

The option was added as a default-off mechanism for tiny-region workloads. It
groups complete target FASTA records into fewer shard FASTAs while preserving
the original FASTA headers and sequences.

## Scope

This is a docs/script/result checkpoint only:

- No Fasim C++ runtime code is changed.
- No default grouping policy is added.
- No output, scoring, threshold, endpoint, CIGAR, traceback, merge semantics,
  scheduler default, GPU policy, chunking, overlap, or in-process multi-GPU
  behavior is changed.
- The runs use the real `scripts/fasim_sharded_runner.py` option, not the
  pre-option helper from the shard-coalescing characterization.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Runtime

The characterized runtime is the current-base local opt-in candidate:

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

`scripts/benchmark_fasim_group_target_records_option.py` runs the real sharded
runner for each workload, group size, and worker count. It writes:

```text
report.json
raw.tsv
```

The summary rows include:

```text
target_record_count
group_target_records
grouped_shard_count
worker_count
wall_seconds
speedup_vs_default_grouping
digest_match
merged_records
duplicate_removed
preAlign CUDA fallbacks
profile_cache_hit_rate
per_worker_seconds
per_shard_seconds
imbalance_ratio
manifest_resume_status
```

## Commands

MEG3 full:

```bash
timeout 3600s python3 scripts/benchmark_fasim_group_target_records_option.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_group_target_records_option_meg3_full \
  --output-mode lite \
  --group-target-records none,8,16,32 \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MEG3_full:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0
```

NEAT1 first64 and MALAT1 first8 used deterministic FASTA prefixes:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=64{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa \
  > .tmp/fasim_group_target_records_option_inputs/NEAT1_DNAseq_first64.fa

awk 'BEGIN{n=0} /^>/{n++} n<=8{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa \
  > .tmp/fasim_group_target_records_option_inputs/MALAT1_DNAseq_first8.fa
```

NEAT1 first64 was run in the combined sampled matrix. That matrix timed out
later while running MALAT1, after all NEAT1 rows had completed. The NEAT1 table
below is from the completed per-run `report.json` files.

MALAT1 first8 was rerun separately to produce a complete top-level summary:

```bash
timeout 900s python3 scripts/benchmark_fasim_group_target_records_option.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_group_target_records_option_malat1_first8 \
  --output-mode lite \
  --group-target-records none,8,16,32 \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MALAT1_first8:.tmp/fasim_group_target_records_option_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0
```

## MEG3 Full

Input:

```text
target records: 532
target bases: 1,316,004
merged records: 4,914
duplicate removed: 1
```

All rows were digest-clean and had `preAlign CUDA fallbacks = 0`.

| group | shards | workers | wall s | speedup vs default | digest | fallbacks | records | duplicate removed | cache hit | imbalance |
|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| default | 532 | 1 | 216.621 | 1.00x | clean | 0 | 4,914 | 1 | 99.6762% | 1.00 |
| default | 532 | 2 | 130.594 | 1.00x | clean | 0 | 4,914 | 1 | 99.6759% | 1.00 |
| default | 532 | 4 | 98.138 | 1.00x | clean | 0 | 4,914 | 1 | 99.6789% | 1.01 |
| 8 | 67 | 1 | 43.724 | 4.95x | clean | 0 | 4,914 | 1 | 99.7085% | 1.00 |
| 8 | 67 | 2 | 26.407 | 4.95x | clean | 0 | 4,914 | 1 | 99.7059% | 1.01 |
| 8 | 67 | 4 | 18.569 | 5.29x | clean | 0 | 4,914 | 1 | 99.7092% | 1.02 |
| 16 | 34 | 1 | 34.136 | 6.35x | clean | 0 | 4,914 | 1 | 99.7116% | 1.00 |
| 16 | 34 | 2 | 19.613 | 6.66x | clean | 0 | 4,914 | 1 | 99.7097% | 1.01 |
| 16 | 34 | 4 | 12.145 | 8.08x | clean | 0 | 4,914 | 1 | 99.7121% | 1.09 |
| 32 | 17 | 1 | 29.128 | 7.44x | clean | 0 | 4,914 | 1 | 99.7144% | 1.00 |
| 32 | 17 | 2 | 16.356 | 7.98x | clean | 0 | 4,914 | 1 | 99.7117% | 1.04 |
| 32 | 17 | 4 | 9.862 | 9.95x | clean | 0 | 4,914 | 1 | 99.7143% | 1.15 |

## NEAT1 First64

Input:

```text
target records: 64
target bases: 179,014
merged records: 2,838
duplicate removed: 0
```

All completed NEAT1 rows were digest-clean. NEAT1 remains fallback-heavy, but
grouping reduces the number of Fasim invocations and therefore reduces one
fallback event per tiny shard to one fallback event per grouped shard.

| group | shards | workers | wall s | speedup vs default | digest | fallbacks | records | duplicate removed | cache hit | imbalance |
|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| default | 64 | 1 | 92.811 | 1.00x | clean | 64 | 2,838 | 0 | 99.9543% | 1.00 |
| default | 64 | 2 | 47.259 | 1.00x | clean | 64 | 2,838 | 0 | 99.9543% | 1.01 |
| default | 64 | 4 | 26.667 | 1.00x | clean | 64 | 2,838 | 0 | 99.9543% | 1.02 |
| 8 | 8 | 1 | 76.522 | 1.21x | clean | 8 | 2,838 | 0 | 99.9943% | 1.00 |
| 8 | 8 | 2 | 39.888 | 1.18x | clean | 8 | 2,838 | 0 | 99.9943% | 1.03 |
| 8 | 8 | 4 | 21.580 | 1.24x | clean | 8 | 2,838 | 0 | 99.9943% | 1.06 |
| 16 | 4 | 1 | 75.323 | 1.23x | clean | 4 | 2,838 | 0 | 99.9971% | 1.00 |
| 16 | 4 | 2 | 38.674 | 1.22x | clean | 4 | 2,838 | 0 | 99.9971% | 1.02 |
| 16 | 4 | 4 | 20.943 | 1.27x | clean | 4 | 2,838 | 0 | 99.9971% | 1.04 |
| 32 | 2 | 1 | 74.909 | 1.24x | clean | 2 | 2,838 | 0 | 99.9986% | 1.00 |
| 32 | 2 | 2 | 38.568 | 1.23x | clean | 2 | 2,838 | 0 | 99.9986% | 1.02 |
| 32 | 2 | 4 | 38.517 | 0.69x | clean | 2 | 2,838 | 0 | 99.9986% | 2.04 |

## MALAT1 First8

Input:

```text
target records: 8
target bases: 166,196
merged records: 796
duplicate removed: 3
```

All rows were digest-clean. This workload shows the over-coalescing boundary:
`group=8/16/32` collapses the whole sample to one shard, which removes fallback
events but also removes multi-worker parallelism.

| group | shards | workers | wall s | speedup vs default | digest | fallbacks | records | duplicate removed | cache hit | imbalance |
|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| default | 8 | 1 | 22.708 | 1.00x | clean | 8 | 796 | 3 | 99.9893% | 1.00 |
| default | 8 | 2 | 11.945 | 1.00x | clean | 8 | 796 | 3 | 99.9893% | 1.04 |
| default | 8 | 4 | 7.700 | 1.00x | clean | 8 | 796 | 3 | 99.9893% | 1.22 |
| 8 | 1 | 1 | 20.942 | 1.08x | clean | 1 | 796 | 3 | 99.9987% | 1.00 |
| 8 | 1 | 2 | 20.929 | 0.57x | clean | 1 | 796 | 3 | 99.9987% | 2.00 |
| 8 | 1 | 4 | 20.907 | 0.37x | clean | 1 | 796 | 3 | 99.9987% | 4.00 |
| 16 | 1 | 1 | 20.923 | 1.09x | clean | 1 | 796 | 3 | 99.9987% | 1.00 |
| 16 | 1 | 2 | 20.945 | 0.57x | clean | 1 | 796 | 3 | 99.9987% | 2.00 |
| 16 | 1 | 4 | 20.925 | 0.37x | clean | 1 | 796 | 3 | 99.9987% | 4.00 |
| 32 | 1 | 1 | 20.897 | 1.09x | clean | 1 | 796 | 3 | 99.9987% | 1.00 |
| 32 | 1 | 2 | 20.899 | 0.57x | clean | 1 | 796 | 3 | 99.9987% | 2.00 |
| 32 | 1 | 4 | 20.903 | 0.37x | clean | 1 | 796 | 3 | 99.9987% | 4.00 |

## Summary

Correctness:

```text
MEG3 full digest clean: 12/12
NEAT1 first64 completed rows digest clean: 12/12
MALAT1 first8 digest clean: 12/12
merged records stable within each workload
duplicate removal stable within each workload
```

Performance:

```text
MEG3 full:
  group=32 workers=4: 98.138s -> 9.862s, 9.95x faster than default grouping
  fallbacks remain 0

NEAT1 first64:
  group=16 workers=4: 26.667s -> 20.943s, 1.27x faster than default grouping
  fallback events drop from 64 to 4 because shard count drops from 64 to 4

MALAT1 first8:
  group=8/16/32 collapses to one shard
  workers=4 gets slower than default grouping because parallelism disappears
```

## Decision

`--group-target-records` should be documented as a recommended default-off
option for tiny-region workloads with many small FASTA records, especially when
default one-record-per-shard overhead dominates.

Initial guidance:

```text
MEG3-like many-record tiny-region workloads:
  try --group-target-records 16 or 32

NEAT1-like sampled tiny-region workloads:
  grouping can help, but avoid group sizes that leave too few shards for the
  selected worker count

MALAT1 first8-like small samples:
  do not over-group; preserving enough shards for worker parallelism matters
```

Keep the option default-off. Do not infer an automatic group-size policy from
this local matrix alone.

Fallback reason taxonomy remains a separate follow-up. Grouping reduces fallback
event count on fallback-heavy sampled workloads by reducing invocation count,
but it does not explain why those records fall back from the preAlign CUDA fast
path.
