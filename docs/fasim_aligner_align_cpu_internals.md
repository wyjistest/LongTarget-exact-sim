# Fasim aligner.Align CPU Internals

This telemetry-only report decomposes the CPU `aligner.Align` wrapper used by `fastSIM_extend_from_scoreinfo`. It is enabled only by `FASIM_ALIGNER_ALIGN_INTERNALS=1`; it does not change output, scoring, thresholds, non-overlap, GPU kernels, AUTO policy, SIM-close, recovery, or validation behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Baseline

| Observed windows | Observed cells | Table seconds | AUTO+internals seconds | AUTO speedup | Digest | Records | Digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 125.180000 | 73.028300 | 1.71x | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes |

## Wrapper Internals

| Component | Seconds | Percent of Align | Notes |
| --- | --- | --- | --- |
| strlen(query) | 0.042659 | 0.10% | query length discovery |
| query allocation | 0.150572 | 0.35% | per-call translated query buffer |
| query translate | 0.958412 | 2.20% | ASCII to SSW alphabet |
| ref allocation | 0.020788 | 0.05% | per-call translated target buffer |
| ref translate | 0.047975 | 0.11% | short target translation |
| profile build | 17.679700 | 40.62% | ssw_init query profile |
| ssw_align | 23.912700 | 54.93% | SSW DP plus begin/CIGAR work |
| convert alignment | 0.364035 | 0.84% | s_align to C++ Alignment |
| destroy/free | 0.194133 | 0.45% | per-call cleanup |

## Call Shape

| Align calls | CPU internals calls | Total cells | Avg query len | Avg target len | Max target len | Null results | Measured internals | Residual vs outer Align |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 979,282 | 979,282 | 185,534,761,740 | 2812.00 | 67.38 | 190 | 0 | 43.370974 | 0.158826 |

## SSW Profile Reuse Shadow

| Build calls | Unique keys | Reusable calls | Reuse opportunity | Build seconds | Est saved seconds | Compared | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 979,282 | 1 | 979,281 | 100.00% | 17.824900 | 17.824900 | 1,024 | 0 | 0 | 0 | 0 |

| Last query length | Scoring hash | Orientation key | Digest match |
| --- | --- | --- | --- |
| 2,812 | 1,288,116,435,481,102,592 | 0 | yes |

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
