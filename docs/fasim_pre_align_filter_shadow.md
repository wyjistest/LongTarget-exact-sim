# Fasim Pre-Align Filter Shadow

This diagnostic report evaluates a pre-align reject estimator before `aligner.Align` while leaving the real output path unchanged. The shadow does not skip Align, does not change output, scoring, thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, or recovery behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Observed windows | Observed cells | Table seconds | AUTO+shadow seconds | AUTO speedup | AUTO+validate+shadow seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 126.768000 | 73.913100 | 1.72x | 179.572000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## Shadow Outcome

| Mode | Candidates | Actual emitted | Actual rejected | Predicted reject | True reject | False reject | False keep | Precision | Recall | Digest affected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 600,667 | 19,511 | 581,156 | 5 | 5 | 0 | 581,151 | 100.00% | 0.00% | 0 |
| auto_validate | 600,667 | 19,511 | 581,156 | 5 | 5 | 0 | 581,151 | 100.00% | 0.00% | 0 |

## Estimated Savings

| Mode | Align seconds | Align calls | Align cells | Rejected align calls | Rejected align cells | Est calls saved | Est cells saved | Est seconds saved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 44.691900 | 979,282 | 185,534,761,740 | 942,923 | 178,831,833,896 | 5 | 250,268 | 0.000163 |
| auto_validate | 44.878400 | 979,282 | 185,534,761,740 | 942,923 | 178,831,833,896 | 5 | 250,268 | 0.000160 |

## Rejection Reason Taxonomy

| Mode | Score/identity/stability | Nt | Length | Coordinates | Overlap/rank | CIGAR | Unknown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 376,741 | 27,988 | 0 | 0 | 176,427 | 0 | 0 |
| auto_validate | 376,741 | 27,988 | 0 | 0 | 176,427 | 0 | 0 |

## Strategy Summary

| Strategy | Predicted reject | True reject | False reject | False keep | Est calls saved | Est cells saved | Est seconds saved | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined conservative guard | 5 | 5 | 0 | 581,151 | 5 | 250,268 | 0.000163 | score/position/max-cutlength metadata only; real path unchanged |
| oracle upper bound | 581,156 | 581,156 | 0 | 0 | 942,923 | 178,831,833,896 | 43.077288 | analysis only; uses post-align outcome |

## Decision

The shadow found a zero-false-reject filter, but estimated savings are small. Keep this as telemetry unless larger workloads show more value.

## Boundaries

```text
skip Align in real path: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU kernel or AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
