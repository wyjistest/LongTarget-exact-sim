# Fasim aligner.Align CPU Internals

This telemetry-only report decomposes the CPU `aligner.Align` wrapper used by `fastSIM_extend_from_scoreinfo`. It is enabled only by `FASIM_ALIGNER_ALIGN_INTERNALS=1`; it does not change output, scoring, thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, recovery, or validation behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Baseline

| Observed windows | Observed cells | Table seconds | AUTO+internals seconds | AUTO speedup | Digest | Records | Digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 126.962000 | 74.080400 | 1.71x | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes |

## Wrapper Internals

| Component | Seconds | Percent of Align | Notes |
| --- | --- | --- | --- |
| strlen(query) | 0.045091 | 0.10% | query length discovery |
| query allocation | 0.142857 | 0.32% | per-call translated query buffer |
| query translate | 1.285150 | 2.89% | ASCII to SSW alphabet |
| ref allocation | 0.021061 | 0.05% | per-call translated target buffer |
| ref translate | 0.047408 | 0.11% | short target translation |
| profile build | 18.001300 | 40.42% | ssw_init query profile |
| ssw_align | 24.269200 | 54.49% | SSW DP plus begin/CIGAR work |
| convert alignment | 0.366518 | 0.82% | s_align to C++ Alignment |
| destroy/free | 0.206113 | 0.46% | per-call cleanup |

## Call Shape

| Align calls | CPU internals calls | Total cells | Avg query len | Avg target len | Max target len | Null results | Measured internals | Residual vs outer Align |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 979,282 | 979,282 | 185,534,761,740 | 2812.00 | 67.38 | 190 | 0 | 44.384698 | 0.154902 |

## Decision

Query profile build is a material cost. The next PR should evaluate query-profile reuse or a batched CPU wrapper before changing alignment semantics.

## Boundaries

```text
optimize aligner.Align: no
bypass Align in real output: no
CIGAR/alignment output semantic change: no
scoring/threshold/non-overlap change: no
GPU kernel or AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
