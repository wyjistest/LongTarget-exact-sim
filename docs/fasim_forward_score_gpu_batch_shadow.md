# Fasim Forward Score GPU Batch Shadow

This note documents the default-off batched forward score/end GPU shadow for
the current clean Fasim base.

## Scope

The active current-base GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
```

That path performs preAlign CUDA burst work before CPU extension. This PR adds
a separate diagnostic batch shadow:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1
```

The diagnostic collector keeps copied query/reference buffers until telemetry
snapshot time. To avoid unbounded memory use when the shadow is accidentally
enabled on a large workload, collection is capped at 100,000 requests by
default. The cap can be changed for diagnostics:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW_MAX_REQUESTS=<N>
```

Requests beyond the cap are counted in
`benchmark.fasim_forward_score_batch_unsupported_requests` and are not sent to
the GPU shadow. This cap does not affect CPU alignment or output.

The shadow does not change runtime semantics. CPU `aligner.Align()` remains the
authority for score, endpoint, traceback, CIGAR, candidate state, output, and
digest. The GPU result is only compared against the CPU forward score/end
result and reported through `benchmark.fasim_forward_score_batch_*` telemetry.

This is not a real optimization path and it is not a replacement for
`ssw_align()`. The implementation collects forward score/end requests, copies
the translated query/reference buffers and CPU authority result, groups requests
by scoring/gap configuration, then runs one batched score/end CUDA probe per
group when telemetry is snapshotted.

The batch kernel is intentionally conservative: one CUDA block handles one
request with a simple single-thread DP. Its purpose is to test whether batching
removes the per-request launch/staging cost seen in the first GPU shadow, not to
claim a final optimized GPU alignment implementation.

## Baseline Context

The earlier per-request shadow used:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1
```

Local smoke result:

```text
requests: 165
cells: 31,446,596
score mismatches: 0
endpoint mismatches: 0
unsupported requests: 0
CPU forward score/end seconds: ~0.005s
GPU shadow total seconds: ~3.1s
```

That proved the score/end contract shape, but the per-request implementation is
a hard performance no-go.

## Telemetry

The Fasim process emits these fields on stderr:

| field | meaning |
|---|---|
| `benchmark.fasim_forward_score_batch_shadow_enabled` | `1` when `FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1`, otherwise `0`. |
| `benchmark.fasim_forward_score_batch_requests` | Forward score/end requests observed by the batch shadow. |
| `benchmark.fasim_forward_score_batch_cells` | Sum of query length times target length for shadowed requests. |
| `benchmark.fasim_forward_score_batch_pack_seconds` | Host-side request copy, grouping, and contiguous batch packing seconds. |
| `benchmark.fasim_forward_score_batch_h2d_seconds` | Host-to-device copy seconds. |
| `benchmark.fasim_forward_score_batch_kernel_seconds` | CUDA event kernel seconds. |
| `benchmark.fasim_forward_score_batch_d2h_seconds` | Device-to-host copy seconds. |
| `benchmark.fasim_forward_score_batch_unpack_seconds` | Result comparison/unpack seconds. |
| `benchmark.fasim_forward_score_batch_total_seconds` | End-to-end GPU batch call seconds, including allocation/copies/kernel/readback. |
| `benchmark.fasim_forward_score_batch_cpu_reference_seconds` | CPU authority forward score/end seconds for the same requests. |
| `benchmark.fasim_forward_score_batch_score_mismatches` | GPU score mismatches versus the CPU authority result. |
| `benchmark.fasim_forward_score_batch_endpoint_mismatches` | GPU best end-position mismatches versus the CPU authority result. Endpoint mismatches are diagnostic only. |
| `benchmark.fasim_forward_score_batch_unsupported_requests` | Requests the shadow could not run, for example missing CUDA support or unsupported dimensions. |

The sharded runner parser aggregates these fields into `per_shard`,
`per_worker`, `sharded_telemetry`, and `single_run.telemetry`.

## Smoke Signal

Run:

```bash
make check-fasim-forward-score-gpu-batch-shadow
```

Observed local smoke signal:

```text
requests: 165
cells: 31,446,596
score mismatches: 0
endpoint mismatches: 0
unsupported requests: 0
CPU forward score/end seconds: ~0.0052s
batch GPU total seconds: ~0.02s
kernel seconds: ~0.016-0.017s
pack/H2D/D2H/unpack seconds: itemized in telemetry
```

This is a useful architectural signal:

```text
batching vs per-request:
  ~3.1s -> ~0.02s on the smoke fixture

batch shadow vs CPU forward score/end:
  still slower than CPU, ~0.02s vs ~0.0052s
```

So the batched shadow fixes most of the per-request dispatch problem, but this
first conservative batch kernel is still not a performance candidate.

## Decision Use

Use this telemetry only as a diagnostic score/end batch probe. Do not use GPU
score, endpoint, CIGAR, traceback, candidate state, output, or digest from this
path.

Continue the GPU-score line only if a future implementation shows:

```text
score_mismatches = 0
digest unchanged
unsupported_requests = 0 or explainable
batch total < CPU forward score/end time
pack/H2D/kernel/D2H/unpack costs clearly itemized
```

Stop or redesign if:

```text
score mismatches appear
batch total remains slower than CPU forward score/end
kernel time dominates without a credible parallel DP design
pack/H2D/D2H dominates and no device-resident request layout is available
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
