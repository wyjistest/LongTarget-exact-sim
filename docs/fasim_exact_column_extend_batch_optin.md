# Fasim Exact-Column Extend Batch Opt-In

This report characterizes the default-off real exact-column extend batch path. The default final stack remains unchanged; CPU exact-column extend remains the fallback authority.

Final stack under test:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
# batch mode adds FASIM_EXACT_COLUMN_EXTEND_BATCH=1
# validate mode also adds FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## A/B Summary

| Mode | Total seconds | vs final | Records | Digest | Batch active | Validate |
| --- | --- | --- | --- | --- | --- | --- |
| final_stack | 51.400800 | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 0 | 0 |
| final_stack_batch | 26.847000 | 1.91x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 1 | 0 |
| final_stack_batch_validate | 51.292000 | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 1 | 1 |

## Batch Telemetry

| Mode | Requests | Cells | Max cells/request | Batch total | Pack | H2D | Kernel | D2H | Unpack | Apply | Validate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_stack | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| final_stack_batch | 2,356 | 33,125,360,000 | 14,060,000 | 0.138748 | 0.002590 | 0.001809 | 0.115792 | 0.006243 | 0.028793 | 0.000573 | 0.000000 |
| final_stack_batch_validate | 2,356 | 33,125,360,000 | 14,060,000 | 0.139665 | 0.002526 | 0.001843 | 0.116647 | 0.006306 | 0.030142 | 0.000513 | 24.381800 |

## Correctness

| Mode | Score | Endpoint | ScoreInfo | Digest | Fallbacks |
| --- | --- | --- | --- | --- | --- |
| final_stack | 0 | 0 | 0 | 0 | 0 |
| final_stack_batch | 0 | 0 | 0 | 0 | 0 |
| final_stack_batch_validate | 0 | 0 | 0 | 0 | 0 |

## Boundaries

```text
default enablement: no
CPU fallback authority: yes
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext change: no
SIM-close/recovery change: no
validation relaxation: no
```
