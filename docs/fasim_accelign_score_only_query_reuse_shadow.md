# Fasim Accelign Score-Only Query-Reuse Shadow

This report characterizes a default-off Accelign score-only shadow. CPU `aligner.Align` remains the runtime authority; Accelign scores are not used for output, thresholding, non-overlap, CIGAR/alignment output, SIM-close, or recovery.

Endpoint comparison is intentionally unsupported here because the endpoint taxonomy showed same-score endpoint selection differences. This mode measures score contract, timing, and one-to-all/PSSM query reuse without feeding Accelign scores into runtime output.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Score-Only Timing

| Sample cap | Requests | Compared | Unsupported | CPU reference seconds | Accelign kernel seconds | Staging/overhead seconds | Accelign total seconds | Kernel vs CPU speedup | Total vs CPU speedup | Score mismatches | Endpoint contract | Uses runtime output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 979,282 | 10,000 | 969,282 | 0.454456 | 0.111589 | 0.072078 | 0.183667 | 4.07x | 2.47x | 0 | 0 | 0 |

## Staging

| Sample cap | H2D bytes | D2H bytes | Query staging bytes | Target staging bytes | Query share of H2D | Target share of H2D | Query reuse active |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 1,698,378 | 40,000 | 902,652 | 675,726 | 53.15% | 39.79% | 1 |

## Decision

Score-only is clean and query reuse is active with total shadow time below the sampled CPU reference. Next work can design a score-only precheck/CPU traceback bridge.

```text
largest_cpu_reference_seconds = 0.454456
largest_accelign_score_only_kernel_seconds = 0.111589
largest_accelign_score_only_total_seconds = 0.183667
query_reuse_active = 1
```

## Boundaries

```text
use Accelign result for output: no
use Accelign endpoints: no
skip CPU aligner.Align: no
CIGAR/alignment-string reconstruction: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
mandatory Accelign dependency: no
```
