# Fasim Current-Base Forward Score GPU Shadow

This note documents the default-off forward score/end GPU shadow for the
current clean Fasim base.

## Scope

The active current-base GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
```

That path performs preAlign CUDA burst work before CPU extension. This PR adds
a separate diagnostic shadow:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1
```

The shadow does not change runtime semantics. CPU `aligner.Align()` remains the
authority for score, endpoint, traceback, CIGAR, candidate state, output, and
digest. The GPU result is only compared against the CPU forward score/end
result and reported through `benchmark.fasim_align_forward_score_gpu_*`
telemetry.

This is not a real optimization path and it is not a replacement for
`ssw_align()`. The first implementation intentionally runs a simple score/end
CUDA probe per forward-score request so the report can expose staging, launch,
kernel, and D2H costs before any batched bridge is considered.

## Telemetry

The Fasim process emits these fields on stderr:

| field | meaning |
|---|---|
| `benchmark.fasim_align_forward_score_gpu_shadow_enabled` | `1` when `FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1`, otherwise `0`. |
| `benchmark.fasim_align_forward_score_gpu_requests` | Forward score/end requests observed by the shadow. |
| `benchmark.fasim_align_forward_score_gpu_cells` | Sum of query length times target length for shadowed requests. |
| `benchmark.fasim_align_forward_score_gpu_cpu_seconds` | CPU authority forward score/end seconds for the same requests. |
| `benchmark.fasim_align_forward_score_gpu_pack_seconds` | Host-side request packing seconds. Current translated buffers are already contiguous, so this is expected to be tiny. |
| `benchmark.fasim_align_forward_score_gpu_h2d_seconds` | Host-to-device copy seconds. |
| `benchmark.fasim_align_forward_score_gpu_kernel_seconds` | CUDA event kernel seconds. |
| `benchmark.fasim_align_forward_score_gpu_d2h_seconds` | Device-to-host copy seconds. |
| `benchmark.fasim_align_forward_score_gpu_unpack_seconds` | Result comparison/unpack seconds. |
| `benchmark.fasim_align_forward_score_gpu_total_seconds` | End-to-end GPU shadow call seconds, including allocation/copies/kernel/readback. |
| `benchmark.fasim_align_forward_score_gpu_score_mismatches` | GPU score mismatches versus the CPU authority result. |
| `benchmark.fasim_align_forward_score_gpu_endpoint_mismatches` | GPU best end-position mismatches versus the CPU authority result. Endpoint mismatches are diagnostic only. |
| `benchmark.fasim_align_forward_score_gpu_unsupported_requests` | Requests the shadow could not run, for example missing CUDA support or unsupported dimensions. |

The sharded runner parser aggregates these fields into `per_shard`,
`per_worker`, `sharded_telemetry`, and `single_run.telemetry`.

## Smoke Signal

The smoke check runs the same small fixture with and without the shadow:

```bash
make check-fasim-forward-score-gpu-shadow
```

Observed local smoke signal after the first implementation:

```text
requests: 165
cells: 31,446,596
score mismatches: 0
endpoint mismatches: 0
unsupported requests: 0
CPU forward score/end seconds: ~0.005s
GPU shadow total seconds: ~3.1s
```

This result is expected for the first probe. It shows the score/end CUDA shadow
can match the CPU authority on the small fixture, but the per-request GPU path
is far slower after allocation, H2D, launch, kernel, and D2H overhead. It should
not be used as a performance mode.

## Decision Use

Use this telemetry to decide whether a future batched score-only bridge is worth
designing.

Continue only if real-workload characterization shows:

```text
score_mismatches = 0
digest unchanged
unsupported_requests = 0 or explainable
projected batched GPU total < CPU forward score/end time
```

Stop or redesign if:

```text
score mismatches appear
GPU total remains slower after batching/staging costs
endpoint mismatches are needed for any proposed real output path
```

Do not use this shadow to justify:

```text
GPU endpoint authority
GPU CIGAR
GPU traceback
GPU full extension replacement
Accelign or Parasail real output authority
single-process multi-GPU policy
historical final speed-stack env claims
```

