# Fasim Shard Coalescing Characterization

This note characterizes whether grouping many tiny target FASTA records into
fewer worker shards can reduce sharded-runner overhead while preserving exact
merged output.

## Scope

This is a docs/script/result checkpoint only:

- No Fasim C++ runtime code is changed.
- No output, scoring, threshold, endpoint, CIGAR, traceback, merge semantics,
  chunking, overlap, scheduler default, GPU policy, or in-process multi-GPU
  behavior is changed.
- No default grouping policy is added.
- The helper script creates grouped shard FASTAs for characterization only.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Why This Matters

The broader current-base validation found that MEG3 full has 532 tiny target
records. Running one worker shard per target record was digest-clean and
fallback-free, but process/scheduler/small-shard overhead dominated:

```text
MEG3 full group_size=1 workers=4 wall ~= 101.8s
single whole-input validation wall ~= 28.0s
```

That is a workload-shaping problem, not evidence for restarting GPU score,
endpoint, CIGAR, traceback, or full aligner GPU work.

## Helper

`scripts/benchmark_fasim_shard_coalescing_characterization.py`:

- reads the target FASTA records;
- writes grouped shard FASTAs at fixed group sizes;
- preserves every original FASTA header and sequence in grouped shards;
- runs each grouped shard as one Fasim subprocess;
- deterministically canonicalizes, exact-deduplicates, and merges outputs with
  the same helper functions used by `scripts/fasim_sharded_runner.py`;
- compares every grouped result against a single whole-input reference digest;
- reports worker/shard timing, fallback counters, preAlign CUDA tasks/batches,
  profile-cache hit rate, extend/output seconds, and imbalance ratio.

It intentionally does not add a runtime option. A production runner option would
need a separate default-off PR.

## Runtime

The characterized runtime is the current-base recommended local candidate:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_VERBOSE=0
```

The sharded run used process-level GPU assignment with one visible GPU per
worker slot:

```text
--gpu-ids 0,1
--auto-cpu-core-ranges
--cpu-pool 0-19
--cpu-cores-per-worker 3
```

## Command

MEG3 full:

```bash
timeout 3600s python3 scripts/benchmark_fasim_shard_coalescing_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_shard_coalescing_meg3_full \
  --output-mode lite \
  --group-sizes 1,4,8,16,32 \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MEG3_full:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0
```

## Results

Input:

```text
target records: 532
target bases: 1,316,004
single whole-input reference: 28.002s
merged records: 4,914
duplicate removed: 1
```

All rows were digest-clean against the single whole-input reference, and every
row kept `preAlign CUDA fallbacks = 0`.

| group size | grouped shards | workers | wall s | speedup vs group 1 | speedup vs single whole | digest | fallbacks | imbalance | preAlign tasks | preAlign batches | profile cache hit rate |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 532 | 1 | 149.779 | 1.00x | 0.19x | clean | 0 | 1.00 | 25,536 | 532 | 99.6730% |
| 1 | 532 | 2 | 122.145 | 1.00x | 0.23x | clean | 0 | 1.00 | 25,536 | 532 | 99.6743% |
| 1 | 532 | 4 | 101.847 | 1.00x | 0.27x | clean | 0 | 1.00 | 25,536 | 532 | 99.6820% |
| 4 | 133 | 1 | 57.513 | 2.60x | 0.49x | clean | 0 | 1.00 | 25,536 | 524 | 99.7016% |
| 4 | 133 | 2 | 40.061 | 3.05x | 0.70x | clean | 0 | 1.01 | 25,536 | 524 | 99.7017% |
| 4 | 133 | 4 | 30.319 | 3.36x | 0.92x | clean | 0 | 1.01 | 25,536 | 524 | 99.7057% |
| 8 | 67 | 1 | 41.963 | 3.57x | 0.67x | clean | 0 | 1.00 | 25,536 | 524 | 99.7067% |
| 8 | 67 | 2 | 26.350 | 4.64x | 1.06x | clean | 0 | 1.01 | 25,536 | 524 | 99.7068% |
| 8 | 67 | 4 | 18.391 | 5.54x | 1.52x | clean | 0 | 1.02 | 25,536 | 524 | 99.7093% |
| 16 | 34 | 1 | 33.716 | 4.44x | 0.83x | clean | 0 | 1.00 | 25,536 | 523 | 99.7138% |
| 16 | 34 | 2 | 19.405 | 6.29x | 1.44x | clean | 0 | 1.01 | 25,536 | 523 | 99.7098% |
| 16 | 34 | 4 | 11.450 | 8.90x | 2.45x | clean | 0 | 1.11 | 25,536 | 523 | 99.7123% |
| 32 | 17 | 1 | 29.150 | 5.14x | 0.96x | clean | 0 | 1.00 | 25,536 | 522 | 99.7123% |
| 32 | 17 | 2 | 16.244 | 7.52x | 1.72x | clean | 0 | 1.04 | 25,536 | 522 | 99.7094% |
| 32 | 17 | 4 | 10.043 | 10.14x | 2.79x | clean | 0 | 1.15 | 25,536 | 522 | 99.7137% |

Summary:

```text
digest clean: 15/15
preAlign CUDA fallbacks: 0/15 rows
merged records stable: 4,914
duplicate removed stable: 1
profile cache active: 15/15
profile cache hit rate: 99.67-99.71%
best row: group_size=32 workers=4, 10.043s
```

## Interpretation

Strong signals:

```text
grouped shards preserve the exact merged digest
record identity is preserved by keeping original FASTA headers in grouped shards
preAlign CUDA fallback count does not increase
profile cache remains active and highly reused
MEG3 tiny-region wall time improves materially as shard count drops
```

The result supports a default-off grouping option for tiny-region workloads. It
does not imply that all workloads should be grouped by default.

Important boundary:

```text
group_size=32 workers=4 is fastest in this matrix, but imbalance rises to 1.15.
Larger groups may over-coalesce and leave workers idle on less uniform inputs.
```

## Runner Option Requirements

A follow-up runtime option such as `--group-target-records N` should remain
default-off and must include:

```text
grouping mode and group size in run_config_digest
group member list in the shard plan
input record digests or grouped shard digests in resume validation
original FASTA headers preserved in grouped shard files
canonical sort and exact de-dup merge unchanged
per-worker and per-shard timing reported for imbalance checks
```

Do not implement grouping by renaming targets to synthetic group names in Fasim
input. The grouped FASTA file may have a synthetic file name, but the records
inside it must keep their original headers.

## Decision

This is a strong go for a default-off runner option:

```text
next PR: add --group-target-records N to scripts/fasim_sharded_runner.py
default: disabled
first recommended candidate for MEG3-like tiny-region workloads: 16 or 32
```

Fallback reason taxonomy should stay separate. MEG3 has fallback=0 here, while
NEAT1/MALAT1 fallback-heavy behavior should be characterized in a follow-up
taxonomy PR instead of being folded into shard coalescing.
