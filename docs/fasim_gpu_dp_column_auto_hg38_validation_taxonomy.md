# Fasim GPU DP+column AUTO hg38 Validation Taxonomy

Base branch:

```text
fasim-gpu-dp-column-auto-large-workload-characterization
```

This report classifies `FASIM_GPU_DP_COLUMN_AUTO=1` validation fallbacks on a large real hg38 workload. It adds telemetry only: no GPU logic, default behavior, scoring, threshold, non-overlap, output, SIM-close, recovery, or validation semantics change.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| auto | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1` |
| auto_validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Performance And Digest

| Workload | Observed windows | Observed cells | Selected path | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hg38_chr21_H19 | 32,836 | 461,674,160,000 | compact_gpu | 104.709000 | 32.385100 | 3.23x | 176.497000 | `sha256:627fb928df14d931afb7dd0b346587596b64222ca7a2218037caf122901b1ad9` | 3017 | yes | yes |

## Validation Counters

| Validate windows | Failed windows | Score mismatches | ScoreInfo mismatches | Compact mismatches | Correctness fallbacks | Compact fallback windows | Emit exact extends | Batch fallback batches | Batch fallback windows | Batch failed windows | First failed window | First failure reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 15 | 15 | 0 | 0 | 28,672 | 28,702 | 30 | 7 | 28,672 | 15 | 6755 | score_mismatch |

## Fallback Taxonomy

| Reason | Windows | Percent of validated windows | Digest affected | Notes |
| --- | --- | --- | --- | --- |
| score mismatch | 15 | 0.05% | no | CPU max score differed from GPU peak score in validation. |
| scoreInfo mismatch | 0 | 0.00% | no | CPU scoreInfo vector differed from GPU-derived scoreInfo. |
| compact scoreInfo mismatch | 0 | 0.00% | no | Subset of scoreInfo mismatches while compact scoreInfo was active. |
| validation failed windows | 15 | 0.05% | no | Actual windows whose validate task returned false. |
| validation batch fallback | 28,672 | 87.32% | no | Whole batches rerun on CPU because at least one window in the batch failed validation. |
| batch-amplified fallback | 28,657 | 87.27% | no | Windows rerun on CPU only because they shared a failed validation batch. |
| TopK overflow in validation | 308 | 0.94% | no | Compact TopK overflow forced exact-column scoreInfo reconstruction during validation. |
| emit-time compact TopK exact extend | 30 | 0.09% | no | Successful compact overflow exact-column extends while emitting GPU results. |
| exact scoreInfo validation failure | 0 | 0.00% | no | Exact-column scoreInfo debug/reconstruction failed during validation. |
| CUDA batch failure fallback | 0 | 0.00% | no | CUDA topK column maxima batch failed before validation. |
| emit-time exact scoreInfo failure fallback | 0 | 0.00% | no | Exact scoreInfo reconstruction failed while emitting GPU results. |

## Finding

`fasim_gpu_dp_column_fallbacks=28,672` is batch-granularity accounting, not a count of mismatching windows. The run validated 32,836 windows; 15 windows failed validation, including 15 score mismatch windows. Those failed windows caused 28,672 windows to be rerun on CPU because validation fallback is applied to whole batches, leaving 28,657 batch-amplified fallback windows.

`fasim_gpu_dp_column_compact_scoreinfo_fallbacks=28,702` splits into 28,672 validation batch fallback windows plus 30 successful emit-time compact TopK exact-column extends. Validation also reconstructed exact scoreInfo for 308 TopK-overflow windows, tracked separately by the new validation telemetry.

Digest match remains useful but is not treated as strict validation clean.

## Decision

AUTO has a strong large-workload speed signal and final digest match, but strict validation is not clean. Keep GPU AUTO default-off and do not recommend/default it until the score mismatch windows are debugged or the validation contract is refined.

Forbidden-scope check:

```text
new GPU/kernel optimization logic: no
default GPU DP+column: no
validation relaxation or hidden mismatches: no
scoring/threshold/non-overlap/output change: no
SIM-close/recovery change: no
```
