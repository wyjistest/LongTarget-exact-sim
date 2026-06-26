# Fasim GASAL2 Two-Slot Multi-Worker 2-GPU Characterization

## Scope

This artifact is only for the default-off bounded two-slot overlap path:

```text
scope = normal-triplex lite
default_policy = default_off
GPU model = process-level sharding, one visible GPU per worker
```

It does not expand support to direct-lite, archive-first, phase3 side effects,
taxonomy exporters, async archive writing, or in-process multi-GPU execution.

## Matrix

Default command:

```bash
make characterize-fasim-gasal2-flush-two-slot-multi-worker-2gpu
```

The wrapper generates a scoped multi-contig input from:

```text
chr17,chr18,chr19,chr20,chr21,chr22
```

By default it truncates each contig to 8 Mb. This keeps six material shards for
the 1/2/4/6 worker resource matrix while avoiding multi-hour canonicalization
of full per-contig lite outputs. Set `--limit-bases-per-contig 0` on the Python
wrapper to run full contigs.

and runs:

```text
workers: 1,2,4,6
GPU ids: 0,1
mode:    synchronous extracted finalizer
mode:    two-slot overlap
```

Each worker receives a single visible GPU through `CUDA_VISIBLE_DEVICES` via
the existing sharded runner. For `workers > GPUs`, multiple worker processes
share each physical GPU; this is intentional for resource-contention
characterization.

## Artifacts

Default output:

```text
.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v1
```

Important files:

```text
runs.tsv
topk_compare.tsv
determinism.tsv
summary.json
summary.txt
*/resource_samples.json
```

`runs.tsv` includes per-worker wall, worker/GPU assignment, merged digest,
top5 output digests, two-slot lifecycle counters, slot occupancy, host
scheduling overlap, runtime memory counters, sampled process-tree RSS, and
sampled `nvidia-smi` compute-app memory.

Independent full runs can have the already-observed 1-2 row nondeterminism.
The checker therefore treats top5 equality as the hard cross-mode correctness
gate and uses repeated runs to decide whether two-slot expands row-set
variability. Cross-mode merged digest equality, missing rows and extra rows are
reported, not used as a single-run hard failure.

Runtime telemetry still does not measure device-level CUDA overlap:

```text
runtime_device_overlap_supported = false
host_scheduling_overlap_available = true
```

Nsight evidence from the single-worker chr22 matrix remains the device-level
ground truth for overlap attribution.

## Gate

Strong go for multi-worker resource behavior requires:

```text
at least two worker counts > 1 with median improvement >= 5%
no OOM or allocation failures
no fallback, order violation, state-transition violation
submitted = finalized = committed for every two-slot run
top5 score/stability/Nt-score clean
row-set variability not expanded relative to the scoped baseline
```

If this gate passes, the recommendation can be written as:

```text
normal-triplex lite workloads:
  FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1
  default-off recommended candidate
```

If worker contention erodes the benefit, keep the recommendation scoped to
single-worker or low-density GPU execution.

## Scoped Result

Artifact:

```text
.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v4
```

Input:

```text
chr17-22, 8 Mb per contig
records = 6
bases   = 48,000,000
sha256  = 5db0d05d3ecb97f6f97b2ed7035cb5afa9debff667b381de015b53f2fe8850d4
```

Completed configurations:

```text
workers=1:
  sync extracted wall = 59.39 s
  two-slot wall       = 53.51 s
  reduction           = 5.88 s / 9.90%
  host overlap        = 9.00 s
  peak sampled RSS    = 1.35 GB
  peak GPU memory     = 19.75 GB

workers=2, GPUs=0,1:
  sync extracted wall = 34.73 s
  two-slot wall       = 31.01 s
  reduction           = 3.72 s / 10.71%
  host overlap        = 9.10 s
  peak sampled RSS    = 2.12 GB
  peak GPU memory     = 39.49 GB aggregate
```

Correctness gates for completed configurations:

```text
merged digest equal = true
top5 score equal = true
top5 stability equal = true
top5 Nt-score equal = true
missing / extra rows = 0 / 0
state/order/fallback/allocation violations = 0
```

High-density configurations failed before a two-slot-specific conclusion:

```text
workers=4: GASAL2 CUDA OOM in synchronous extracted and two-slot modes
workers=6: GASAL2 CUDA OOM in synchronous extracted and two-slot modes
```

The OOM is therefore a per-GPU worker-density/resource-budget limit, not a
two-slot-only regression.

Decision:

```text
two-slot multi-worker resource behavior = scoped-go
recommended scope = single worker or one worker per GPU
not recommended for multiple GASAL2 workers per 24 GB GPU with this batch/stream profile
```

## Runner Guardrail

The sharded runner now encodes this policy:

```text
FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1
worker_count > len(gpu_ids)
→ fail closed before shard execution
→ disabled_reason = unsupported_worker_density_for_current_gasal2_memory_budget
```

Use this override only for explicit resource-characterization experiments:

```text
FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING=1
```

Focused check:

```bash
make check-fasim-gasal2-two-slot-low-density-guard
```
