# Fasim aligner.Align Batch Shadow Scaling

This report characterizes scaling for the default-off batched/GPU `aligner.Align` score/ref-end shadow. CPU `aligner.Align` remains the real output authority; shadow results are never used for output. This does not add CIGAR/alignment-string reconstruction and does not change scoring, thresholds, non-overlap, GPU DP column AUTO policy, SIM-close, or recovery behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Baseline

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | Digest | Records | AUTO digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 126.355000 | 73.700600 | 1.71x | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes |

## Scaling

| Sample cap | Requests total | Compared | Skipped | CPU reference seconds | GPU kernel seconds | Transfer seconds | GPU shadow total seconds | GPU vs CPU shadow speedup | Score mismatches | Ref-end mismatches | Total mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 979,282 | 1,000 | 978,282 | 0.044909 | 0.091731 | 0.010742 | 0.102473 | 0.44x | 0 | 0 | 0 |
| 10000 | 979,282 | 10,000 | 969,282 | 0.453129 | 0.720775 | 0.082972 | 0.803747 | 0.56x | 0 | 0 | 0 |
| 50000 | 979,282 | 50,000 | 929,282 | 2.252500 | 3.657640 | 0.414290 | 4.071930 | 0.55x | 0 | 0 | 0 |

## Throughput

| Sample cap | Compared | Cells | CPU requests/sec | GPU shadow requests/sec | CPU cells/sec | GPU shadow cells/sec |
| --- | --- | --- | --- | --- | --- | --- |
| 1000 | 1,000 | 192,222,696 | 22267.30 | 9758.67 | 4280280657.06 | 1875837498.66 |
| 10000 | 10,000 | 1,900,141,512 | 22068.77 | 12441.73 | 4193378733.21 | 2364104017.81 |
| 50000 | 50,000 | 9,340,873,480 | 22197.56 | 12279.19 | 4146891667.04 | 2293967106.51 |

## Decision

The score/ref-end GPU shadow remains slower than CPU reference at the largest sampled size. Do not add CIGAR/alignment-string reconstruction or real path from this result.

## Boundaries

```text
use shadow result for output: no
skip CPU aligner.Align: no
CIGAR/alignment-string reconstruction: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
