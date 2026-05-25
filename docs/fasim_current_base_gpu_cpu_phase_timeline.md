# Fasim Current-Base GPU/CPU Phase Timeline

This note characterizes the current clean `cuda-p0.2-initial-handoff-pipeline`
base after #141 and #142. It intentionally describes only the runtime behavior
that is active in this checkout.

## Boundary

This is not the historical Fasim final speed-stack branch. The current clean
base primarily exposes Fasim CUDA through the preAlign CUDA path:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> batched preAlign CUDA topK/peak generation
  -> CPU-side peak suppression, fastSIM extension, SSW/align, output
```

The following historical speed-stack env names are not active source envs in
this clean base unless their implementation is integrated separately:

```text
FASIM_TRANSFERSTRING_TABLE
FASIM_GPU_DP_COLUMN_AUTO
FASIM_SSW_PROFILE_CACHE
FASIM_SSW_AVX2
FASIM_SSW_PROFILE_CONTEXT
```

`FASIM_EXACT_COLUMN_EXTEND_BATCH` is present in the current binary as the
single-process multi-GPU safety guard added by #141. It should not be described
as an active exact-column batch implementation on this clean base.

## Active Env Audit

`strings ./fasim_longtarget_cuda | rg 'FASIM_[A-Z0-9_]+' | sort -u` on this
checkout reports:

```text
FASIM_CUDA_DEVICE
FASIM_CUDA_DEVICES
FASIM_DEBUG_CUDA_PREALIGN
FASIM_ENABLE_PREALIGN_CUDA
FASIM_EXACT_COLUMN_EXTEND_BATCH
FASIM_EXTEND_THREADS
FASIM_OUTPUT_MODE
FASIM_PREALIGN_CUDA_MAX_TASKS
FASIM_PREALIGN_CUDA_TOPK
FASIM_PREALIGN_PEAK_SUPPRESS_BP
FASIM_VERBOSE
FASIM_WRITE_TFOSORTED_LITE
```

Operationally relevant settings for the sharded current-base runs are:

| env | current role |
|---|---|
| `FASIM_ENABLE_PREALIGN_CUDA` | Enables the Fasim preAlign CUDA path when the CUDA binary is used. |
| `FASIM_EXTEND_THREADS` | Controls CPU worker threads inside each Fasim process for the extension/output phase. |
| `FASIM_CUDA_DEVICE` | Selects the logical CUDA device inside each worker. The sharded runner sets it to `0` after constraining `CUDA_VISIBLE_DEVICES`. |
| `FASIM_CUDA_DEVICES` | In-process multi-device preAlign/topK device list. Do not use as the recommended multi-GPU mode with exact-column guard settings. |
| `FASIM_PREALIGN_CUDA_TOPK` | Top-K peaks per preAlign task, default `64`, capped at `256`. |
| `FASIM_PREALIGN_CUDA_MAX_TASKS` | Max preAlign tasks per GPU batch, default `4096`. |
| `FASIM_PREALIGN_PEAK_SUPPRESS_BP` | CPU-side peak suppression radius after CUDA returns peaks, default `5`. |
| `FASIM_OUTPUT_MODE` | Runner sets `lite` for these measurements. |
| `FASIM_DEBUG_CUDA_PREALIGN` | Debug print path for selected CUDA preAlign batches; not a structured telemetry stream. |
| `FASIM_VERBOSE` / `FASIM_WRITE_TFOSORTED_LITE` | Output/log behavior controls. |
| `FASIM_EXACT_COLUMN_EXTEND_BATCH` | Guarded for unsafe single-process multi-GPU combinations in this clean base. |

## Safety State

#141 fails closed for the known unsafe combination:

```text
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
FASIM_CUDA_DEVICES=0,1
```

The supported multi-GPU execution model is process-level sharding. Each worker
gets one visible GPU:

```text
CUDA_VISIBLE_DEVICES=<assigned physical GPU>
FASIM_CUDA_DEVICE=0
FASIM_CUDA_DEVICES unset for the worker
```

#142 serializes sharded-runner manifest payload mutation with atomic manifest
writes. That matters for 6-worker characterization, where concurrent manifest
updates previously exposed a `dictionary changed size during iteration` runner
race even though Fasim shard subprocesses completed normally.

## Workload

Host:

```text
CPU: 20 logical CPUs, Intel Core i9-10900X
GPU: 2 x NVIDIA GeForce RTX 4090
CPU pool: 0-19
CPU cores per worker: 3
GPU ids: 0,1
```

Workload:

```text
name: rheMac10_nonchrom_top8_H19
target: /data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa
RNA: H19.fa
rule: 1
contigs: 8
bases: 7,181,742
output mode: lite
```

Contigs:

| contig | bases |
|---|---:|
| QNVO02000334.1 | 1,229,889 |
| ML143124.1 | 1,117,261 |
| ML143121.1 | 1,005,795 |
| ML143119.1 | 862,827 |
| ML143120.1 | 823,856 |
| ML143117.1 | 738,392 |
| ML143122.1 | 733,739 |
| ML143118.1 | 669,983 |

## Command

Each run used digest validation against a single-process run:

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target /data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_phase_timeline/runs/et${FASIM_EXTEND_THREADS}_w${WORKERS} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_phase_timeline/runs/et${FASIM_EXTEND_THREADS}_w${WORKERS}/run_manifest.json \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=${FASIM_EXTEND_THREADS}
```

GPU utilization was sampled externally with:

```bash
nvidia-smi --query-gpu=timestamp,index,utilization.gpu,utilization.memory,power.draw,memory.used \
  --format=csv,noheader,nounits -lms 200
```

The sampler captures coarse GPU occupancy and power. It is not the same as
kernel time. Current Fasim does not emit structured preAlign H2D, kernel, D2H,
or CPU-extension phase telemetry into the sharded-runner report.

## Matrix Results

| extend threads | workers | wall s | single s | speedup vs single | digest | records | GPU avg | GPU max |
|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 1 | 2 | 7.139 | 10.657 | 1.49x | True | 926 | 1.29% | 12% |
| 1 | 4 | 3.869 | 10.642 | 2.75x | True | 926 | 1.59% | 12% |
| 1 | 6 | 4.218 | 10.749 | 2.55x | True | 926 | 1.50% | 17% |
| 2 | 2 | 5.532 | 8.075 | 1.46x | True | 926 | 1.70% | 12% |
| 2 | 4 | 3.049 | 8.183 | 2.68x | True | 926 | 2.17% | 18% |
| 2 | 6 | 2.993 | 8.174 | 2.73x | True | 926 | 2.04% | 21% |
| 4 | 2 | 4.960 | 6.474 | 1.31x | True | 926 | 1.91% | 12% |
| 4 | 4 | 2.961 | 6.370 | 2.15x | True | 926 | 2.32% | 18% |
| 4 | 6 | 2.716 | 6.392 | 2.35x | True | 926 | 2.46% | 14% |

All measured runs passed the single-vs-sharded digest gate with 926 merged
records.

## Worker Balance

The fastest row in this run was `FASIM_EXTEND_THREADS=4`, `workers=6`, with
wall time 2.716s. Its per-worker shape was:

```text
worker seconds: [2.650, 2.615, 1.752, 1.670, 2.716, 2.529]
worker records: [68, 241, 110, 150, 211, 146]
gpu ids:        [0, 1, 0, 1, 0, 1]
cpu ranges:     [0-2, 3-5, 6-8, 9-11, 12-14, 15-17]
```

The 4-worker row was close and simpler:

```text
FASIM_EXTEND_THREADS=4 workers=4 wall=2.961s
worker seconds: [2.961, 2.568, 2.407, 2.765]
worker records: [127, 300, 197, 302]
```

This indicates that 4-6 workers on 2 GPUs is the local tuning range for this
workload and host. Do not promote either value to a global default based on one
8-contig workload.

## Interpretation

The current clean-base Fasim GPU path is narrow and bursty. The measured GPU
average utilization is low, while wall time improves strongly from CPU extension
threads and process-level worker density. That is consistent with the current
pipeline shape:

```text
preAlign CUDA burst
  -> CPU peak filtering / suppression
  -> CPU fastSIM extension and SSW alignment work
  -> per-worker output
  -> runner merge and digest validation
```

`FASIM_EXTEND_THREADS=4` improves the single-process validation time from about
10.7s at one extend thread to about 6.4s. That points to CPU-side extension work
being material for this workload. Increasing workers from 2 to 4/6 reduces wall
for the sharded portion by spreading contigs and CPU-side extension across more
processes, while each worker remains a single-visible-GPU process.

The low GPU averages should not be read as a failed GPU run. They mean the
current clean base is not dominated by a long GPU kernel lane. The GPU work is
short enough that the 200ms sampler mostly observes CPU-side phases around the
preAlign bursts.

## Current Local Recommendation

For this machine and this workload, use the current-base active envs only:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=4 \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target /data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_run \
  --output-mode lite \
  --workers 4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3
```

Use `--workers 6` as the next candidate when the workload has enough contigs and
when extra CPU oversubscription is acceptable. Keep digest validation in tuning
runs.

## Telemetry Gaps

The current sharded report exposes:

```text
wall_seconds
single_run.wall_seconds
per_worker[*].wall_seconds
per_shard[*].run.wall_seconds
merged_records / merged_digest
single_vs_sharded_digest_match
worker GPU id and CPU core range assignments
```

The current report does not expose:

```text
preAlign CUDA task count per batch/run
preAlign CUDA kernel seconds per run
preAlign CUDA H2D/D2H seconds
CPU extension seconds
output write seconds
runner merge seconds
worker idle seconds
```

`cuda/prealign_cuda.cu` does compute `PreAlignCudaBatchResult.gpuSeconds`, but
that value is not aggregated into the Fasim process output or sharded-runner
JSON. H2D/D2H timing is not split out by the current preAlign API.

A future instrumentation PR should add structured current-base telemetry before
attempting another GPU optimization:

```text
fasim_prealign_cuda_active
fasim_prealign_cuda_batches
fasim_prealign_cuda_tasks
fasim_prealign_cuda_kernel_seconds
fasim_prealign_cuda_h2d_seconds, if added to the CUDA API
fasim_prealign_cuda_d2h_seconds, if added to the CUDA API
fasim_extend_seconds
fasim_output_seconds
fasim_merge_seconds in runner
```

## Decision

- If CPU extension remains dominant after instrumentation, tune
  `FASIM_EXTEND_THREADS`, worker density, and CPU affinity first.
- If preAlign CUDA kernel seconds dominates while GPU utilization remains low,
  inspect `FASIM_PREALIGN_CUDA_MAX_TASKS`, `FASIM_PREALIGN_CUDA_TOPK`, and batch
  shape.
- If worker imbalance dominates, improve the shard cost model or scheduler
  assignment before changing Fasim internals.
- If merge/output dominates, decompose runner merge and Fasim output costs.
- Do not use single-process multi-GPU as the recommended Fasim multi-GPU mode on
  this branch.
- Do not claim historical final-speed-stack behavior from this current clean
  base.
