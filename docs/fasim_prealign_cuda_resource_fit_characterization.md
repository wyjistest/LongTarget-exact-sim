# Fasim PreAlign CUDA Resource-Fit Characterization

This note follows the fallback taxonomy checkpoint by measuring whether the
`cuda_allocation_or_launch` fallbacks in NEAT1/MALAT1 are avoidable with current
resource-fit launch settings.

## Scope

This is a telemetry/script/result checkpoint:

- No default preAlign behavior is changed.
- No output, scoring, threshold, endpoint, CIGAR, traceback, merge semantics,
  scheduler default, chunking, overlap, or in-process multi-GPU behavior is
  changed.
- CPU fallback and CPU Fasim output remain authoritative.
- `FASIM_PREALIGN_CUDA_TOPK` and `FASIM_PREALIGN_CUDA_MAX_TASKS` are only swept
  by the characterization script.
- `--group-target-records` remains default-off.

## Telemetry

This PR adds resource telemetry for the current preAlign CUDA topK launch:

```text
benchmark.fasim_prealign_cuda_dynamic_smem_required
benchmark.fasim_prealign_cuda_dynamic_smem_limit
benchmark.fasim_prealign_cuda_device_shared_mem_limit
benchmark.fasim_prealign_cuda_block_dim
benchmark.fasim_prealign_cuda_resource_fit_supported
```

The values are recorded for both successful CUDA batches and resource preflight
fallbacks. Sharded runner aggregation reports the maximum observed shared-memory
requirement/limit/block dimension and an all-fit `resource_fit_supported` flag.

## Script

`scripts/benchmark_fasim_prealign_cuda_resource_fit.py` runs the real sharded
runner and writes:

```text
report.json
raw.tsv
```

It collects digest equivalence, fallback reason counts, CUDA task/batch counts,
effective topK/max-tasks settings, resource-fit telemetry, and profile-cache hit
rate. Each non-baseline row also compares its merged digest against the first
topK/max-tasks row for the same workload/group/worker shape.

## Commands

The runs used:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_VERBOSE=0
```

MALAT1 first8:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=8{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa \
  > .tmp/fasim_prealign_cuda_resource_fit_inputs/MALAT1_DNAseq_first8.fa

timeout 300s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_resource_fit_malat1_default_w4 \
  --output-mode lite \
  --group-target-records none \
  --workers 4 \
  --topk-values 64,32,16 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MALAT1_first8:.tmp/fasim_prealign_cuda_resource_fit_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0
```

NEAT1 first64, grouped to keep the run bounded:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=64{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa \
  > .tmp/fasim_prealign_cuda_resource_fit_inputs/NEAT1_DNAseq_first64.fa

timeout 300s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_resource_fit_neat1_group16_w4 \
  --output-mode lite \
  --group-target-records 16 \
  --workers 4 \
  --topk-values 64,32,16 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload NEAT1_first64:.tmp/fasim_prealign_cuda_resource_fit_inputs/NEAT1_DNAseq_first64.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa:0
```

MEG3 fallback-clean control:

```bash
timeout 180s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_resource_fit_meg3_group32_w4 \
  --output-mode lite \
  --group-target-records 32 \
  --workers 4 \
  --topk-values 64 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MEG3_full:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0
```

## Results

All rows were digest-clean against their single-run reference and against the
baseline topK/max-tasks row for the same workload/group/worker shape.

### NEAT1 First64, Group 16, Workers 4

| topK | max tasks | wall s | digest | baseline digest | fallbacks | reason | tasks | required smem | limit | fit |
|---:|---:|---:|---|---|---:|---|---:|---:|---:|---:|
| 64 | 4096 | 21.229 | clean | clean | 4 | cuda_allocation_or_launch | 0 | 137,216 | 49,152 | 0 |
| 32 | 4096 | 21.744 | clean | clean | 4 | cuda_allocation_or_launch | 0 | 136,960 | 49,152 | 0 |
| 16 | 4096 | 21.291 | clean | clean | 4 | cuda_allocation_or_launch | 0 | 136,832 | 49,152 | 0 |

### MALAT1 First8, Default Grouping, Workers 4

| topK | max tasks | wall s | digest | baseline digest | fallbacks | reason | tasks | required smem | limit | fit |
|---:|---:|---:|---|---|---:|---|---:|---:|---:|---:|
| 64 | 4096 | 7.826 | clean | clean | 8 | cuda_allocation_or_launch | 0 | 52,928 | 49,152 | 0 |
| 32 | 4096 | 7.824 | clean | clean | 8 | cuda_allocation_or_launch | 0 | 52,672 | 49,152 | 0 |
| 16 | 4096 | 7.805 | clean | clean | 8 | cuda_allocation_or_launch | 0 | 52,544 | 49,152 | 0 |

### MEG3 Full, Group 32, Workers 4

| topK | max tasks | wall s | digest | fallbacks | tasks | batches | required smem | limit | fit | preAlign total s |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | 4096 | 9.979 | clean | 0 | 25,536 | 522 | 10,112 | 49,152 | 1 | 2.342 |

## Decision

The NEAT1/MALAT1 sampled fallbacks are explained by the current topK kernel's
dynamic shared-memory shape:

```text
NEAT1 first64 group=16:
  required smem ~= 137 KB
  block limit    = 49 KB

MALAT1 first8:
  required smem ~= 52.5 KB
  block limit    = 49 KB
```

Lowering topK from 64 to 16 does not eliminate fallback for either workload.
This is expected because most of the requirement comes from the query/profile
term, not the topK heap term. Changing `FASIM_PREALIGN_CUDA_MAX_TASKS` would not
change this per-block dynamic shared-memory requirement for the current kernel.

Current conclusion:

```text
NEAT1/MALAT1:
  CPU fallback remains the correct path.
  Do not claim preAlign CUDA fast-path coverage.
  Do not add a resource-fit real opt-in based on topK/max-tasks downshift.

MEG3:
  resource-fit clean.
  --group-target-records 32 remains a good tiny-region workload shape.
```

Future work should only continue if it changes the CUDA execution design, for
example a lower-shared-memory topK kernel layout. That should start as a
default-off diagnostic/shadow path and must prove digest equivalence before any
runtime recommendation changes.
