# Fasim Current-Base SSW Profile Reuse Shadow

This note documents the current-base SSW profile/query reuse shadow added after
the aligner internal characterization. It is telemetry-only: Fasim still builds
profiles normally for every `aligner.Align()` call, and CPU alignment output
remains authoritative.

## Scope

This PR does not change:

```text
scoring
thresholds
endpoint selection
CIGAR / traceback
record construction
output
sharded scheduling
GPU policy
merge semantics
```

It also does not add Accelign, GPU kernels, in-process multi-GPU, chunking, or
historical final speed-stack behavior.

The active current-base GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension
  -> CPU aligner.Align()
  -> output
```

## Why This Shadow Exists

#149 showed this real-workload split:

```text
aligner.Align / extension:     about 98.2-99.0%
profile setup / align outer:   about 41-43%
SSW total / align outer:       about 53-55%
forward score/end / SSW:       about 70-73%
traceback/CIGAR / SSW:         about 6-8%
```

That makes profile setup a large, low-risk target to characterize before a
score-only GPU probe. A profile reuse cache would not change endpoint or CIGAR
logic, but it must still be gated by measured reuse opportunity and exactness
before any real path is added.

## Enable

The shadow is default-off:

```bash
FASIM_ALIGN_PROFILE_REUSE_SHADOW=1
```

The real alignment path still calls `ssw_init()` for every alignment request.
The shadow records keys and estimates how much profile build time would have
been reusable if a real cache existed.

## Telemetry Fields

Each Fasim process emits these fields in stderr:

| field | meaning |
|---|---|
| `benchmark.fasim_align_profile_reuse_shadow_enabled` | `1` when `FASIM_ALIGN_PROFILE_REUSE_SHADOW=1`, otherwise `0`. |
| `benchmark.fasim_align_profile_build_calls` | Number of observed `ssw_init()` profile builds while the shadow is enabled. |
| `benchmark.fasim_align_profile_unique_keys` | Number of unique profile keys observed in the process. |
| `benchmark.fasim_align_profile_reusable_calls` | Number of profile builds after the first build for the same profile key. |
| `benchmark.fasim_align_profile_build_seconds` | Total measured profile build seconds while the shadow is enabled. |
| `benchmark.fasim_align_profile_est_saved_seconds` | Sum of measured profile build seconds for reusable calls; this is an upper-bound estimate, not a measured real-cache speedup. |
| `benchmark.fasim_align_query_unique_keys` | Number of unique translated query keys observed in the process. |
| `benchmark.fasim_align_query_reusable_calls` | Number of calls after the first call for the same translated query key. |

Sharded runner reports parse these fields into each shard, worker aggregate,
`sharded_telemetry`, and `single_run.telemetry`. In sharded aggregates,
`*_unique_keys` is the sum of per-process unique-key counts, not a global
cross-worker de-duplication.

## Key Definition

The profile key includes:

```text
translated query length
translated query hash
score matrix size
score matrix hash
gap open penalty
gap extend penalty
score_size
```

The query key includes:

```text
translated query length
translated query hash
```

Orientation and strand are represented by the actual query sequence passed to
`aligner.Align()`. This shadow does not add separate strand labels because the
current aligner API does not carry an explicit strand parameter.

## Interpreting Results

Use these derived values:

```text
profile reuse rate = reusable_calls / build_calls
estimated saved fraction = est_saved_seconds / profile_build_seconds
query reuse rate = query_reusable_calls / build_calls
```

This is only an opportunity estimate. A real cache would also need:

```text
cache lookup overhead
cache memory footprint
thread-safety cost
profile lifetime management
validate/fallback behavior
exactness proof against CPU authority
```

## Small Smoke Signal

On `testDNA.fa + H19.fa` with `FASIM_EXTEND_THREADS=2`, the shadow reports a
single repeated query/profile key while keeping output unchanged:

```text
fasim_align_profile_reuse_shadow_enabled=1
fasim_align_profile_build_calls=165
fasim_align_profile_unique_keys=1
fasim_align_profile_reusable_calls=164
fasim_align_profile_build_seconds=0.007025386
fasim_align_profile_est_saved_seconds=0.006926685
fasim_align_query_unique_keys=1
fasim_align_query_reusable_calls=164
```

This only confirms that the shadow wiring can observe reuse on a small
workload. It is not a large-workload performance conclusion.

## Recommended Real-Workload Command Shape

Use only current-base active envs:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=4 \
FASIM_ALIGN_PROFILE_REUSE_SHADOW=1 \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target ${TARGET_FASTA} \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_profile_reuse_shadow/${RUN_ID} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_profile_reuse_shadow/${RUN_ID}/run_manifest.json
```

For the same workloads used in #149, start with:

```text
rheMac10_nonchrom_top8_H19:
  workers=4 or 6
  FASIM_EXTEND_THREADS=4 or 6

hg38_chr21_chr22_H19:
  workers=4 or 6, but only two contigs are non-empty
  FASIM_EXTEND_THREADS=4 or 6
```

## Decision Gate

Move to a default-off real profile cache only if real workload shadow data shows:

```text
profile unique keys are few
profile reusable calls are high
estimated saved seconds are material
digest remains clean
cache memory and locking look bounded
```

Skip real profile caching and move to forward score/end GPU shadow if:

```text
profile keys are mostly unique
estimated saved seconds are small
thread-local or process-local cache overhead would likely dominate
```

Stop the profile reuse path if any future real-cache probe changes:

```text
score
endpoint
CIGAR
record identity
digest
```

This shadow must not be used to justify GPU CIGAR, GPU full traceback,
in-process multi-GPU, chunking/overlap, or historical final speed-stack claims.
