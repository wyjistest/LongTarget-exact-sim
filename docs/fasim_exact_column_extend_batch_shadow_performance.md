# Fasim Exact-Column Extend Batch Shadow Performance

This characterization measures the default-off exact-column extend batch shadow added after the final speed stack decomposition. CPU exact-column extend remains authoritative, and shadow output is never used by `fastSIM_extend_from_scoreinfo` or final output.

Final stack under test:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
FASIM_EXACT_COLUMN_EXTEND_BATCH_SHADOW=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Summary

| Mode | Total seconds | Records | Digest | Shadow enabled |
| --- | --- | --- | --- | --- |
| final_stack | 51.326400 | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 0 |
| final_stack_shadow | 50.895300 | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 1 |

`final_stack_shadow` includes extra diagnostic work. Its total runtime is not a proposed real-path speedup.

## Request Shape

| Requests | Compared | Cells | Avg cells/request | Max cells/request | H2D bytes | D2H bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 2,356 | 2,356 | 33,125,360,000 | 14,060,000 | 14,060,000 | 11,780,000 | 47,120,000 |

## Correctness

| Field | Mismatches | First mismatch | Notes |
| --- | --- | --- | --- |
| score | 0 | -1 | max column score |
| endpoint | 0 | -1 | max-score column endpoint |
| scoreInfo | 0 | -1 | score/position records consumed downstream |
| total | 0 | -1 | shadow remains diagnostic only |

## Timing

| CPU reference | Shadow total | Kernel | H2D | D2H | Pack | Unpack | Net saved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24.031800 | 0.027392 | 0.000000 | 0.000000 | 0.000000 | 0.000054 | 0.027175 | 24.004400 |

| Reference | Seconds | Percent of final stack |
| --- | --- | --- |
| final-stack exact-column extend | 24.359300 | 47.46% |
| shadow CPU reference | 24.031800 | 46.82% |
| shadow diagnostic total | 0.027392 | 0.05% |

The current shadow is CPU-side diagnostic instrumentation. `kernel_seconds`, `h2d_seconds`, and `d2h_seconds` remain zero because this PR does not add a packed CUDA batch implementation. `pack_seconds` and `unpack_seconds` characterize the diagnostic request preparation and score/endpoint/scoreInfo reconstruction work.
`net_saved_seconds` is therefore a diagnostic upper-bound estimate against the observed CPU exact-column reference, not a measured real-path wall-clock saving. A real opt-in would need packed request/output buffers, transfer timing, kernel timing, CPU validation, and fallback.

## Boundaries

```text
real output changed: no
shadow output used by fastSIM emit: no
default enablement: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext change: no
SIM-close/recovery change: no
validation relaxation: no
```

Decision: the performance shadow remains contract-clean. Real batched exact-column extend should still be a separate default-off PR with validate/fallback and measured transfer/kernel overhead.
