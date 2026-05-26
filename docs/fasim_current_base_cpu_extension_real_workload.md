# Fasim Current-Base CPU Extension Real Workload Characterization

This note applies the current-base CPU extension telemetry from #146 to larger
workloads. It is a docs/result checkpoint only: no Fasim runtime behavior,
scoring, thresholds, output, scheduler policy, GPU policy, or sharded merge
semantics are changed.

## Scope

The current clean-base Fasim GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension / aligner.Align()
  -> output
```

This characterization uses only active current-base envs. It does not use or
claim historical final speed-stack envs unless they are separately integrated
into this base.

The question for this run is narrow:

```text
On real workloads, is current-base CPU extension dominated by aligner.Align(),
or by conversion / sort-unique / output / orchestration?
```

The answer decides the next GPU investigation. If `aligner.Align()` dominates,
the next step is to decompose aligner internals or build a score-only shadow. It
is still not evidence for GPU CIGAR, GPU traceback, direct Accelign authority,
single-process multi-GPU, or output-changing GPU paths.

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
still useful for extension decomposition, but it is not a fair density benchmark
for worker counts above the contig count.

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
  --work-dir .tmp/fasim_current_base_extension_real_workload/runs/${RUN_ID} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_extension_real_workload/runs/${RUN_ID}/run_manifest.json \
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
| rheMac10 top8 | 4 | 4 | 2.967 | 6.446 | 926 | 0.273 | 9.996 | 9.842 | 98.46% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 4 | 6 | 2.880 | 6.549 | 926 | 0.225 | 10.966 | 10.842 | 98.87% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 6 | 4 | 2.851 | 5.790 | 926 | 0.212 | 14.717 | 14.471 | 98.33% | 147,270 | 28,338,793,284 | 0 |
| rheMac10 top8 | 6 | 6 | 2.671 | 5.815 | 926 | 0.197 | 16.602 | 16.361 | 98.55% | 147,270 | 28,338,793,284 | 0 |
| hg38 chr21+chr22 | 4 | 4 | 41.814 | 76.270 | 7,274 | 1.409 | 88.717 | 87.372 | 98.48% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 4 | 6 | 42.659 | 77.872 | 7,274 | 1.409 | 88.636 | 87.311 | 98.51% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 6 | 4 | 42.980 | 70.523 | 7,274 | 1.411 | 132.867 | 130.908 | 98.53% | 1,420,427 | 271,509,822,692 | 0 |
| hg38 chr21+chr22 | 6 | 6 | 43.444 | 70.178 | 7,274 | 1.411 | 133.363 | 131.620 | 98.69% | 1,420,427 | 271,509,822,692 | 0 |

The dominant result is stable across both workloads: `aligner.Align()` accounts
for roughly 98.3-98.9% of measured CPU extension time. Conversion, sort/unique,
and output are small in these runs.

## Per-Worker Notes

The rheMac10 top8 workload has enough contigs to exercise all workers. For the
fastest row:

```text
rheMac10_nonchrom_top8_H19
FASIM_EXTEND_THREADS=6
workers=6
wall=2.671s

worker wall seconds:   [2.604, 2.555, 1.786, 1.688, 2.671, 2.344]
worker records:        [68, 241, 110, 150, 211, 146]
worker extend seconds: [2.905, 3.610, 2.241, 1.937, 2.996, 2.914]
worker align seconds:  [2.870, 3.566, 2.219, 1.899, 2.913, 2.895]
worker align ratios:   [98.79%, 98.80%, 99.00%, 98.02%, 97.23%, 99.37%]
```

The hg38 chr21+chr22 workload has two non-empty shards. Extra workers are idle:

```text
hg38_chr21_chr22_H19
FASIM_EXTEND_THREADS=4
workers=4
wall=41.814s

worker 0: wall=41.814s records=4725 extend=44.614s align=43.934s ratio=98.48%
worker 1: wall=41.275s records=2549 extend=44.104s align=43.438s ratio=98.49%
worker 2: idle
worker 3: idle
```

The idle-worker behavior is expected for contig-level sharding on a two-contig
target. It does not weaken the phase conclusion because the two active workers
show the same extension split as the 8-contig rheMac10 workload.

## Interpretation

The real workload data supports the smoke signal from #146:

```text
CPU extension is dominated by aligner.Align().
preAlign CUDA remains short compared with extension work.
conversion / sort-unique / output are not the measured bottleneck here.
```

For rheMac10 top8, `FASIM_EXTEND_THREADS=6` with 6 workers remained the fastest
local row. For hg38 chr21+chr22, 4 and 6 workers are effectively two active
contig workers plus idle workers; `FASIM_EXTEND_THREADS=4` produced lower wall
time than `6` in this two-contig workload, while the single-process validation
run was faster with `6`. Treat this as workload-shape dependent, not a default
policy decision.

## Decision

- The next GPU-focused investigation should target the alignment work boundary,
  not conversion, sort/unique, output, or preAlign TOPK/MAX_TASKS.
- Do not directly replace the extension path with Accelign or another GPU
  aligner. First decompose `aligner.Align()` into score-only DP, endpoint, and
  traceback/CIGAR work, or add a shadow-only score probe if that boundary is
  cleanly exposed.
- Any score-only GPU probe must keep CPU output authoritative and report score
  mismatches, false rejects, buffer-build time, H2D, kernel, and D2H separately.
- Current-base low average GPU utilization is still expected: the active GPU
  path is short preAlign CUDA, while the measured real-workload CPU extension
  work is dominated by `aligner.Align()`.
- Do not use this result to justify single-process multi-GPU, GPU CIGAR, GPU
  full traceback, chunking/overlap, or historical final speed-stack claims.
