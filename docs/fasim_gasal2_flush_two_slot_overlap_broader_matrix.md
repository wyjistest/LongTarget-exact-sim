# Fasim GASAL2 Two-Slot Broader Matrix

## Scope

This result records schema v2 broader characterization for the default-off
bounded two-slot overlap path. Runtime telemetry and external profiler evidence
remain separate:

```text
runtime_device_overlap_supported=false
host_scheduling_overlap_available=true
device_overlap_measurement=nsight
```

## Workloads

```text
chr21_full = .tmp/gasal2_hg38_archive_first_rule0_run/shards/chr21.fa
chr22_full = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
```

Each workload ran:

```text
synchronous extracted finalizer: 3 runs
two-slot serialized control:    3 runs
two-slot overlap:               3 runs
two-slot validate audit:        1 run
```

`chr22_full` additionally ran one NVTX/Nsight two-slot profile.

## Result

Artifact:

```text
.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix_v2
```

Summary:

```text
chr21_full:
  sync extracted median    = 62.4632 s
  serialized control median = 66.9649 s
  two-slot median          = 54.3438 s
  reduction vs extracted   = 8.1194 s / 12.9986%
  reduction vs serialized  = 12.6211 s / 18.8473%
  host scheduling overlap  = 10.2344 s
  top5 clean               = true

chr22_full:
  sync extracted median    = 61.7299 s
  serialized control median = 65.7023 s
  two-slot median          = 53.7131 s
  reduction vs extracted   = 8.0168 s / 12.9868%
  reduction vs serialized  = 11.9892 s / 18.2478%
  host scheduling overlap  = 10.5932 s
  top5 clean               = true
```

Nsight on `chr22_full`:

```text
CPU finalizer / CUDA activity overlap = 4.8484 s
CPU finalizer / kernel overlap        = 4.6668 s
CPU finalizer / memcpy overlap        = 0.1817 s
CPU finalizer device-overlap fraction = 0.4473
```

## Decision

```text
strong_go_workloads = 2
decision = broader_matrix_recorded
```

This is sufficient for a default-off recommended optimization for
normal-triplex lite workloads. It is still not a default-on policy and does not
cover direct-lite/archive-first shapes.

Next remaining characterization is multi-worker resource behavior:

```text
per-worker RSS
device memory peak
OOM/allocation fallback rate
GPU contention under 2 GPU / 4 worker scheduling
```
