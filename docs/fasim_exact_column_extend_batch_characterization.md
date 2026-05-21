# Fasim Exact-Column Extend Batch Characterization

This docs/script-only report characterizes the default-off real `FASIM_EXACT_COLUMN_EXTEND_BATCH=1` opt-in with repeated median runs. It does not add optimization logic, default the batch path, or change output, scoring, threshold, non-overlap, GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, recovery, or validation behavior.

## Modes

| Mode | Environment |
| --- | --- |
| table-only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1` |
| final stack + exact-column batch | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| final stack + exact-column batch + validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` |

Workload: `hg38_chr21_H19`. Each mode uses 3 run(s); tables report medians.

## Median Summary

| Mode | Total seconds | Speedup vs table-only | Speedup vs final stack | Records | Digest | Digest clean | Batch active | Validate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| table-only | 131.579000 | 1.00x | n/a | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes | 0 | 0 |
| final stack | 51.030900 | 2.58x | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes | 0 | 0 |
| final stack + exact-column batch | 27.011300 | 4.87x | 1.89x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes | 1 | 0 |
| final stack + exact-column batch + validate | 51.132300 | 2.57x | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes | 1 | 1 |

`FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` is a correctness gate, not the recommended performance mode.

## Batch Telemetry

| Mode | Requests | Cells | Max cells/request | Batch total | Pack | H2D | Kernel | D2H | Unpack | Apply | CPU fallback | Validate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| table-only | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| final stack | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| final stack + exact-column batch | 2,356 | 33,125,360,000 | 14,060,000 | 0.139044 | 0.002508 | 0.001774 | 0.115943 | 0.006468 | 0.028505 | 0.000547 | 0.000000 | 0.000000 |
| final stack + exact-column batch + validate | 2,356 | 33,125,360,000 | 14,060,000 | 0.137920 | 0.002546 | 0.001812 | 0.114595 | 0.006428 | 0.030351 | 0.000562 | 0.000000 | 24.090500 |

## Correctness

| Mode | Score | Endpoint | ScoreInfo | Digest | Batch fallbacks | GPU fallbacks |
| --- | --- | --- | --- | --- | --- | --- |
| table-only | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack + exact-column batch | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack + exact-column batch + validate | 0 | 0 | 0 | 0 | 0 | 0 |

## Decision

`FASIM_EXACT_COLUMN_EXTEND_BATCH=1` remains a strong large-workload opt-in candidate if these medians stay clean and stable. This PR does not default it.

## Boundaries

```text
optimization logic added: no
default batch enablement: no
CPU fallback authority: yes
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext change: no
SIM-close/recovery change: no
validation relaxation: no
```
