# Fasim aligner.Align Batch Shadow

This report characterizes a default-off `aligner.Align` batch shadow. The real CPU `aligner.Align` path remains authoritative; the shadow only collects bounded requests and reports score/coordinate contract coverage. It does not feed shadow results into output and does not change scoring, thresholds, non-overlap, CIGAR/alignment output, GPU DP column AUTO policy, SIM-close, or recovery behavior.

Current implementation note: the shadow uses the existing CUDA DP+column top-1 backend to batch score and reference-end checks. CPU `aligner.Align` still provides the real output and the CIGAR/alignment-string contract is not implemented.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians. Shadow cap: `1000` requests, stride `1`.

## Performance

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | Batch shadow seconds | Batch shadow speedup | Batch shadow validate seconds | Digest | Records | Shadow digest match | Validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 125.868000 | 73.558300 | 1.71x | 73.422300 | 1.71x | 178.132000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## Request Shape

| Mode | Requests total | Compared | Unsupported/skipped | Query bases | Target bases | Cells | H2D bytes | D2H bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_shadow | 979,282 | 1,000 | 978,282 | 2,812,000 | 68,358 | 192,222,696 | 68,358 | 8,000 |
| batch_shadow_validate | 979,282 | 1,000 | 978,282 | 2,812,000 | 68,358 | 192,222,696 | 68,358 | 8,000 |

## Contract Coverage

| Mode | Enabled | Supported | Disabled reason | Score | Coordinates | CIGAR | Alignment string |
| --- | --- | --- | --- | --- | --- | --- | --- |
| batch_shadow | 1 | 1 | 0 | 1 | 1 | 0 | 0 |
| batch_shadow_validate | 1 | 1 | 0 | 1 | 1 | 0 | 0 |

## Mismatches

| Mode | Score mismatches | Coordinate mismatches | CIGAR mismatches | Alignment string mismatches | Total mismatches | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- |
| batch_shadow | 0 | 0 | 0 | 0 | 0 | 0 |
| batch_shadow_validate | 0 | 0 | 0 | 0 | 0 | 0 |

## Timing

| Mode | CPU reference seconds | Shadow total seconds | Kernel seconds | Transfer seconds |
| --- | --- | --- | --- | --- |
| batch_shadow | 0.044901 | 0.099954 | 0.089377 | 0.010576 |
| batch_shadow_validate | 0.045312 | 0.099405 | 0.088802 | 0.010603 |

## Decision

Stage 1 CUDA score/ref-end shadow is clean for the sampled requests. Next work should add query-coordinate and CIGAR/alignment-string reconstruction shadow before any real path.

## Boundaries

```text
use shadow result for output: no
skip CPU aligner.Align in real path: no
CIGAR/alignment output semantic change: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
