# Fasim Current-Base Align Profile Cache Characterization

This note records repeated local A/B runs for the default-off current-base
align profile cache from #152.

## Scope

This is a docs/script/result checkpoint only:

- No new optimization logic is added.
- `FASIM_ALIGN_PROFILE_CACHE` is not enabled by default.
- No output, scoring, threshold, endpoint, CIGAR, traceback, scheduler, GPU
  policy, merge, chunking, or in-process multi-GPU behavior is changed.
- No Accelign or GPU aligner path is added.
- Current clean-base active GPU work remains `FASIM_ENABLE_PREALIGN_CUDA=1`.

The goal is to check whether the single-run #152 signal is stable enough to
call the profile cache a current-base recommended opt-in candidate.

## Command

The repeated matrix was run with:

```bash
timeout 3600s python3 scripts/benchmark_fasim_align_profile_cache_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_align_profile_cache_characterization \
  --workload rheMac10_nonchrom_top8_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --workload hg38_chr21_chr22_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa:H19.fa:1 \
  --workers 4,6 \
  --repeats 3 \
  --gpu-ids 0,1 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --extend-threads 6 \
  --force
```

Each worker process used one visible GPU via the sharded runner. The parent
environment had `FASIM_CUDA_DEVICES` removed.

Common active env:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
```

Modes:

```text
baseline:
  no profile cache env

cache:
  FASIM_ALIGN_PROFILE_CACHE=1

cache_validate:
  FASIM_ALIGN_PROFILE_CACHE=1
  FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1
```

## Median Results

The `wall` value is `max(per_worker.wall_seconds)` from the sharded runner
report. `runner_total_seconds` is preserved in the raw TSV for end-to-end wrapper
cost, but the local worker-density characterization uses the worker critical
path as the main wall metric.

The mismatch/fallback column is:

```text
score / endpoint / CIGAR / digest / fallback
```

| workload | workers | mode | runs | median wall s | delta vs baseline | records | hit rate | validate s | mismatches/fallbacks |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| hg38_chr21_chr22_H19 | 4 | baseline | 3 | 46.350 | +0.00% | 7274 | 0.0000% | 0.000 | 0/0/0/0/0 |
| hg38_chr21_chr22_H19 | 4 | cache | 3 | 39.971 | -13.76% | 7274 | 99.9929% | 0.000 | 0/0/0/0/0 |
| hg38_chr21_chr22_H19 | 4 | cache_validate | 3 | 50.197 | +8.30% | 7274 | 99.9928% | 124.152 | 0/0/0/0/0 |
| hg38_chr21_chr22_H19 | 6 | baseline | 3 | 45.422 | +0.00% | 7274 | 0.0000% | 0.000 | 0/0/0/0/0 |
| hg38_chr21_chr22_H19 | 6 | cache | 3 | 39.789 | -12.40% | 7274 | 99.9928% | 0.000 | 0/0/0/0/0 |
| hg38_chr21_chr22_H19 | 6 | cache_validate | 3 | 50.264 | +10.66% | 7274 | 99.9928% | 124.165 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 4 | baseline | 3 | 2.985 | +0.00% | 926 | 0.0000% | 0.000 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 4 | cache | 3 | 2.655 | -11.05% | 926 | 99.9511% | 0.000 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 4 | cache_validate | 3 | 3.428 | +14.82% | 926 | 99.9511% | 13.874 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 6 | baseline | 3 | 2.920 | +0.00% | 926 | 0.0000% | 0.000 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 6 | cache | 3 | 2.550 | -12.65% | 926 | 99.9552% | 0.000 | 0/0/0/0/0 |
| rheMac10_nonchrom_top8_H19 | 6 | cache_validate | 3 | 3.115 | +6.69% | 926 | 99.9545% | 15.776 | 0/0/0/0/0 |

## Raw Wall Seconds

| workload | workers | mode | run 1 | run 2 | run 3 |
|---|---:|---|---:|---:|---:|
| hg38_chr21_chr22_H19 | 4 | baseline | 46.350 | 44.921 | 46.879 |
| hg38_chr21_chr22_H19 | 4 | cache | 39.971 | 39.693 | 40.149 |
| hg38_chr21_chr22_H19 | 4 | cache_validate | 50.197 | 50.110 | 50.225 |
| hg38_chr21_chr22_H19 | 6 | baseline | 44.150 | 45.422 | 45.724 |
| hg38_chr21_chr22_H19 | 6 | cache | 41.137 | 39.789 | 39.285 |
| hg38_chr21_chr22_H19 | 6 | cache_validate | 51.222 | 50.264 | 50.234 |
| rheMac10_nonchrom_top8_H19 | 4 | baseline | 3.050 | 2.985 | 2.983 |
| rheMac10_nonchrom_top8_H19 | 4 | cache | 2.658 | 2.655 | 2.653 |
| rheMac10_nonchrom_top8_H19 | 4 | cache_validate | 3.267 | 3.507 | 3.428 |
| rheMac10_nonchrom_top8_H19 | 6 | baseline | 2.972 | 2.920 | 2.767 |
| rheMac10_nonchrom_top8_H19 | 6 | cache | 2.512 | 2.550 | 2.691 |
| rheMac10_nonchrom_top8_H19 | 6 | cache_validate | 3.413 | 3.063 | 3.115 |

## Correctness

All 36 raw rows were digest clean against single-process validation:

```text
digest clean: 36/36
preAlign CUDA fallbacks: 0
profile cache score mismatches: 0
profile cache endpoint mismatches: 0
profile cache CIGAR mismatches: 0
profile cache digest mismatches: 0
profile cache fallbacks: 0
```

Validate mode stayed clean in every row but is intentionally slower because it
rebuilds the legacy profile and reruns the legacy alignment side path.

## Interpretation

The repeated medians confirm the #152 single-run signal:

```text
rheMac10 top8:
  workers=4 cache median improvement: 11.05%
  workers=6 cache median improvement: 12.65%

hg38 chr21+chr22:
  workers=4 cache median improvement: 13.76%
  workers=6 cache median improvement: 12.40%
```

Cache hit rates were effectively saturated:

```text
rheMac10 top8:
  workers=4 median hits/misses/keys: 147198 / 72 / 8
  workers=6 median hits/misses/keys: 147204 / 66 / 8

hg38 chr21+chr22:
  workers=4 median hits/misses/keys: 1420326 / 101 / 2
  workers=6 median hits/misses/keys: 1420325 / 102 / 2
```

The cache removes almost all measured profile-build time from the real path.
The exact wall-time gain is smaller than summed saved-seconds telemetry because
that field aggregates per-call/thread estimates and is not a wall-time
predictor.

## Decision

`FASIM_ALIGN_PROFILE_CACHE=1` is a current-base recommended opt-in candidate for
the tested local 2x4090 setup and these same-query multi-target workloads. It
should remain default-off until broader workload and hardware coverage exists.

Recommended current-base opt-in form:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
python3 scripts/fasim_sharded_runner.py \
  --gpu-ids 0,1 \
  --workers 4 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --auto-cpu-core-ranges \
  ...
```

Use:

```bash
FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1
```

only for correctness audit sweeps, not for performance runs.

If further optimization is needed after profile caching, re-measure the remaining
aligner cost. Only if forward score/end still dominates should a separate
score-only GPU shadow be considered.
