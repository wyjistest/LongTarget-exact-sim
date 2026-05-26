# Fasim Current-Base Profile Reuse Real Workload Characterization

This note applies the default-off profile/query reuse shadow telemetry from
`FASIM_ALIGN_PROFILE_REUSE_SHADOW=1` to the same current-base real workloads
used for recent extension and aligner characterization.

It is a docs/result checkpoint only. It does not add a real profile cache and
does not change Fasim runtime behavior, output, scoring, thresholds, endpoint
selection, CIGAR/traceback, sharded scheduling, GPU policy, merge semantics,
chunking, or in-process multi-GPU behavior.

## Scope

The active current-base GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension
  -> CPU aligner.Align()
  -> output
```

This run uses only active current-base envs:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_ALIGN_PROFILE_REUSE_SHADOW=1
FASIM_EXTEND_THREADS=4 or 6
```

It does not use historical final speed-stack envs as performance claims.

The question for this run is narrow:

```text
On real workloads, are SSW profile/query keys reused enough to justify a
future default-off real profile cache probe?
```

The shadow still builds an SSW profile for every `aligner.Align()` call. The
estimated saved seconds are an upper-bound opportunity estimate, not a measured
real-cache speedup.

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

The hg38 chr21+chr22 workload has only two contigs, so worker counts above two
include idle workers. Those rows are useful for telemetry consistency but are
not a worker-density benchmark.

## Command Shape

All runs used process-level GPU sharding. Each worker saw one assigned physical
GPU through `CUDA_VISIBLE_DEVICES`, and inherited `FASIM_CUDA_DEVICES` was
removed by the parent shell and by the sharded runner worker env hygiene.

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target ${TARGET_FASTA} \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_profile_reuse_real_workload/runs/${RUN_ID} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_profile_reuse_real_workload/runs/${RUN_ID}/run_manifest.json \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_ALIGN_PROFILE_REUSE_SHADOW=1 \
  --env FASIM_EXTEND_THREADS=${EXTEND_THREADS}
```

## Summary

All eight rows were digest clean against single-process validation, had
`FASIM_ALIGN_PROFILE_REUSE_SHADOW=1` active, and had zero preAlign CUDA
fallbacks.

Seconds are sharded telemetry sums across Fasim processes and extension
threads, so they can exceed wall time.

| workload | extend threads | workers | wall s | single s | records | align s | unique profile keys | reusable calls | est saved s | est saved / align | fallbacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 4 | 3.091 | 6.812 | 926 | 11.242 | 8 | 147,262 | 4.232 | 37.64% | 0 |
| rheMac10 top8 | 6 | 4 | 2.978 | 5.949 | 926 | 16.745 | 8 | 147,262 | 6.319 | 37.74% | 0 |
| rheMac10 top8 | 4 | 6 | 2.997 | 6.602 | 926 | 11.833 | 8 | 147,262 | 4.352 | 36.78% | 0 |
| rheMac10 top8 | 6 | 6 | 2.987 | 5.993 | 926 | 17.646 | 8 | 147,262 | 6.520 | 36.95% | 0 |
| hg38 chr21+chr22 | 4 | 4 | 47.023 | 77.598 | 7,274 | 100.456 | 2 | 1,420,425 | 36.628 | 36.46% | 0 |
| hg38 chr21+chr22 | 6 | 4 | 44.614 | 70.986 | 7,274 | 149.502 | 2 | 1,420,425 | 54.368 | 36.37% | 0 |
| hg38 chr21+chr22 | 4 | 6 | 44.321 | 76.234 | 7,274 | 100.295 | 2 | 1,420,425 | 36.523 | 36.42% | 0 |
| hg38 chr21+chr22 | 6 | 6 | 45.725 | 71.066 | 7,274 | 149.944 | 2 | 1,420,425 | 54.063 | 36.06% | 0 |

The dominant signal is stable:

```text
profile reusable calls are effectively all align calls after the first key per process
estimated saved profile-build seconds are about 36-38% of measured align time
digest remains clean because the shadow does not change the real path
```

## Reuse Detail

The sharded `*_unique_keys` fields are sums of per-Fasim-process unique-key
counts. They are not global cross-worker de-duplication counts. In this setup,
each contig shard runs as a separate Fasim process, so the rheMac10 top8 rows
show eight unique profile/query keys and the hg38 chr21+chr22 rows show two.

| workload | extend threads | workers | build calls | unique profile keys | reusable calls | reuse rate | saved fraction | unique ratio | query unique keys | query reusable calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 4 | 147,270 | 8 | 147,262 | 99.99457% | 99.98649% | 0.005432% | 8 | 147,262 |
| rheMac10 top8 | 6 | 4 | 147,270 | 8 | 147,262 | 99.99457% | 99.99190% | 0.005432% | 8 | 147,262 |
| rheMac10 top8 | 4 | 6 | 147,270 | 8 | 147,262 | 99.99457% | 99.98870% | 0.005432% | 8 | 147,262 |
| rheMac10 top8 | 6 | 6 | 147,270 | 8 | 147,262 | 99.99457% | 99.99489% | 0.005432% | 8 | 147,262 |
| hg38 chr21+chr22 | 4 | 4 | 1,420,427 | 2 | 1,420,425 | 99.99986% | 99.99972% | 0.000141% | 2 | 1,420,425 |
| hg38 chr21+chr22 | 6 | 4 | 1,420,427 | 2 | 1,420,425 | 99.99986% | 99.99989% | 0.000141% | 2 | 1,420,425 |
| hg38 chr21+chr22 | 4 | 6 | 1,420,427 | 2 | 1,420,425 | 99.99986% | 99.99962% | 0.000141% | 2 | 1,420,425 |
| hg38 chr21+chr22 | 6 | 6 | 1,420,427 | 2 | 1,420,425 | 99.99986% | 99.99977% | 0.000141% | 2 | 1,420,425 |

The query-key and profile-key counts match in these workloads, which is
consistent with repeated same-query alignment. The current key also includes
the translated query hash, translated query length, score matrix hash/size, gap
open, gap extend, and score size.

## Interpretation

The real workload shadow data supports a real profile cache investigation:

```text
profile keys are few
reusable calls are high
estimated saved profile-build time is material
```

The opportunity is large because these workloads repeatedly align H19-derived
query sequence against many target windows. However, the estimate is still an
upper bound. A real cache must pay for lookup, lifetime management, memory, and
thread-safety, and it must prove exact output equivalence.

The current data does not justify:

```text
GPU CIGAR
GPU full traceback
Accelign or Parasail as output authority
single-process multi-GPU
chunking / overlap
historical final speed-stack claims
```

It also does not make GPU utilization the decision metric. Current-base GPU
work remains short preAlign CUDA bursts; the measured profile reuse opportunity
is inside CPU `aligner.Align()` setup.

## Decision

The next implementation PR can be a default-off real profile cache probe, not a
default behavior change:

```text
FASIM_ALIGN_PROFILE_CACHE=1
FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1
```

Recommended guardrails:

```text
CPU output remains authoritative.
Keep the cache default-off.
Start with per-thread or otherwise thread-safe cache ownership.
Validate score, endpoint, CIGAR, record digest, fallbacks, and mismatches.
Report cache lookups, hits, misses, unique keys, memory estimate, build seconds
saved, validate mismatches, and fallback counts.
Fall back to normal per-call profile build on any validation uncertainty.
```

If the real cache probe shows low net speedup after lookup/locking overhead, or
if any validation mismatch appears, keep the shadow telemetry and move to a
separate forward score/end score-only GPU shadow. That future GPU shadow must
remain diagnostic first and keep CPU output authoritative.
