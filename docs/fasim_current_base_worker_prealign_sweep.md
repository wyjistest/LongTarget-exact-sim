# Fasim Current-Base Worker and preAlign Parameter Sweep

This note characterizes a local worker-density, CPU extension, and preAlign
parameter sweep on the current clean `cuda-p0.2-initial-handoff-pipeline` base
after #144. It uses the #144 `benchmark.fasim_*` telemetry to explain wall time
instead of relying on coarse `nvidia-smi` averages alone.

## Scope

This is a docs/result PR only:

- No Fasim C++ runtime behavior is changed.
- No scoring, threshold, non-overlap, output, or digest semantics are changed.
- No scheduler default is changed.
- No chunking, overlap, or in-process multi-GPU support is added.
- No historical final speed-stack behavior is claimed.

The active GPU path in this base is the current preAlign CUDA path:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> batched preAlign CUDA topK/peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension / alignment / output
```

The historical final speed-stack env names are not used for this sweep unless
they are separately integrated into this current base.

## Host and Workload

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
target: /data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa
RNA: H19.fa
rule: 1
contigs: 8
bases: 7,181,742
output mode: lite
```

All sharded runs used one visible GPU per worker through the sharded runner.
The parent environment explicitly removed `FASIM_CUDA_DEVICES`.

## Command Shape

Phase 1 swept `FASIM_EXTEND_THREADS` and worker count:

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target /data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_worker_prealign_sweep/phase1_runs/et${ET}_w${WORKERS} \
  --output-mode lite \
  --validate-single \
  --workers ${WORKERS} \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest .tmp/fasim_current_base_worker_prealign_sweep/phase1_runs/et${ET}_w${WORKERS}/run_manifest.json \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=${ET}
```

Phase 2 fixed `FASIM_EXTEND_THREADS=6` and `workers=4`, then swept selected
preAlign knobs:

```text
FASIM_PREALIGN_CUDA_TOPK=64,128,256
FASIM_PREALIGN_CUDA_MAX_TASKS=4096,8192
```

GPU utilization was sampled externally at 200ms intervals with `nvidia-smi`.
The preAlign and extend seconds below come from #144 runner telemetry. Sharded
telemetry seconds are summed across worker processes, so they can exceed wall
time when workers run concurrently.

## Phase 1: Workers x EXTEND_THREADS

All rows were digest clean against the single-process validation run:

```text
single_vs_sharded_digest_match=True
merged_records=926
fallbacks=0
```

| extend threads | workers | wall s | single s | speedup vs single | GPU avg | GPU max | preAlign total s | extend s | records |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 2 | 5.792 | 8.574 | 1.48x | 1.658% | 13% | 0.232707 | 7.155420 | 926 |
| 2 | 4 | 3.146 | 8.393 | 2.67x | 1.661% | 13% | 0.202481 | 7.155440 | 926 |
| 2 | 6 | 3.035 | 8.449 | 2.78x | 2.076% | 20% | 0.197055 | 7.327491 | 926 |
| 4 | 2 | 4.990 | 6.546 | 1.31x | 1.890% | 12% | 0.194876 | 9.535225 | 926 |
| 4 | 4 | 3.000 | 6.590 | 2.20x | 2.469% | 17% | 0.213649 | 9.955835 | 926 |
| 4 | 6 | 2.937 | 6.654 | 2.27x | 2.316% | 18% | 0.200583 | 10.581825 | 926 |
| 6 | 2 | 5.028 | 5.988 | 1.19x | 2.054% | 12% | 0.195076 | 14.105261 | 926 |
| 6 | 4 | 2.867 | 5.871 | 2.05x | 2.656% | 18% | 0.208506 | 14.851318 | 926 |
| 6 | 6 | 2.805 | 5.986 | 2.13x | 2.522% | 19% | 0.229144 | 17.209586 | 926 |

The fastest row was:

```text
FASIM_EXTEND_THREADS=6
workers=6
wall_seconds=2.805
```

The simpler near-best row was:

```text
FASIM_EXTEND_THREADS=6
workers=4
wall_seconds=2.867
```

That is about 2% slower than the fastest row while using fewer processes.

## Worker Balance

For the fastest row:

```text
FASIM_EXTEND_THREADS=6
workers=6
worker seconds:        [2.745, 2.602, 1.891, 1.776, 2.805, 2.641]
worker records:        [68, 241, 110, 150, 211, 146]
worker preAlign total: [0.060540, 0.043708, 0.016609, 0.014493, 0.047764, 0.046030]
worker extend seconds: [3.320907, 3.646639, 2.169276, 1.897046, 3.247097, 2.928621]
gpu ids:               [0, 1, 0, 1, 0, 1]
cpu ranges:            [0-2, 3-5, 6-8, 9-11, 12-14, 15-17]
```

For the simpler near-best row:

```text
FASIM_EXTEND_THREADS=6
workers=4
worker seconds:        [2.867, 2.572, 2.479, 2.803]
worker records:        [127, 300, 197, 302]
worker preAlign total: [0.058225, 0.059952, 0.049229, 0.041101]
worker extend seconds: [3.661455, 3.573057, 3.395583, 4.221223]
gpu ids:               [0, 1, 0, 1]
cpu ranges:            [0-2, 3-5, 6-8, 9-11]
```

The summed preAlign CUDA time stays near 0.20s in the sharded runs, while summed
extension time is 7-17s depending on the thread and worker configuration. This
is the key telemetry result: current-base preAlign CUDA is short and bursty;
CPU extension is the dominant measured phase for this workload.

## Phase 2: TOPK / MAX_TASKS Probe

Phase 2 used `FASIM_EXTEND_THREADS=6` and `workers=4`. All rows were digest
clean and had zero preAlign fallbacks.

| topK | max tasks | wall s | single s | records | GPU avg | GPU max | preAlign total s | extend s | wall delta vs 64/4096 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4096 | 3.012 | 5.897 | 926 | 2.587% | 18% | 0.239941 | 14.838433 | 0.0% |
| 128 | 4096 | 3.451 | 6.591 | 1206 | 2.304% | 15% | 0.245288 | 22.570408 | +14.6% |
| 256 | 4096 | 3.638 | 6.908 | 1311 | 2.528% | 17% | 0.253547 | 26.434064 | +20.8% |
| 64 | 8192 | 3.018 | 5.887 | 926 | 2.433% | 18% | 0.199343 | 14.826355 | +0.2% |

Increasing `FASIM_PREALIGN_CUDA_TOPK` to 128 or 256 increased record count and
CPU extension work, and wall time worsened even though digest validation still
passed. Raising `FASIM_PREALIGN_CUDA_MAX_TASKS` from 4096 to 8192 did not
materially improve this workload.

## Interpretation

Low average GPU utilization is expected for this current base. The GPU lane is
a short preAlign CUDA burst, not the whole Fasim pipeline. In these runs:

```text
preAlign CUDA total: roughly 0.20s sharded sum
CPU extension:       7-17s sharded sum
GPU avg:             1.6-2.7%
GPU max:             12-20%
```

Wall time still improves when the CPU-side work is spread across more extension
threads and worker processes. That makes wall time, digest, records, and phase
telemetry more useful decision signals than GPU average utilization alone.

The TOPK probe also shows why increasing GPU-side candidate breadth is not
automatically a win: higher TOPK produced more records and more CPU extension
work, which increased wall time.

## Current Local Candidate

For this 2x4090 / i9-10900X host and this 8-contig workload:

```text
fastest measured:
  FASIM_EXTEND_THREADS=6
  workers=6
  wall=2.805s

practical near-best:
  FASIM_EXTEND_THREADS=6
  workers=4
  wall=2.867s
```

Use `workers=4` as the simpler local candidate when fewer processes are
preferred, and use `workers=6` when the workload has enough shards and the
extra worker pressure is acceptable. Do not promote either value to a global
default from this single workload.

Keep the current/default preAlign settings for this workload:

```text
FASIM_PREALIGN_CUDA_TOPK=64
FASIM_PREALIGN_CUDA_MAX_TASKS=4096
```

The recommended command shape for the practical candidate is:

```bash
env -u FASIM_CUDA_DEVICES \
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
  --cpu-cores-per-worker 3 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=6
```

Keep `--validate-single` in characterization runs.

## Decision

- Current-base GPU average utilization remains low because preAlign CUDA is a
  short burst and CPU extension dominates the measured phase totals.
- The next tuning surface is worker density, `FASIM_EXTEND_THREADS`, and CPU
  affinity, not single-process multi-GPU.
- For this host/workload, `FASIM_EXTEND_THREADS=6` with 4-6 workers is the local
  tuning range.
- Increasing TOPK above 64 worsened wall time by increasing record and extension
  work.
- Increasing max tasks to 8192 did not materially improve wall time.
- No default policy changes should be made from this PR.
