# Fasim Exact-Column Extend Batch Shadow

This PR adds a default-off diagnostic shadow for the exact-column extend step identified by the final speed stack decomposition. CPU exact-column extend remains authoritative; shadow output is never fed into fastSIM emit or final output.

Final stack under test:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
# shadow mode adds:
FASIM_EXACT_COLUMN_EXTEND_BATCH_SHADOW=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Mode | Total seconds | Records | Digest | Shadow enabled |
| --- | --- | --- | --- | --- |
| final_stack | 51.453600 | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 0 |
| final_stack_shadow | 51.113000 | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 1 |

## Request Shape

| Requests | Compared | Cells | Avg cells/request | H2D bytes | D2H bytes |
| --- | --- | --- | --- | --- | --- |
| 2,356 | 2,356 | 33,125,360,000 | 14,060,000 | 11,780,000 | 47,120,000 |

## Correctness

| Field | Mismatches | First mismatch | Notes |
| --- | --- | --- | --- |
| score | 0 | -1 | max column score contract |
| endpoint | 0 | -1 | max-score column endpoint |
| scoreInfo | 0 | -1 | score/position records consumed by fastSIM emit |
| total | 0 | -1 | shadow remains diagnostic only |

## Timing

| CPU reference | Shadow total | Kernel | Transfer | Estimated saved |
| --- | --- | --- | --- | --- |
| 24.103200 | 0.032465 | 0.000000 | h2d=11,780,000, d2h=47,120,000 | 24.070700 |

The current shadow is a CPU-side diagnostic contract check. `kernel_seconds=0` means this PR does not add a new CUDA kernel; a later real batched GPU opt-in would need to replace the diagnostic shadow with a packed request/output implementation and validate the same fields.
`estimated saved` is an upper-bound diagnostic for the exact-column contract only. It is not a measured wall-clock speedup from this PR.

## Boundaries

```text
real output changed: no
shadow output used by emit: no
default enablement: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext change: no
SIM-close/recovery change: no
validation relaxation: no
```

Decision: contract shadow is clean. A real batched GPU exact-column extend remains a separate opt-in PR and should keep CPU validation/fallback.
