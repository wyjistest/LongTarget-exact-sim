# Fasim Current-Base Align Profile Cache Opt-In

This note documents the default-off current-base align profile cache added
after the profile reuse shadow characterization.

The cache is an opt-in CPU-side optimization. It does not change output,
scoring, thresholds, endpoint selection, CIGAR/traceback logic, sharded
scheduling, GPU policy, merge semantics, chunking, or in-process multi-GPU
behavior. CPU `aligner.Align()` output remains authoritative.

## Enable

The default path is unchanged.

```bash
FASIM_ALIGN_PROFILE_CACHE=1
```

Validation mode is also default-off:

```bash
FASIM_ALIGN_PROFILE_CACHE=1
FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1
```

Validation mode rebuilds the legacy per-call SSW profile, reruns the legacy
alignment side path, compares score, endpoints, CIGAR, and an alignment digest
proxy, and falls back to the legacy result on any mismatch. It is a correctness
gate, not a performance mode.

This PR intentionally uses current-base env names. It does not use historical
final speed-stack names as active implementation claims.

## Implementation Boundary

The cache only reuses `ssw_init()` profile objects. It does not replace:

```text
ssw_align()
forward score/end DP
reverse-start recovery
banded traceback / CIGAR
alignment conversion
Fasim record construction
output merge
```

`s_profile` stores a `read` pointer, so cache entries own their translated query
buffer and score matrix copy for the lifetime of the cached profile. The first
implementation is thread-local to avoid cross-thread sharing of profile
objects.

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

Orientation and strand are represented by the actual translated query sequence
passed to `aligner.Align()`.

## Telemetry

Each Fasim process emits:

| field | meaning |
|---|---|
| `benchmark.fasim_align_profile_cache_requested` | `1` when `FASIM_ALIGN_PROFILE_CACHE=1`. |
| `benchmark.fasim_align_profile_cache_active` | `1` when the cache path was active. |
| `benchmark.fasim_align_profile_cache_validate` | `1` when validate mode was active. |
| `benchmark.fasim_align_profile_cache_calls` | Align calls observed by the cache path. |
| `benchmark.fasim_align_profile_cache_hits` | Profile cache hits. |
| `benchmark.fasim_align_profile_cache_misses` | Profile cache misses. |
| `benchmark.fasim_align_profile_cache_unique_keys` | Unique profile keys observed in the process. |
| `benchmark.fasim_align_profile_cache_build_seconds` | Profile build seconds paid on cache misses. |
| `benchmark.fasim_align_profile_cache_saved_seconds` | Sum of prior miss build seconds attributed to cache hits; use as an estimate, not exact wall savings. |
| `benchmark.fasim_align_profile_cache_validate_seconds` | Extra validation side-path seconds. |
| `benchmark.fasim_align_profile_cache_score_mismatches` | Score mismatches found by validate mode. |
| `benchmark.fasim_align_profile_cache_endpoint_mismatches` | Endpoint mismatches found by validate mode. |
| `benchmark.fasim_align_profile_cache_cigar_mismatches` | CIGAR mismatches found by validate mode. |
| `benchmark.fasim_align_profile_cache_digest_mismatches` | Alignment digest-proxy mismatches found by validate mode. |
| `benchmark.fasim_align_profile_cache_fallbacks` | Legacy fallback count after validation mismatch. |

Sharded reports aggregate these fields into per-shard, per-worker,
`sharded_telemetry`, and `single_run.telemetry`.

## A/B Workload Matrix

All rows used:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
--gpu-ids 0,1
--cpu-pool 0-19
--cpu-cores-per-worker 3
--auto-cpu-core-ranges
env -u FASIM_CUDA_DEVICES
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

All rows were digest clean against single-process validation and had zero
preAlign CUDA fallbacks. The mismatch column is:

```text
score / endpoint / CIGAR / digest / fallback
```

| workload | workers | mode | wall s | wall delta | single s | records | hits | misses | hit rate | profile s | validate s | mismatches |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| rheMac10 top8 | 4 | baseline | 3.051 | +0.00% | 6.000 | 926 | 0 | 0 | 0.0000% | 5.873 | 0.000 | 0/0/0/0/0 |
| rheMac10 top8 | 4 | cache | 2.697 | -11.58% | 5.460 | 926 | 147,197 | 73 | 99.9504% | 0.099 | 0.000 | 0/0/0/0/0 |
| rheMac10 top8 | 4 | cache_validate | 3.592 | +17.75% | 6.747 | 926 | 147,198 | 72 | 99.9511% | 0.097 | 15.162 | 0/0/0/0/0 |
| rheMac10 top8 | 6 | baseline | 3.029 | +0.00% | 5.940 | 926 | 0 | 0 | 0.0000% | 6.106 | 0.000 | 0/0/0/0/0 |
| rheMac10 top8 | 6 | cache | 2.649 | -12.53% | 5.494 | 926 | 147,203 | 67 | 99.9545% | 0.078 | 0.000 | 0/0/0/0/0 |
| rheMac10 top8 | 6 | cache_validate | 3.166 | +4.54% | 6.663 | 926 | 147,203 | 67 | 99.9545% | 0.131 | 16.974 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 4 | baseline | 44.572 | +0.00% | 71.154 | 7,274 | 0 | 0 | 0.0000% | 52.990 | 0.000 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 4 | cache | 39.638 | -11.07% | 66.783 | 7,274 | 1,420,325 | 102 | 99.9928% | 0.019 | 0.000 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 4 | cache_validate | 50.099 | +12.40% | 77.417 | 7,274 | 1,420,325 | 102 | 99.9928% | 0.007 | 123.854 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 6 | baseline | 44.362 | +0.00% | 71.407 | 7,274 | 0 | 0 | 0.0000% | 52.833 | 0.000 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 6 | cache | 39.693 | -10.52% | 66.921 | 7,274 | 1,420,326 | 101 | 99.9929% | 0.005 | 0.000 | 0/0/0/0/0 |
| hg38 chr21+chr22 | 6 | cache_validate | 49.600 | +11.81% | 77.486 | 7,274 | 1,420,325 | 102 | 99.9928% | 0.037 | 124.488 | 0/0/0/0/0 |

## Interpretation

The real cache probe converts the #151 reuse opportunity into measured wall
time improvement:

```text
rheMac10 top8:
  cache wall improvement: about 11.6-12.5%

hg38 chr21+chr22:
  cache wall improvement: about 10.5-11.1%

validate mode:
  mismatch/fallback counters remain zero
  wall time is slower because it intentionally reruns the legacy side path
```

The cache removes almost all measured profile-build seconds from the real path.
The `cache_saved_seconds` field is useful for confirming hit opportunity but is
not an exact wall-time predictor because it sums per-call/thread estimates.

## Decision

Keep `FASIM_ALIGN_PROFILE_CACHE=1` as a default-off real opt-in candidate.
It is a lower-risk CPU optimization than score-only GPU shadowing because it
does not change SSW alignment logic or output authority.

Recommended use while this remains opt-in:

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

Use `FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1` for validation sweeps, not for
performance runs.

Do not use this result to justify GPU CIGAR, GPU full traceback, Accelign or
Parasail output authority, single-process multi-GPU, chunking/overlap, or
historical final speed-stack claims. If further optimization is needed after
profile caching, the next measured target remains forward score/end work under
a separate score-only shadow.
