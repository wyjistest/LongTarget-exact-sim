# Fasim PreAlign CUDA Shared-Memory Opt-In Probe

This note follows the resource-fit checkpoint by checking whether the observed
49 KB preAlign CUDA launch limit is the default dynamic shared-memory limit or a
hard per-block limit.

## Scope

This is a telemetry/script/result checkpoint:

- No default preAlign behavior is changed.
- No output, scoring, threshold, endpoint, CIGAR, traceback, merge semantics,
  scheduler default, chunking, overlap, or in-process multi-GPU behavior is
  changed.
- CPU fallback and CPU Fasim output remain authoritative.
- `FASIM_PREALIGN_CUDA_SMEM_OPTIN=1` is default-off and used only for this
  resource probe.
- `--group-target-records` remains default-off.

## Telemetry

This PR extends the preAlign CUDA resource telemetry:

```text
benchmark.fasim_prealign_cuda_shared_mem_default_limit
benchmark.fasim_prealign_cuda_shared_mem_optin_limit
benchmark.fasim_prealign_cuda_smem_optin_possible
benchmark.fasim_prealign_cuda_smem_optin_requested
benchmark.fasim_prealign_cuda_smem_optin_active
benchmark.fasim_prealign_cuda_smem_optin_fallback_reason
```

The opt-in path is only attempted when:

```text
required_smem > default_limit
required_smem <= optin_limit
FASIM_PREALIGN_CUDA_SMEM_OPTIN=1
```

Otherwise the current CPU fallback behavior remains unchanged.

## Commands

MALAT1 first8 default, no opt-in baseline:

```bash
timeout 120s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_smem_optin_malat1_default_w4_nooptin \
  --output-mode lite \
  --group-target-records none \
  --workers 4 \
  --topk-values 64 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --workload MALAT1_first8:.tmp/fasim_prealign_cuda_smem_optin_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0
```

MALAT1 first8 default, opt-in probe:

```bash
timeout 300s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_smem_optin_malat1_default_w4 \
  --output-mode lite \
  --group-target-records none \
  --workers 4 \
  --topk-values 64,32,16 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --env FASIM_PREALIGN_CUDA_SMEM_OPTIN=1 \
  --workload MALAT1_first8:.tmp/fasim_prealign_cuda_smem_optin_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0
```

NEAT1 first64 group=16, opt-in probe:

```bash
timeout 180s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_smem_optin_neat1_group16_w4 \
  --output-mode lite \
  --group-target-records 16 \
  --workers 4 \
  --topk-values 64 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --env FASIM_PREALIGN_CUDA_SMEM_OPTIN=1 \
  --workload NEAT1_first64:.tmp/fasim_prealign_cuda_smem_optin_inputs/NEAT1_DNAseq_first64.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa:0
```

MEG3 fallback-clean control:

```bash
timeout 120s python3 scripts/benchmark_fasim_prealign_cuda_resource_fit.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_prealign_cuda_smem_optin_meg3_group32_w4 \
  --output-mode lite \
  --group-target-records 32 \
  --workers 4 \
  --topk-values 64 \
  --max-tasks-values 4096 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --env FASIM_PREALIGN_CUDA_SMEM_OPTIN=1 \
  --workload MEG3_full:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0
```

## Results

### MALAT1 First8

The 49 KB limit is the default dynamic shared-memory limit. The device reports
an opt-in limit of 101,376 bytes, and MALAT1's current topK launch can use it.
However, enabling the current preAlign CUDA topK path changes output relative
to the CPU fallback authority.

| mode | topK | wall s | digest vs single | digest vs CPU fallback | records | fallbacks | tasks | required smem | default limit | opt-in limit | opt-in active |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| no opt-in | 64 | 10.084 | clean | clean | 796 | 8 | 0 | 52,928 | 49,152 | 101,376 | 0 |
| opt-in | 64 | 3.375 | clean | mismatch | 564 | 0 | 1,824 | 52,928 | 49,152 | 101,376 | 1 |
| opt-in | 32 | 2.903 | clean | mismatch | 365 | 0 | 1,824 | 52,672 | 49,152 | 101,376 | 1 |
| opt-in | 16 | 2.551 | clean | mismatch | 241 | 0 | 1,824 | 52,544 | 49,152 | 101,376 | 1 |

The single-run digest is clean within each mode because the runner validates
the same mode against itself. The important authority comparison is against the
CPU fallback baseline, where the opt-in CUDA rows change records and digest.

### NEAT1 First64, Group 16

NEAT1 remains above the opt-in limit:

| mode | topK | wall s | digest | records | fallbacks | required smem | default limit | opt-in limit | opt-in active | reason |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| opt-in | 64 | 21.167 | clean | 2,838 | 4 | 137,216 | 49,152 | 101,376 | 0 | required_exceeds_optin_limit |

### MEG3 Full, Group 32

MEG3 remains the fallback-clean control:

| mode | topK | wall s | digest | records | fallbacks | required smem | default limit | opt-in possible | opt-in active |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| opt-in env set | 64 | 11.457 | clean | 4,914 | 0 | 10,112 | 49,152 | 0 | 0 |

## Decision

The 49 KB value is a default dynamic shared-memory launch limit, not the
device's opt-in per-block limit.

That does not make the current preAlign CUDA topK path a real candidate for
MALAT1:

```text
MALAT1:
  opt-in launch works
  fallback goes to 0
  digest/records differ from CPU fallback authority
  no real opt-in

NEAT1:
  required smem exceeds opt-in limit
  CPU fallback remains expected

MEG3:
  already resource-fit clean
```

Current conclusion:

```text
Do not enable FASIM_PREALIGN_CUDA_SMEM_OPTIN as a runtime recommendation.
Keep CPU fallback as authority for MALAT1/NEAT1-like workloads.
Do not pursue TOPK/MAX_TASKS tuning for this resource boundary.
```

Future CUDA work would need a separate equivalence-first design, such as a
lower-shared-memory topK kernel or a candidate-generation path that reproduces
CPU fallback output before making any performance claim.
