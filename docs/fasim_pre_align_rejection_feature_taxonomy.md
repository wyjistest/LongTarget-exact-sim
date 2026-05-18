# Fasim Pre-Align Rejection Feature Taxonomy

This telemetry-only report characterizes pre-align features for `fastSIM_extend_from_scoreinfo` candidates and sweeps simple zero-false-reject rules. It does not skip `aligner.Align` and does not change output, scoring, thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, or recovery behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Observed windows | Observed cells | Table seconds | AUTO+feature-sweep seconds | AUTO speedup | AUTO+validate+feature-sweep seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 127.478000 | 74.025200 | 1.72x | 177.944000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## Emitted Vs Rejected Feature Summary

| Mode | Emitted | Rejected | Emitted score mean | Rejected score mean | Emitted rank mean | Rejected rank mean | Emitted target-len mean | Rejected target-len mean | Emitted align calls mean | Rejected align calls mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 19,511 | 581,156 | 93.551500 | 91.905400 | 13.475800 | 14.091500 | 84.230600 | 83.053600 | 1.863510 | 1.622500 |
| auto_validate | 19,511 | 581,156 | 93.551500 | 91.905400 | 13.475800 | 14.091500 | 84.230600 | 83.053600 | 1.863510 | 1.622500 |

## Rejection Reason Taxonomy

| Mode | Score/identity/stability | Nt | Length | Coordinates | Overlap/rank | CIGAR | Unknown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 376,741 | 27,988 | 0 | 0 | 176,427 | 0 | 0 |
| auto_validate | 376,741 | 27,988 | 0 | 0 | 176,427 | 0 | 0 |

## Zero-False-Reject Rule Sweep

| Mode | Rules tested | Best rule | Predicted reject | True reject | False reject | False keep | Est calls saved | Est cells saved | Est seconds saved | Rejected recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 63,922 | position left of emitted minimum | 41 | 41 | 0 | 1 | 164 | 43,338,544 | 0.009397 | 0.01% |
| auto_validate | 63,922 | position left of emitted minimum | 41 | 41 | 0 | 1 | 164 | 43,338,544 | 0.009481 | 0.01% |

## Decision

The sweep found a zero-false-reject rule, but estimated savings are not meaningful on this workload. Do not implement a real filter from this result.

## Boundaries

```text
real pre-align filter: no
skip Align in real path: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU kernel or AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
