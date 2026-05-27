# Fasim Current-Base Runtime Recommendation

This note summarizes the recommended runtime shape for the current clean
`cuda-p0.2-initial-handoff-pipeline` base after the current-base telemetry,
worker-density, and align profile cache characterization work.

## Boundary

This document describes only the implementation that is active in the current
clean base. The current GPU path is:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA burst
  -> CPU peak suppression
  -> CPU fastSIM extension and aligner.Align()
  -> CPU output and sharded merge
```

The current base should not be described as the historical final speed-stack
implementation. In particular, do not use historical exact-column or SSW env
names to claim current runtime behavior unless those implementations are
separately integrated into this branch.

## Current Active Env

These envs are active knobs in the current clean-base runtime or runner-facing
workflow:

| env | role |
|---|---|
| `FASIM_ENABLE_PREALIGN_CUDA` | Enables the current preAlign CUDA path in the CUDA Fasim binary. |
| `FASIM_EXTEND_THREADS` | Controls CPU extension/output worker threads inside each Fasim process. |
| `FASIM_ALIGN_PROFILE_REUSE_SHADOW` | Default-off telemetry-only profile reuse opportunity shadow. |
| `FASIM_ALIGN_PROFILE_CACHE` | Default-off current-base opt-in cache for repeated `ssw_init()` profiles. |
| `FASIM_ALIGN_PROFILE_CACHE_VALIDATE` | Default-off correctness audit mode for the profile cache; not a performance mode. |
| `FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW` | Default-off diagnostic score/end GPU shadow; not a performance mode or output authority. |
| `FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW` | Default-off diagnostic batched score/end GPU shadow; current implementation is not a performance mode or output authority. |
| `FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW` | Default-off diagnostic low-copy score bridge shadow; current implementation is stopped as a performance path. |
| `FASIM_CUDA_DEVICE` | Selects the logical CUDA device inside a worker. With sharding this is normally `0`. |
| `FASIM_CUDA_DEVICES` | In-process CUDA device list for preAlign/topK paths. Do not use it as the recommended multi-GPU mode for current sharded runs. |
| `FASIM_PREALIGN_CUDA_TOPK` | PreAlign CUDA top-K peak count per task. |
| `FASIM_PREALIGN_CUDA_MAX_TASKS` | PreAlign CUDA task cap per GPU batch. |
| `FASIM_PREALIGN_PEAK_SUPPRESS_BP` | CPU-side peak suppression radius after CUDA preAlign. |
| `FASIM_OUTPUT_MODE` | Output mode, commonly `lite` in sharded performance runs. |
| `FASIM_VERBOSE` | Verbose logging control. |
| `FASIM_WRITE_TFOSORTED_LITE` | Optional lite-output write control. |
| `FASIM_DEBUG_CUDA_PREALIGN` | Debug print path for preAlign CUDA batches. |
| `FASIM_EXACT_COLUMN_EXTEND_BATCH` | Present as a safety-guarded env in this clean base; do not describe it as an active exact-column batch implementation here. |

## Recommended Local Opt-In

For the tested local 2x4090 same-query multi-target workloads, the current
recommended opt-in candidate is:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_run \
  --output-mode lite \
  --gpu-ids 0,1 \
  --workers 4 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest run_manifest.json
```

Use `--workers 6` as the next candidate when the workload has enough shards and
the host has enough CPU headroom. Do not promote either worker count to a global
default from the local 2x4090 characterization alone.

Use this only for validation/audit sweeps:

```bash
FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1
```

Validate mode rebuilds the legacy profile and reruns the legacy alignment side
path to compare score, endpoints, CIGAR, and an alignment digest proxy. It is
expected to be slower and should not be used as the performance mode.

## Multi-GPU Policy

The recommended multi-GPU execution model is process-level sharding:

```text
one worker process -> one visible GPU
```

With `--gpu-ids`, `scripts/fasim_sharded_runner.py` assigns each worker a
single physical GPU by setting:

```text
CUDA_VISIBLE_DEVICES=<assigned physical GPU>
FASIM_CUDA_DEVICE=0
FASIM_CUDA_DEVICES unset
```

Do not run the parent environment with `FASIM_CUDA_DEVICES=0,1` and treat that
as the current recommended single-process multi-GPU mode. The current clean-base
wall-clock wins come from worker density, CPU extension threads, CPU affinity,
and the profile cache opt-in, not from keeping one Fasim process resident across
multiple GPUs.

## Historical Non-Current Env Names

These names appear in older speed-stack notes or historical branches, but they
are not current clean-base active implementations unless separately integrated:

```text
FASIM_TRANSFERSTRING_TABLE
FASIM_GPU_DP_COLUMN_AUTO
FASIM_SSW_PROFILE_CACHE
FASIM_SSW_AVX2
FASIM_SSW_PROFILE_CONTEXT
```

Use `FASIM_ALIGN_PROFILE_CACHE=1` for the current-base profile cache opt-in.
Do not call it `FASIM_SSW_PROFILE_CACHE` in current-base recommendations.

## Current Result Summary

The latest repeated characterization for `FASIM_ALIGN_PROFILE_CACHE=1` measured
three-run medians on two same-query multi-target workloads with 2x4090
process-level sharding:

| workload | workers | median wall change with cache |
|---|---:|---:|
| rheMac10 top8 | 4 | -11.05% |
| rheMac10 top8 | 6 | -12.65% |
| hg38 chr21+chr22 | 4 | -13.76% |
| hg38 chr21+chr22 | 6 | -12.40% |

Correctness and safety counters stayed clean:

```text
digest clean: 36/36
preAlign CUDA fallbacks: 0
profile cache score mismatches: 0
profile cache endpoint mismatches: 0
profile cache CIGAR mismatches: 0
profile cache digest mismatches: 0
profile cache fallbacks: 0
```

This makes `FASIM_ALIGN_PROFILE_CACHE=1` a current-base recommended opt-in
candidate for the tested local workloads. It should remain default-off until
broader workload and hardware coverage exists.

## Next Performance Direction

After enabling the profile cache, the remaining aligner internals were
re-measured and forward score/end remained the largest block. The GPU score
line then passed through per-request, batched, and low-copy score bridge
diagnostic shadows. The score/end contract stayed clean, but the current
implementation did not beat CPU forward score/end on real-workload samples.

Treat the current GPU score bridge line as stopped for performance work:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1:
  diagnostic only

FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1:
  diagnostic only

FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1:
  diagnostic/research only; current implementation is no-go for real opt-in
```

The current score bridge characterization found:

```text
digest clean: 12/12
bridge score mismatches: 0
bridge endpoint mismatches: 0

rheMac10 top8 full processed rows:
  2.06-3.07x CPU forward score/end

hg38 chr21+chr22 capped processed-only estimate:
  1.16-1.51x CPU forward score/end
```

Only restart GPU score work with a materially different DP execution design
that is shadow-first, score-clean, and faster than CPU forward score/end on
real workloads. CPU `aligner.Align()` remains the output authority.

Do not use the current profile-cache result to justify:

```text
GPU CIGAR
GPU traceback
GPU full extension replacement
Accelign or Parasail output authority
single-process multi-GPU as the main policy
chunking or overlap
historical final speed-stack claims
```
