# Fasim aligner.Align Decomposition

This telemetry-only report characterizes `aligner.Align` calls inside `fastSIM_extend_from_scoreinfo` under `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1`. It does not bypass Align and does not change output, scoring, thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, or recovery behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 125.810000 | 73.071200 | 1.72x | 177.723000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## Align Call Distribution

| Mode | Calls | Total seconds | Total cells | Avg query len | Avg target len | Max query len | Max target len | Seconds / call |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 979,282 | 43.743600 | 185,534,761,740 | 2812.00 | 67.38 | 2,812 | 190 | 0.000045 |
| auto_validate | 979,282 | 43.879100 | 185,534,761,740 | 2812.00 | 67.38 | 2,812 | 190 | 0.000045 |

## Align Outcome

| Mode | Records considered | Emitted | Rejected after Align | Rejected fraction | ScoreInfo score matches | ScoreInfo position matches | Required for CIGAR | Required for score | Required for coordinates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 600,667 | 19,511 | 376,741 | 62.72% | 368,712 | 413,829 | 600,667 | 600,667 | 600,667 |
| auto_validate | 600,667 | 19,511 | 376,741 | 62.72% | 368,712 | 413,829 | 600,667 | 600,667 | 600,667 |

## Bypass Feasibility

| Mode | Shadow enabled | Bypassable | Non-bypassable | Estimated saved seconds | Score mismatches | Coordinate mismatches | CIGAR missing records | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 0 | 0 | 0 | 0.000000 | 0 | 0 | 0 | No bypass estimator is active in this telemetry PR. |
| auto_validate | 0 | 0 | 0 | 0.000000 | 0 | 0 | 0 | No bypass estimator is active in this telemetry PR. |

## Decision

`aligner.Align` accounts for 43.743600s across 979,282 calls. Average target length is 67.38 bases and max target length is 190 bases.

62.72% of considered records are rejected after Align. The next PR should investigate pre-align filtering or a scoreInfo-to-output shadow.

## Boundaries

```text
bypass Align in real output: no
CIGAR/alignment output semantic change: no
scoring/threshold/non-overlap change: no
GPU kernel or AUTO policy change: no
validation relaxation: no
```
