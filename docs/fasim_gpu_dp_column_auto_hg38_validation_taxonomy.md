# Fasim GPU DP+column AUTO hg38 Validation Taxonomy

Base branch:

```text
fasim-gpu-dp-column-auto-hg38-validation-taxonomy
```

This report classifies `FASIM_GPU_DP_COLUMN_AUTO=1` validation fallbacks on a large real hg38 workload after the score-mismatch and lowercase soft-mask fixes. GPU AUTO remains default-off. Lowercase FASTA bases are now treated as their uppercase bases during Fasim transforms instead of being converted to `N`; that is an intentional output semantic fix.

## Root Cause And Fix

The original hg38 score mismatches were threshold-score mismatches, not CUDA DP recurrence mismatches. A second issue was that legacy Fasim transformed lowercase soft-masked `a/c/g/t` bases to `N`; this report uses the corrected case-insensitive transform. GPU AUTO also keeps exact-column scoreInfo reconstruction on the already-selected threshold, so compact overflow repair cannot drift from the CPU threshold contract.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| auto | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1` |
| auto_validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1 FASIM_GPU_DP_COLUMN_THRESHOLD_SHADOW=1` |

## Performance And Digest

| Workload | Observed windows | Observed cells | Selected path | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hg38_chr21_H19 | 32,836 | 461,674,160,000 | compact_gpu | 126.377000 | 73.498300 | 1.72x | 178.307000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## Validation Counters

| Validate windows | Failed windows | Score mismatches | ScoreInfo mismatches | Compact mismatches | Correctness fallbacks | Compact fallback windows | Emit exact extends | Batch fallback batches | Batch fallback windows | Batch failed windows | First failed window | First failure reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 0 | 0 | 0 | 0 | 0 | 2,356 | 2,356 | 0 | 0 | 0 | -1 | none |

## Threshold Source

| Mode | GPU threshold windows | CPU threshold windows | CPU threshold seconds | Shadow enabled | Shadow compared windows | Shadow mismatches | Shadow max delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 32,532 | 304 | 0.384468 | 0 | 0 | 0 | 0 |
| auto_validate | 65,064 | 608 | 0.773509 | 1 | 608 | 8 | 12 |

## Fallback Taxonomy

| Reason | Windows | Percent of validated windows | Digest affected | Notes |
| --- | --- | --- | --- | --- |
| score mismatch | 0 | 0.00% | no | CPU max score differed from GPU peak score in validation. |
| scoreInfo mismatch | 0 | 0.00% | no | CPU scoreInfo vector differed from GPU-derived scoreInfo. |
| compact scoreInfo mismatch | 0 | 0.00% | no | Subset of scoreInfo mismatches while compact scoreInfo was active. |
| validation failed windows | 0 | 0.00% | no | Actual windows whose validate task returned false. |
| validation batch fallback | 0 | 0.00% | no | Whole batches rerun on CPU because at least one window in the batch failed validation. |
| batch-amplified fallback | 0 | 0.00% | no | Windows rerun on CPU only because they shared a failed validation batch. |
| TopK overflow in validation | 2,356 | 7.18% | no | Compact TopK overflow forced exact-column scoreInfo reconstruction during validation. |
| emit-time compact TopK exact extend | 2,356 | 7.18% | no | Successful compact overflow exact-column extends while emitting GPU results. |
| exact scoreInfo validation failure | 0 | 0.00% | no | Exact-column scoreInfo debug/reconstruction failed during validation. |
| CUDA batch failure fallback | 0 | 0.00% | no | CUDA topK column maxima batch failed before validation. |
| emit-time exact scoreInfo failure fallback | 0 | 0.00% | no | Exact scoreInfo reconstruction failed while emitting GPU results. |

## TopK Sweep

| TopK | AUTO+validate seconds | Exact extends | Compact fallback windows | Digest match | Validation failed windows |
| --- | --- | --- | --- | --- | --- |
| default (256) | 178.307000 | 2,356 | 2,356 | yes | 0 |
| 64 | 679.793000 | 27,046 | 27,046 | yes | 0 |
| 128 | 408.654000 | 13,708 | 13,708 | yes | 0 |

The sweep is characterization only. Runtime dynamic TopK remains a follow-up candidate unless a later PR turns this evidence into a strict policy change. Values below the default TopK test whether reducing TopK creates more exact extends; values above the default require a separate implementation because the current runtime caps TopK at 256.

## Finding

`fasim_gpu_dp_column_fallbacks=0` is batch-granularity accounting, not a count of mismatching windows. The run validated 32,836 windows; 0 windows failed validation, including 0 score mismatch windows. Those failed windows caused 0 windows to be rerun on CPU because validation fallback is applied to whole batches, leaving 0 batch-amplified fallback windows.

`fasim_gpu_dp_column_compact_scoreinfo_fallbacks=2,356` splits into 0 validation batch fallback windows plus 2,356 successful emit-time compact TopK exact-column extends. Validation also reconstructed exact scoreInfo for 2,356 TopK-overflow windows, tracked separately by the new validation telemetry.

Digest match remains useful but is not treated as strict validation clean.

## Decision

Validation taxonomy is clean for this workload. Threshold shadow shows true non-ACGT windows cannot yet switch blindly to GPU peak thresholds: 608 shadow comparisons produced 8 mismatches with max delta 12, while the production path keeps CPU threshold fallback for those windows. TopK sweep shows lowering TopK below the current default 256 increases exact-column extends and is not an optimization path. AUTO remains default-off; a later PR may evaluate N-aware threshold equivalence or a >256/batched exact-column strategy.

Forbidden-scope check:

```text
new GPU/kernel optimization logic: no
default GPU DP+column: no
validation relaxation or hidden mismatches: no
lowercase soft-mask output semantic fix: yes
threshold contract fix for non-ACGT transformed targets: yes
non-overlap/SIM-close/recovery change: no
```
