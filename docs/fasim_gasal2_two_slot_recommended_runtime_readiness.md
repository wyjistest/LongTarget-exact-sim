# Fasim GASAL2 Two-Slot Recommended Runtime Readiness

## Decision

```text
decision = default-off recommended candidate
scope    = normal-triplex lite
runtime  = FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1
density  = single worker or one worker per GPU
```

This closes the bounded two-slot overlap line as a recommended low-density
optimization, not as a default-on policy.

## Evidence

Single-worker chr21/chr22 broader matrix:

```text
chr21_full:
  sync extracted median = 62.4632 s
  two-slot median       = 54.3438 s
  reduction             = 12.9986%

chr22_full:
  sync extracted median = 61.7299 s
  two-slot median       = 53.7131 s
  reduction             = 12.9868%

strong_go_workloads = 2
```

Nsight Systems device-level attribution on `chr22_full`:

```text
CPU finalizer / CUDA activity overlap = 4.8484 s
CPU finalizer / kernel overlap        = 4.6668 s
CPU finalizer / memcpy overlap        = 0.1817 s
```

Runtime telemetry and profiler evidence remain separate:

```text
runtime_device_overlap_supported = false
host_scheduling_overlap_available = true
device_overlap_measurement = nsight
```

Multi-worker 2-GPU scoped resource characterization:

```text
workers=1:
  sync extracted wall = 59.39 s
  two-slot wall       = 53.51 s
  reduction           = 9.90%

workers=2, GPUs=0,1:
  sync extracted wall = 34.73 s
  two-slot wall       = 31.01 s
  reduction           = 10.71%

workers=4 and workers=6:
  synchronous extracted already GASAL2 CUDA OOM
  two-slot also OOM
```

This makes high worker density a GASAL2 memory-budget no-go before any
two-slot-specific conclusion.

## Guardrail

The sharded runner enforces the measured resource boundary:

```text
FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1
worker_count > len(gpu_ids)
→ fail closed before shard execution
→ disabled_reason = unsupported_worker_density_for_current_gasal2_memory_budget
```

The guard state is recorded as:

```text
two_slot_low_density_guard
```

and included in `run_config_digest`.

Only explicit resource-characterization experiments should override it:

```text
FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING=1
```

## Supported Invocation

Single worker:

```bash
FASIM_OUTPUT_MODE=lite \
FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
FASIM_ALIGN_GASAL2_STREAMS=3 \
FASIM_ALIGN_GASAL2_BATCH=20000 \
FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1 \
./fasim_longtarget_gasal2 -f1 target.fa -f2 H19.fa -r 0 -O out
```

Process-level 2-GPU sharding:

```bash
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_gasal2 \
  --target targets.fa \
  --rna H19.fa \
  --rule 0 \
  --work-dir .tmp/fasim_two_slot \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 0,1 \
  --env FASIM_OUTPUT_MODE=lite \
  --env FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  --env FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  --env FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  --env FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
  --env FASIM_ALIGN_GASAL2_STREAMS=3 \
  --env FASIM_ALIGN_GASAL2_BATCH=20000 \
  --env FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1
```

## Out Of Scope

```text
default-on policy
direct-lite finalizer shape
archive-first finalizer shape
phase3 side effects
taxonomy / eligibility exporters
async archive writer
multiple CPU finalizer workers
unbounded queues
multiple GASAL2 workers per 24 GB GPU at the current batch/stream profile
```

Direct-lite and archive-first should each get their own payload/finalizer/commit
boundary before any overlap work.

## Checks

Static/readiness:

```bash
make check-fasim-gasal2-two-slot-recommended-runtime-readiness
```

Focused guardrail:

```bash
make check-fasim-gasal2-two-slot-low-density-guard
```

Long benchmark artifacts:

```text
.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix_v2
.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v4
```

## Next Work

Do not keep expanding this two-slot line before a new problem statement. The
next higher-upside directions are:

```text
traceback / exact-column kernel optimization
GASAL2 memory footprint reduction
direct-lite or archive-first payload/finalizer/commit boundaries
```
