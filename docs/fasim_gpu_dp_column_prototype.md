# Fasim GPU DP+column Prototype

Base branch:

```text
fasim-transferstring-table-characterization
```

This PR adds a narrow, default-off GPU DP+column prototype for Fasim after
`FASIM_TRANSFERSTRING_TABLE=1` made DP/column the dominant documented stage.

## Scope

```text
default unchanged
CPU/Fasim output, validation, non-overlap, and final writing remain unchanged
no threshold change
no scoring semantic change
no conservative filter
no full CUDA rewrite
```

The prototype reuses the existing CUDA prealign backend:

```text
batched transformed windows
-> prealign_cuda_find_topk_column_maxima(...)
-> GPU max-score / column peak summary
-> CPU fastSIM_extend_from_scoreinfo(...)
-> existing CPU validation/output path
```

## Runtime Controls

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
```

Optional correctness gate:

```bash
FASIM_GPU_DP_COLUMN_VALIDATE=1
```

`FASIM_GPU_DP_COLUMN=1` activates only the streaming batch prototype. It does
not turn on the older internal `fastSIM` CUDA prealign path; that remains gated
by `FASIM_ENABLE_PREALIGN_CUDA`.

For this prototype, the default `FASIM_PREALIGN_CUDA_TOPK` is 256 when
`FASIM_GPU_DP_COLUMN=1`. The older `FASIM_ENABLE_PREALIGN_CUDA` path keeps its
existing default of 64.

## Telemetry

The profile harness now requires:

```text
fasim_gpu_dp_column_requested
fasim_gpu_dp_column_active
fasim_gpu_dp_column_validate_enabled
fasim_gpu_dp_column_calls
fasim_gpu_dp_column_windows
fasim_gpu_dp_column_cells
fasim_gpu_dp_column_h2d_bytes
fasim_gpu_dp_column_d2h_bytes
fasim_gpu_dp_column_kernel_seconds
fasim_gpu_dp_column_total_seconds
fasim_gpu_dp_column_validate_seconds
fasim_gpu_dp_column_score_mismatches
fasim_gpu_dp_column_column_max_mismatches
fasim_gpu_dp_column_fallbacks
```

`fasim_num_dp_cells` also includes GPU DP+column cells when the prototype is
active, while `fasim_gpu_dp_column_cells` remains the explicit GPU-side count.

## Exactness Finding

Initial validation with the existing topK default exposed a real mismatch:

```text
FASIM_PREALIGN_CUDA_TOPK=64:
  score_mismatches = 0
  column_max_mismatches = 4
  fallbacks = 4
```

Root cause:

```text
CUDA returns peaks sorted by score desc / position asc.
CPU preAlign scans by position and compacts adjacent columns with distance < 5.
topK=64 can also truncate lower-score local peaks that CPU keeps.
```

The prototype now converts GPU peaks back into CPU-shaped `scoreInfo` by sorting
by position and applying the same local-max compaction shape. With topK 256, the
tiny oracle validates cleanly:

```text
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1

canonical digest = sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6
score_mismatches = 0
column_max_mismatches = 0
fallbacks = 0
gpu kernel seconds ~= 0.0123
gpu total seconds ~= 0.0123
D2H bytes = 8192
```

The non-validate GPU path also matches the same tiny oracle digest with zero
recorded mismatches or fallbacks.

## Representative Result

Single-run representative synthetic profile with:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1
```

| Fixture | Total seconds | GPU windows | GPU cells | Kernel seconds | Total GPU seconds | Mismatches | Fallbacks | Digest |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | 0.195230 | 4 | 49,108,768 | 0.012257 | 0.012306 | 0 | 0 | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` |
| medium_synthetic | 0.266851 | 32 | 392,870,144 | 0.012256 | 0.012368 | 0 | 0 | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` |
| window_heavy_synthetic | 0.642174 | 128 | 1,571,480,576 | 0.012241 | 0.012546 | 0 | 0 | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` |

The validate mode is intentionally not a performance mode because it runs CPU
DP/column checks as well.

Single-run non-validate representative totals stayed digest-clean and showed the
expected reduction on the window-heavy synthetic fixture, but not on tiny inputs:

| Fixture | Total seconds | Kernel seconds | GPU total seconds | Mismatches | Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: |
| tiny | 0.417701 | 0.011571 | 0.011708 | 0 | 0 |
| medium_synthetic | 0.234746 | 0.011274 | 0.011387 | 0 | 0 |
| window_heavy_synthetic | 0.392889 | 0.011247 | 0.011543 | 0 | 0 |

The tiny fixture is dominated by one-time CUDA/setup and host overhead. This PR
therefore does not claim a recommended opt-in.

## Decision

```text
prototype wiring: pass
tiny oracle exactness: pass
representative digest stability: pass
recommended opt-in: no
default enablement: no
next target: batching/H2D/host overhead characterization on larger workloads
```

The next PR should characterize larger or real-corpus workloads with repeated
medians and separate CUDA init, H2D/D2H, kernel, CPU extension, and output costs
before promoting the GPU path beyond prototype status.
