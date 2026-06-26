# Fasim GASAL2 NVTX Ground-Truth Scaffold

## Scope

This checkpoint adds default-off NVTX host ranges for Nsight Systems ground
truth. It does not change scheduling, buffering, GASAL2 execution, exact-column
logic, traceback, conversion, archive writing, sorting, or output semantics.

The runtime switch is:

```bash
FASIM_GASAL2_NVTX_TRACE=1
```

NVTX support is compile-time opt-in. The default GASAL2 build remains unchanged.
Use:

```bash
make build-fasim-gasal2-nvtx
```

or:

```bash
make check-fasim-gasal2-nvtx-trace-smoke
```

## Ranges

The first scaffold emits host-envelope ranges:

```text
fasim.gasal2.flush
fasim.gasal2.pack
fasim.gasal2.score_traceback
fasim.gasal2.convert
fasim.gasal2.archive_write   # direct archive-convert path only
```

The two-slot path additionally emits:

```text
fasim.gasal2.two_slot.submit_result
fasim.gasal2.two_slot.cpu_finalizer
fasim.gasal2.two_slot.ordered_commit
fasim.gasal2.two_slot.slot_lifetime
fasim.gasal2.two_slot.drain
```

These ranges are intended to be aligned against Nsight Systems CUDA kernel,
memcpy and CPU-thread lanes. They do not add `cudaDeviceSynchronize()` and do
not attempt to replace the existing CUDA-event and flush wait-state telemetry.

Exact-column is not yet emitted as a separate NVTX host range because the
current timing is aggregated from deeper GPU scoreInfo paths rather than one
single local code block. For now, use existing exact-column telemetry and the
Nsight CUDA kernel lane to interpret that stage.

On the chr22 full-plain profile below, the active ranges were:

```text
fasim.gasal2.flush
fasim.gasal2.pack
fasim.gasal2.score_traceback
fasim.gasal2.convert
```

The direct `archive_write` range did not appear in that run because this
particular output path did not use the direct archive-convert branch.

## Runtime Metrics

When requested, stderr reports:

```text
benchmark.fasim_gasal2_nvtx_trace_requested
benchmark.fasim_gasal2_nvtx_trace_compiled
benchmark.fasim_gasal2_nvtx_trace_active
benchmark.fasim_gasal2_nvtx_trace_ranges
benchmark.fasim_gasal2_nvtx_trace_decision
```

Expected active decision:

```text
nvtx_ranges_emitted_for_nsight
```

If `FASIM_GASAL2_NVTX_TRACE=1` is set on a binary compiled without
`FASIM_WITH_NVTX`, the decision is:

```text
not_compiled
```

## Nsight Command

A chr22 full-plain profile should be run with the NVTX binary, for example:

```bash
mkdir -p .tmp/nsys_fasim_gasal2_chr22_nvtx/out
nsys profile \
  --trace=cuda,nvtx,osrt \
  --sample=none \
  --force-overwrite=true \
  --output=.tmp/nsys_fasim_gasal2_chr22_nvtx \
  env FASIM_GASAL2_NVTX_TRACE=1 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
      FASIM_ALIGN_GASAL2_STREAMS=3 \
      FASIM_ALIGN_GASAL2_BATCH=20000 \
      FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
      .tmp/fasim_longtarget_gasal2_nvtx \
      -f1 .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
      -f2 H19.fa \
      -r 0 \
      -O .tmp/nsys_fasim_gasal2_chr22_nvtx/out
```

A two-slot ground-truth profile should use the same binary and add the two-slot
runtime switch:

```bash
mkdir -p .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/out
nsys profile \
  --trace=cuda,nvtx,osrt \
  --sample=none \
  --force-overwrite=true \
  --output=.tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/profile \
  env FASIM_GASAL2_NVTX_TRACE=1 \
      FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1 \
      FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
      FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
      FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
      FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
      FASIM_ALIGN_GASAL2_STREAMS=3 \
      FASIM_ALIGN_GASAL2_BATCH=20000 \
      .tmp/fasim_longtarget_gasal2_nvtx \
      -f1 .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
      -f2 H19.fa \
      -r 0 \
      -O .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/out
```

The target question for this run is whether CUDA kernels or memcpy work for
flush N+1 overlap the `fasim.gasal2.two_slot.cpu_finalizer` range for flush N.

After export, summarize interval overlap with:

```bash
nsys export \
  --type sqlite \
  --force-overwrite=true \
  --output .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/profile.sqlite \
  .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/profile.nsys-rep

python3 scripts/summarize_fasim_gasal2_nvtx_overlap.py \
  .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/profile.sqlite \
  --output .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx/overlap_summary.txt
```

## Decision Boundary

This checkpoint makes Nsight correlation possible. The first chr22 profile also
provides a material ground-truth result:

```text
profile = .tmp/nsys_fasim_gasal2_chr22_nvtx/profile.nsys-rep
sqlite  = .tmp/nsys_fasim_gasal2_chr22_nvtx/profile.sqlite

program wall clock = 71.2345 s
flush_total        = 64.0194 s
GASAL2 extend      = 39.5627 s
exact-column       = 11.6029 s
convert            = 15.8194 s
output write       =  1.5342 s

NVTX ranges emitted = 376
```

Nsight NVTX summary:

```text
range                         instances   total
fasim.gasal2.flush                  94    64.0204 s
fasim.gasal2.score_traceback        94    20.6548 s
fasim.gasal2.convert                94    15.8196 s
fasim.gasal2.pack                   94     1.0176 s
```

CUDA summary:

```text
GPU kernels total        = 51.9895 s
GPU memcpy total         =  2.8199 s
cudaEventSynchronize API = 16.6684 s
```

NVTX/GPU overlap from the exported SQLite:

```text
range                         range s    GPU overlap s
fasim.gasal2.flush            64.0204       54.8094
fasim.gasal2.score_traceback  20.6548       37.0334
fasim.gasal2.convert          15.8196        0.0000
fasim.gasal2.pack              1.0176        0.0000
```

This means the current path is still effectively serial at the flush boundary:
the CPU convert phase is not overlapped with GPU kernel or memcpy work in the
chr22 profile.

This checkpoint still does not prove:

```text
convert backpressure
archive writer backpressure
double-buffer readiness
```

Those require a two-slot prototype and comparison against the full-run
determinism oracle.

Two-slot performance characterization later showed a strong host-side result:

```text
sync extracted      61.23 s
serialized control  65.88 s
two-slot overlap    53.12 s
```

That supports a real scheduling benefit, but runtime telemetry only measures
host scheduling overlap. Device-level GPU/CPU overlap remains pending until the
two-slot Nsight profile above is captured.

A two-slot chr22 NVTX/Nsight profile captured on this checkpoint produced:

```text
profile = .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx_attribution/profile.nsys-rep
sqlite  = .tmp/nsys_fasim_gasal2_chr22_two_slot_nvtx_attribution/profile.sqlite

flush_total              = 48.4408 s
GASAL2 extend            = 25.3134 s
exact-column             = 11.6057 s
output write             =  0.5893 s
NVTX ranges emitted      = 753

two-slot submitted/finalized/committed = 94/94/94
host scheduling overlap                = 10.8276 s
runtime device-overlap telemetry       = unavailable
```

Nsight device-activity summary from the exported SQLite:

```text
GPU kernel union seconds       = 32.1764
GPU memcpy union seconds       =  2.8099
GPU activity union seconds     = 34.1521

two_slot.cpu_finalizer ranges  = 94
two_slot.cpu_finalizer seconds = 10.9383
cpu_finalizer/GPU activity overlap = 4.8569 s
cpu_finalizer/kernel overlap       = 4.6736 s
cpu_finalizer/memcpy overlap       = 0.1833 s
cpu_finalizer device-overlap fraction = 0.4440
```

This confirms real device-level overlap, but it is smaller than the host
scheduling overlap. The careful wording is:

```text
The two-slot path created 10.83 s of host scheduling overlap on this chr22
profile; Nsight confirms 4.86 s of that finalizer interval overlapped CUDA
kernel or memcpy activity.
```

Next decision gate:

```text
Broaden characterization to additional material workloads while keeping
host_scheduling_overlap_seconds and Nsight device-overlap metrics separate.
```
