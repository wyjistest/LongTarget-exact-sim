# Fasim Accelign Aligner Shadow Scaling

This report characterizes scaling for the default-off Accelign float `aligner.Align` shadow. CPU `aligner.Align` remains the runtime authority; Accelign results are never used for output. This does not add CIGAR/alignment-string reconstruction and does not change scoring, thresholds, non-overlap, GPU DP column AUTO policy, SIM-close, or recovery behavior.

Accelign shadow timing is extra diagnostic work after CPU `aligner.Align`; compare sampled CPU reference seconds against Accelign kernel/total seconds, not Fasim wall-clock as a real-path speedup.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Baseline

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | Digest | Records | AUTO digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 126.690000 | 73.685900 | 1.72x | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes |

## Scaling

| Sample cap | Requests total | Compared | Skipped | CPU reference seconds | Accelign kernel seconds | Staging/overhead seconds | Accelign shadow total seconds | Kernel vs CPU speedup | Total vs CPU speedup | Score mismatches | Endpoint mismatches | Total mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 979,282 | 1,000 | 978,282 | 0.047064 | 0.020658 | 0.030068 | 0.050725 | 2.28x | 0.93x | 0 | 6 | 6 |
| 10000 | 979,282 | 10,000 | 969,282 | 0.457947 | 0.137534 | 0.128548 | 0.266082 | 3.33x | 1.72x | 0 | 114 | 114 |
| 50000 | 979,282 | 50,000 | 929,282 | 2.248550 | 0.650194 | 0.551386 | 1.201580 | 3.46x | 1.87x | 0 | 578 | 578 |
| 100000 | 979,282 | 100,000 | 879,282 | 4.503150 | 1.345230 | 1.090080 | 2.435310 | 3.35x | 1.85x | 0 | 1,140 | 1,140 |

## Throughput

| Sample cap | Compared | Cells | CPU requests/sec | Accelign kernel requests/sec | Accelign total requests/sec | CPU cells/sec | Accelign kernel cells/sec | Accelign total cells/sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 1,000 | 192,222,696 | 21247.71 | 48408.33 | 19714.11 | 4084291697.03 | 9305180466.27 | 3789498611.14 |
| 10000 | 10,000 | 1,900,141,512 | 21836.59 | 72709.29 | 37582.40 | 4149260748.51 | 13815794727.12 | 7141187724.09 |
| 50000 | 50,000 | 9,340,873,480 | 22236.55 | 76900.13 | 41611.88 | 4154176460.39 | 14366286800.55 | 7773825696.17 |
| 100000 | 100,000 | 18,691,791,424 | 22206.68 | 74336.73 | 41062.53 | 4150825849.46 | 13894866620.58 | 7675323233.59 |

## Endpoint Taxonomy

| Sample cap | Endpoint mismatches | Same-score endpoint mismatches | Ref-end mismatches | Query-end mismatches | Both-end mismatches | Off-by-one mismatches |
| --- | --- | --- | --- | --- | --- | --- |
| 100000 | 1,140 | 1,140 | 1,140 | 1,140 | 1,140 | 0 |

## Endpoint Direction

| Sample cap | Ref-end GPU before CPU | Ref-end GPU after CPU | Query-end GPU before CPU | Query-end GPU after CPU | Max abs ref-end delta | Max abs query-end delta |
| --- | --- | --- | --- | --- | --- | --- |
| 100000 | 0 | 1,140 | 1,140 | 0 | 58 | 2,333 |

## First Mismatch

| Sample cap | Request | CPU score | Accelign score | CPU ref_end | Accelign ref_end | CPU query_end | Accelign query_end |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100000 | 21 | 56 | 56 | 18 | 19 | 1,942 | 318 |

## Contract Coverage

| Sample cap | Score | Endpoint | CIGAR | Alignment string | Uses runtime output |
| --- | --- | --- | --- | --- | --- |
| 1000 | 1 | 1 | 0 | 0 | 0 |
| 10000 | 1 | 1 | 0 | 0 | 0 |
| 50000 | 1 | 1 | 0 | 0 | 0 |
| 100000 | 1 | 1 | 0 | 0 | 0 |

## Decision

Accelign score is clean at the largest sampled size, but endpoint mismatches remain. Do not use Accelign as an endpoint authority or runtime replacement.

The useful speed signal is sampled `aligner.Align` throughput:

```text
100k sampled CPU reference = 4.503150s
100k Accelign kernel       = 1.345230s  (3.35x vs CPU)
100k Accelign total        = 2.435310s  (1.85x vs CPU)
```

This is not an end-to-end Fasim speedup claim. The current shadow still pays
CPU `aligner.Align`, then runs Accelign as extra diagnostic work. It also
duplicates the query in a simple one-to-one layout, so staging remains a
material part of total time.

```text
largest_cpu_reference_seconds = 4.503150
largest_accelign_kernel_seconds = 1.345230
largest_accelign_total_seconds = 2.435310
```

## Boundaries

```text
use Accelign result for output: no
skip CPU aligner.Align: no
CIGAR/alignment-string reconstruction: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
