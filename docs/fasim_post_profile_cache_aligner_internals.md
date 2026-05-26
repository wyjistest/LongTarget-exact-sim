# Fasim Post-Profile-Cache Aligner Internals

This note characterizes the remaining current-base `aligner.Align()` cost after
enabling the default-off profile cache opt-in:

```text
FASIM_ALIGN_PROFILE_CACHE=1
```

It is a docs/script/result checkpoint only. It does not add optimization logic,
GPU kernels, Accelign integration, chunking, overlap, scheduler changes,
output changes, scoring changes, threshold changes, merge changes, or
in-process multi-GPU behavior.

## Goal

#153 showed that `FASIM_ALIGN_PROFILE_CACHE=1` is a stable current-base opt-in
candidate, improving tested same-query multi-target workloads by about 11-14%
wall time while keeping digest and mismatch/fallback counters clean.

After that cache removes repeated `ssw_init()` profile setup from the real path,
the next question is:

```text
What is the largest remaining aligner.Align() substage?
```

This determines whether a later score-only GPU shadow is worth testing.

## Command

The matrix was run on the latest current base after #154:

```bash
timeout 2400s python3 scripts/benchmark_fasim_post_profile_cache_aligner_internals.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_post_profile_cache_aligner_internals \
  --workload rheMac10_nonchrom_top8_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --workload hg38_chr21_chr22_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa:H19.fa:1 \
  --workers 4,6 \
  --gpu-ids 0,1 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --extend-threads 6 \
  --force
```

Each worker process used one visible GPU via the sharded runner. The parent
environment removed inherited `FASIM_CUDA_DEVICES`.

Active env:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
```

## Results

Seconds below are sharded telemetry sums across workers/shards, not wall time.
They can exceed wall time because workers and extension threads run
concurrently.

| workload | workers | wall s | records | align s | profile s | SSW s | forward s | reverse s | traceback s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 2.729 | 926 | 10.543 | 0.079 | 7.839 | 5.605 | 1.585 | 0.548 |
| rheMac10 top8 | 6 | 2.664 | 926 | 11.140 | 0.051 | 8.416 | 5.962 | 1.750 | 0.638 |
| hg38 chr21+chr22 | 4 | 39.835 | 7274 | 94.660 | 0.007 | 71.740 | 52.048 | 14.457 | 4.290 |
| hg38 chr21+chr22 | 6 | 41.985 | 7274 | 94.751 | 0.033 | 70.958 | 50.322 | 15.188 | 4.771 |

Relative split:

| workload | workers | SSW / align | profile / align | forward / SSW | reverse / SSW | traceback / SSW | forward / align |
|---|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 74.35% | 0.75% | 71.51% | 20.22% | 6.99% | 53.16% |
| rheMac10 top8 | 6 | 75.55% | 0.46% | 70.84% | 20.80% | 7.58% | 53.52% |
| hg38 chr21+chr22 | 4 | 75.79% | 0.01% | 72.55% | 20.15% | 5.98% | 54.98% |
| hg38 chr21+chr22 | 6 | 74.89% | 0.03% | 70.92% | 21.40% | 6.72% | 53.11% |

Correctness and safety counters stayed clean:

```text
digest clean: 4/4
preAlign CUDA fallbacks: 0
profile cache active: 4/4
profile cache score mismatches: 0
profile cache endpoint mismatches: 0
profile cache CIGAR mismatches: 0
profile cache digest mismatches: 0
profile cache fallbacks: 0
```

Profile cache hit rates stayed saturated:

```text
rheMac10 top8:
  workers=4 hits/misses/keys: 147197 / 73 / 8
  workers=6 hits/misses/keys: 147199 / 71 / 8

hg38 chr21+chr22:
  workers=4 hits/misses/keys: 1420326 / 101 / 2
  workers=6 hits/misses/keys: 1420325 / 102 / 2
```

## Interpretation

The profile cache changes the aligner cost shape materially. In #149,
profile setup was about 41-43% of align outer time before the real cache. With
`FASIM_ALIGN_PROFILE_CACHE=1`, measured profile setup in the real path drops to:

```text
rheMac10 top8:     about 0.46-0.75% of align
hg38 chr21+chr22: about 0.01-0.03% of align
```

The largest remaining measured bucket is now forward score/end:

```text
forward score/end:
  about 70.9-72.6% of SSW total
  about 53.1-55.0% of align outer time
```

Reverse-start recovery is still material:

```text
reverse start:
  about 20.2-21.4% of SSW total
  about 15.0-16.0% of align outer time
```

Traceback/CIGAR is smaller:

```text
traceback/CIGAR:
  about 6.0-7.6% of SSW total
  about 4.5-5.7% of align outer time
```

For `hg38_chr21_chr22_H19`, `workers=6` remains diagnostic rather than a worker
density benchmark because the workload has only two contigs; extra workers are
idle or oversubscribed around the two real shard workers.

## Decision

This result supports a next PR for a score-only GPU shadow, but not a real GPU
alignment replacement.

The next GPU probe should remain diagnostic:

```text
CPU aligner.Align remains authoritative.
GPU score/end output cannot reject candidates.
Do not use GPU endpoint for final output.
Do not use GPU CIGAR.
Do not change output/digest.
Report buffer build, H2D, kernel, D2H, score mismatches, and false rejects.
```

Do not prioritize GPU CIGAR or GPU traceback from this result. Traceback/CIGAR
is not the dominant remaining measured bucket after the profile cache.

Also do not go back to historical final speed-stack env claims. The current
active GPU path remains `FASIM_ENABLE_PREALIGN_CUDA=1`, with the profile cache
as `FASIM_ALIGN_PROFILE_CACHE=1`.
