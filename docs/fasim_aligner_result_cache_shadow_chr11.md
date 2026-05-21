# Fasim Aligner Result-Cache Shadow

This report characterizes whether repeated identical `aligner.Align` requests exist inside legacy `fastSIM_extend_from_scoreinfo`. It is shadow-only: every legacy `aligner.Align` call still executes normally, cached results are never used for runtime output, and the shadow only compares duplicate request results against the first observed result for the same exact key.

Boundary: no real result cache, no default enablement, no output change, no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior change.

Workload: `hg38_chr11_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final_stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| result_cache_shadow | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_ALIGNER_RESULT_CACHE_SHADOW=1` |

## Runtime Summary

| Table-only seconds | Final stack seconds | Result-cache shadow seconds | Final stack speedup | Records | Digest | Final digest match | Shadow digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 450.720000 | 98.026300 | 130.334000 | 4.60x | 20607 | `sha256:0ae481985f0a060873f983cb80c2fb2b75a1fc4ff153b4492868376bb31d7310` | yes | yes |

## Request Shape

| Calls | Unique keys | Duplicate calls | Duplicate fraction | Duplicate cells | Memory estimate bytes |
| --- | --- | --- | --- | --- | --- |
| 3,265,277 | 3,069,999 | 195,278 | 5.98% | 36,141,688,356 | 809,553,314 |

## Key Class

| Key class | Calls | Unique | Duplicates | Est saved seconds | Mismatch count |
| --- | --- | --- | --- | --- | --- |
| query_hash + target_hash + filter/mask/scoring/AVX2 mode | 3,265,277 | 3,069,999 | 195,278 | 4.695390 | 0 |

## Correctness

| Field | Mismatches | Notes |
| --- | --- | --- |
| score | 0 | Duplicate request score matches first-seen result. |
| endpoint | 0 | Compares ref/read begin and end fields. |
| CIGAR | 0 | Compares CIGAR string. |
| digest | 0 | Runtime digest is unchanged because shadow output is not used. |

## Timing Estimate

| Align CPU seconds | Estimated seconds saved | Shadow total seconds |
| --- | --- | --- |
| 82.158100 | 4.695390 | 130.334000 |

## Decision

Duplicate requests are present, but the hit rate and estimated saved CPU time are modest. Keep the result-cache idea as shadow-only unless larger workloads show a larger absolute saving with acceptable memory overhead.

## Boundaries

```text
real result cache added: no
skips aligner.Align in runtime path: no
uses cached result for runtime output: no
default enabled: no
scoring/threshold/non-overlap/output changed: no
GPU AUTO / SSW / AVX2 / ProfileContext changed: no
SIM-close / recovery changed: no
```
