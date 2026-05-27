# Fasim Current-Base Broader Workload Validation

This note validates the current clean-base recommended runtime on additional
local Fasim example workloads after the GPU score bridge line was stopped as a
performance path.

## Scope

This is a docs/result checkpoint only:

- No runtime code is changed.
- No env is added or defaulted.
- No scheduler or GPU policy is changed.
- No output, scoring, threshold, merge, chunking, endpoint, CIGAR, traceback,
  or in-process multi-GPU behavior is changed.
- GPU score bridge shadows remain diagnostic/research-only.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Runtime

The characterized runtime is the current-base recommended local candidate:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
FASIM_VERBOSE=0 \
python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest
```

Each worker process sees one logical GPU through `CUDA_VISIBLE_DEVICES` and uses
`FASIM_CUDA_DEVICE=0`. The parent environment does not set
`FASIM_CUDA_DEVICES`.

## Inputs

The matrix used local Fasim example datasets:

| workload | target scope | target records | target bases | RNA | rule |
|---|---|---:|---:|---|---:|
| MEG3 full | full local example | 532 | 1,316,004 | `MEG3-ENST00000451743.fa` | 0 |
| NEAT1 first64 | deterministic first 64 target records | 64 | 179,014 | `NEAT1.fa` | 0 |
| MALAT1 first8 | deterministic first 8 target records | 8 | 166,196 | `MALAT1.fa` | 0 |

The full NEAT1 example has 3,692 target records and the full MALAT1 example has
670 target records. A first attempt to run full MEG3, full NEAT1, and full
MALAT1 in one matrix was stopped after MEG3 completed and NEAT1 workers=1 had
processed only a small prefix of the 3,692 tiny shards. That is a workload-shape
finding: thousands of small target-region records should be characterized with
sampled/capped matrices or a different region grouping strategy before making
worker-density claims.

## Commands

MEG3 full:

```bash
timeout 3600s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_current_base_broader_validation_examples \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest \
  --workload MEG3_example:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa:0 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=6 \
  --env FASIM_ALIGN_PROFILE_CACHE=1 \
  --env FASIM_VERBOSE=0
```

NEAT1 first64 and MALAT1 first8 used deterministic FASTA prefixes:

```bash
awk 'BEGIN{n=0} /^>/{n++} n<=64{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa \
  > .tmp/fasim_current_base_broader_validation_inputs/NEAT1_DNAseq_first64.fa

awk 'BEGIN{n=0} /^>/{n++} n<=8{print}' \
  /data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa \
  > .tmp/fasim_current_base_broader_validation_inputs/MALAT1_DNAseq_first8.fa
```

```bash
timeout 1800s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_current_base_broader_validation_samples \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest \
  --workload NEAT1_first64:.tmp/fasim_current_base_broader_validation_inputs/NEAT1_DNAseq_first64.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa:0 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=6 \
  --env FASIM_ALIGN_PROFILE_CACHE=1 \
  --env FASIM_VERBOSE=0

timeout 900s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_current_base_broader_validation_malat1_first8 \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest \
  --workload MALAT1_first8:.tmp/fasim_current_base_broader_validation_inputs/MALAT1_DNAseq_first8.fa:/data/wenyujianData/LongTarget-exact-sim/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa:0 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=6 \
  --env FASIM_ALIGN_PROFILE_CACHE=1 \
  --env FASIM_VERBOSE=0
```

## Results

`wall s` is the sharded worker critical path from the runner report. `single
whole s` is the runner's validation single-process whole-input time for that
same input.

| workload | input scope | shards | bases | workers | wall s | single whole s | speedup vs single | records | digest | preAlign fallbacks | profile cache active | cache hit rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| MEG3 full | full example | 532 | 1,316,004 | 1 | 209.604 | 28.195 | 0.13x | 4,914 | clean | 0 | 1 | 99.6759% |
| MEG3 full | full example | 532 | 1,316,004 | 2 | 128.719 | 28.077 | 0.22x | 4,914 | clean | 0 | 1 | 99.6746% |
| MEG3 full | full example | 532 | 1,316,004 | 4 | 98.899 | 28.162 | 0.28x | 4,914 | clean | 0 | 1 | 99.6797% |
| NEAT1 first64 | sampled first 64 regions | 64 | 179,014 | 1 | 92.539 | 73.365 | 0.79x | 2,838 | clean | 64 | 1 | 99.9543% |
| NEAT1 first64 | sampled first 64 regions | 64 | 179,014 | 2 | 47.014 | 73.428 | 1.56x | 2,838 | clean | 64 | 1 | 99.9543% |
| NEAT1 first64 | sampled first 64 regions | 64 | 179,014 | 4 | 26.074 | 73.485 | 2.82x | 2,838 | clean | 64 | 1 | 99.9543% |
| MALAT1 first8 | sampled first 8 regions | 8 | 166,196 | 1 | 22.646 | 20.625 | 0.91x | 796 | clean | 8 | 1 | 99.9893% |
| MALAT1 first8 | sampled first 8 regions | 8 | 166,196 | 2 | 11.929 | 20.593 | 1.73x | 796 | clean | 8 | 1 | 99.9893% |
| MALAT1 first8 | sampled first 8 regions | 8 | 166,196 | 4 | 7.663 | 20.577 | 2.69x | 796 | clean | 8 | 1 | 99.9893% |

Summary:

```text
digest clean: 9/9
profile cache active: 9/9
profile cache hit rate: 99.67-99.99%
preAlign CUDA fallbacks:
  MEG3 full: 0
  NEAT1 first64: 64 per row
  MALAT1 first8: 8 per row
```

## Interpretation

This broader validation supports the current-base recommendation only as a
correctness-clean opt-in shape, not as a blanket performance claim.

Positive signals:

```text
all rows digest-clean
profile cache active on all rows
profile cache reuse remains very high across three RNA examples
NEAT1 first64 and MALAT1 first8 improve with 2/4 workers
```

Boundary signals:

```text
MEG3 full has 532 tiny target records and sharded overhead dominates;
  even workers=4 is slower than the single whole-input validation run.

NEAT1 first64 and MALAT1 first8 fall back from preAlign CUDA once per shard;
  these sampled example inputs do not provide a fallbacks=0 GPU-fast-path claim.

Full NEAT1/MALAT1 should not be characterized by blindly running thousands of
  tiny region shards through the same matrix. Use sampled/capped runs or a
  separate region-grouping/readiness design.
```

## Decision

Keep the current recommendation:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharded runner
```

But qualify it:

```text
recommended for same-query multi-target workloads with enough per-shard work;
digest-clean on the broader example smoke/sampled matrix;
not a universal speedup for thousands of tiny region shards;
preAlign CUDA fast path must be checked per workload via fallback counters.
```

Do not restart the stopped GPU score bridge, endpoint, CIGAR, traceback, or full
GPU aligner lines based on this validation.
