# Fasim GPU DP+column Emit / ScoreInfo Decomposition

This characterization decomposes the default-off `FASIM_GPU_DP_COLUMN_AUTO=1` path after GPU DP+column scoring. It adds telemetry only: no GPU optimization logic, no scoring/threshold change, no output/non-overlap change, and no SIM-close/recovery behavior change.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| auto | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1` |
| auto_validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Performance

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 125.651000 | 72.781500 | 1.73x | 177.292000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## AUTO Post-GPU Decomposition

| Mode | GPU total seconds | GPU kernel seconds | H2D bytes | D2H bytes | compact unpack seconds | topK postprocess seconds | scoreInfo reconstruct seconds | exact-column extend seconds | threshold fallback seconds | emit seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 0.830403 | 0.790932 | 164,180,000 | 67,248,128 | 0.030464 | 0.111148 | 0.156000 | 24.731900 | 0.384302 | 44.341400 |
| auto_validate | 0.833587 | 0.789574 | 164,180,000 | 67,248,128 | 0.058585 | 0.227767 | 0.315207 | 49.811700 | 0.760542 | 44.251500 |

## Counts

| Mode | scoreInfo reconstruct records | CPU emit records | overflow windows | exact extend windows | threshold fallback windows | validation failed windows | score mismatches | scoreInfo mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 600,667 | 19,511 | 2,356 | 2,356 | 304 | 0 | 0 | 0 |
| auto_validate | 1,201,334 | 19,511 | 2,356 | 2,356 | 608 | 0 | 0 | 0 |

## Interpretation

In the AUTO run, exact-column extend is 24.731900s, scoreInfo reconstruction is 0.156000s, threshold fallback is 0.384302s, emit is 44.341400s, and compact result D2H is 67,248,128 bytes.

Emit/extension is the largest measured post-GPU substage; further speed work should focus on the `fastSIM_extend_from_scoreinfo` and output path.

## Boundaries

```text
new GPU optimization logic: no
GPU default/recommendation change: no
scoring/threshold/non-overlap/output change: no
SIM-close/recovery change: no
validation relaxation: no
```
