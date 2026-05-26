# Fasim Current-Base Aligner Internal Real Workload Characterization

This note applies the current-base `aligner.Align()` telemetry from #148 to
larger workloads. It is a docs/result checkpoint only: no Fasim runtime
behavior, scoring, thresholds, output, scheduler policy, GPU policy, sharded
merge semantics, chunking, or in-process multi-GPU behavior are changed.

## Scope

The current clean-base Fasim GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension
  -> CPU aligner.Align()
  -> output
```

This characterization uses only active current-base envs:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=4 or 6
```

It does not use or claim historical final speed-stack envs unless they are
separately integrated into this base.

#147 showed that real-workload CPU extension is dominated by `aligner.Align()`.
#148 split `aligner.Align()` into profile setup, SSW forward score/end,
reverse-start recovery, traceback/CIGAR, conversion, and cleanup. The question
for this run is narrow:

```text
Inside current-base aligner.Align(), which substage is the dominant cost on
real workloads?
```

## Host and Workloads

Host:

```text
CPU: 20 logical CPUs, Intel Core i9-10900X
GPU: 2 x NVIDIA GeForce RTX 4090
CPU pool: 0-19
CPU cores per worker: 3
GPU ids: 0,1
```

Workloads:

```text
rheMac10_nonchrom_top8_H19:
  target: .tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa
  contigs: 8
  bases: 7,181,742
  RNA: H19.fa
  output mode: lite

hg38_chr21_chr22_H19:
  target: .tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa
  contigs: 2
  bases: 97,528,451
  RNA: H19.fa
  output mode: lite
```

The hg38 chr21+chr22 workload has only two contigs, so worker-density
comparisons with 4 or 6 workers include idle workers by design. Its telemetry is
still useful for aligner-internal decomposition, but it is not a fair density
benchmark for worker counts above the contig count.

## Command Shape

All runs used single visible GPU assignment per worker through the sharded
runner and explicitly removed inherited `FASIM_CUDA_DEVICES`:

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target ${TARGET_FASTA} \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_aligner_internal_real_workload/runs/${RUN_ID} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_aligner_internal_real_workload/runs/${RUN_ID}/run_manifest.json \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=${EXTEND_THREADS}
```

## Summary

All rows were digest clean against single-process validation and had zero
preAlign CUDA fallbacks.

Seconds are sharded telemetry sums across workers and extension threads, so
they can exceed wall time.

| workload | extend threads | workers | wall s | single s | records | preAlign total s | extend s | align s | align / extend | align calls | align cells | fallbacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 4 | 2.936 | 6.364 | 926 | 0.295 | 10.120 | 9.993 | 98.75% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 4 | 6 | 2.974 | 6.422 | 926 | 0.223 | 11.030 | 10.922 | 99.02% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 6 | 4 | 2.915 | 5.906 | 926 | 0.196 | 15.066 | 14.893 | 98.85% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 6 | 6 | 2.799 | 5.852 | 926 | 0.228 | 18.052 | 17.721 | 98.17% | 147,270 | 28,338,793,284 | 0 |
| hg38 chr21+chr22 | 4 | 4 | 46.119 | 73.556 | 7,274 | 1.409 | 88.942 | 87.720 | 98.63% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 4 | 6 | 42.946 | 73.683 | 7,274 | 1.410 | 88.726 | 87.464 | 98.58% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 6 | 4 | 44.274 | 69.713 | 7,274 | 1.411 | 132.711 | 130.627 | 98.43% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 6 | 6 | 42.274 | 69.342 | 7,274 | 1.409 | 133.652 | 131.669 | 98.52% | 1,420,427 | 271,509,822,692 | 0 |

The #147 conclusion holds with the #148 split enabled: measured CPU extension
is still dominated by `aligner.Align()`, at roughly 98.2-99.0% of extension
time in these rows.

## Aligner Internal Split

The table below reports the sharded sums inside `aligner.Align()`. `profile /
align` uses `fasim_align_profile_seconds / fasim_extend_align_seconds`.
`SSW / align` uses `fasim_align_ssw_total_seconds /
fasim_extend_align_seconds`. The forward, reverse, and traceback ratios are
relative to `fasim_align_ssw_total_seconds`.

| workload | extend threads | workers | profile / align | SSW / align | forward / SSW | reverse / SSW | traceback / SSW |
|---|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 4 | 40.61% | 54.84% | 72.75% | 19.88% | 6.69% |
| rheMac10 top8 | 4 | 6 | 42.22% | 53.41% | 71.11% | 19.12% | 8.03% |
| rheMac10 top8 | 6 | 4 | 42.53% | 53.37% | 69.96% | 21.55% | 7.21% |
| rheMac10 top8 | 6 | 6 | 41.94% | 54.17% | 73.33% | 19.92% | 6.36% |
| hg38 chr21+chr22 | 4 | 4 | 42.67% | 52.92% | 71.85% | 20.56% | 6.54% |
| hg38 chr21+chr22 | 4 | 6 | 41.29% | 54.17% | 71.44% | 20.76% | 6.82% |
| hg38 chr21+chr22 | 6 | 4 | 41.26% | 54.19% | 71.88% | 20.40% | 6.71% |
| hg38 chr21+chr22 | 6 | 6 | 42.43% | 53.48% | 72.29% | 20.32% | 6.45% |

The important result is that `aligner.Align()` is not a single score-only
bucket in this current base:

```text
profile setup:      about 41-43% of align outer time
SSW total:          about 53-55% of align outer time
forward score/end:  about 70-73% of SSW time
reverse start:      about 19-22% of SSW time
traceback/CIGAR:    about 6-8% of SSW time
```

That means a future score-only GPU shadow can target a real large substage, but
it would not cover the full alignment cost by itself. SSW profile/query reuse
is a parallel CPU-side candidate because profile setup is nearly as large as
the SSW total bucket.

## Per-Worker Notes

The rheMac10 top8 workload has enough contigs to exercise all workers. For the
fastest local row in this run:

```text
rheMac10_nonchrom_top8_H19
FASIM_EXTEND_THREADS=6
workers=6
wall=2.799s

worker 0: wall=2.513s records=68  align/extend=98.02% profile/align=50.56% SSW/align=46.07%
worker 1: wall=2.369s records=241 align/extend=98.82% profile/align=40.54% SSW/align=56.00%
worker 2: wall=2.212s records=110 align/extend=98.48% profile/align=35.23% SSW/align=60.95%
worker 3: wall=1.645s records=150 align/extend=99.45% profile/align=49.45% SSW/align=44.64%
worker 4: wall=2.738s records=211 align/extend=96.97% profile/align=36.68% SSW/align=59.25%
worker 5: wall=2.799s records=146 align/extend=97.79% profile/align=42.25% SSW/align=54.22%
```

The hg38 chr21+chr22 workload has two non-empty shards. Extra workers are idle:

```text
hg38_chr21_chr22_H19
FASIM_EXTEND_THREADS=4
workers=4
wall=46.119s

worker 0: wall=46.119s records=4725 align/extend=98.71% profile/align=43.37% SSW/align=52.23%
worker 1: wall=41.109s records=2549 align/extend=98.54% profile/align=41.95% SSW/align=53.62%
worker 2: idle
worker 3: idle
```

The idle-worker behavior is expected for contig-level sharding on a two-contig
target. It does not weaken the phase conclusion because the two active workers
show the same aligner-internal split as the 8-contig rheMac10 workload.

## Interpretation

The real workload data supports two conclusions:

```text
1. CPU extension is still dominated by aligner.Align().
2. Inside aligner.Align(), the largest current buckets are profile setup and
   SSW forward score/end, not traceback/CIGAR.
```

preAlign CUDA remains short compared with extension/alignment work:

```text
rheMac10 top8 preAlign sharded sum:       about 0.20-0.30s
hg38 chr21+chr22 preAlign sharded sum:    about 1.41s
```

Low average GPU utilization is still expected for this current base because the
active GPU path is a short preAlign CUDA burst while the measured real-workload
CPU time is in alignment.

## Decision

- A future GPU-focused experiment should not target full extension, full CIGAR,
  or output first.
- The strongest GPU candidate is a shadow-only forward score/end probe, because
  forward score/end is roughly 70-73% of SSW time.
- A score-only GPU shadow is not enough to cover all alignment cost. It must
  account for buffer build, H2D, kernel, D2H, and CPU profile/setup cost.
- Profile setup is large enough to justify a separate current-base profile or
  query reuse investigation before or alongside GPU score shadowing.
- Reverse-start recovery is a smaller but non-trivial SSW substage. Any endpoint
  experiment needs a separate tie-policy and false-reject gate.
- Traceback/CIGAR is not the measured dominant substage here. Do not use this
  data to justify GPU CIGAR or GPU full traceback as the first optimization.

Any future score-only GPU or Accelign-style experiment must remain diagnostic
first:

```text
CPU output remains authoritative
GPU score output cannot reject candidates
digest must remain unchanged
score mismatches and false rejects must be zero
buffer build, H2D, kernel, and D2H seconds must be reported separately
```

Do not use this result to justify in-process multi-GPU, chunking/overlap,
historical final speed-stack claims, or output-changing GPU paths.
