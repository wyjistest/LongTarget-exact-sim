# Fasim Accelign Endpoint Envelope Shadow

This report characterizes a default-off research shadow for using Accelign endpoint output as an envelope hint, followed by CPU legacy traceback inside that envelope. CPU `aligner.Align` remains the runtime authority; the shadow never feeds Fasim output.

The shadow tests whether `Accelign ref_end +/- flank` covers the CPU legacy alignment interval and whether CPU traceback inside that smaller target window can reconstruct score, endpoints, and CIGAR.

Workload: `hg38_chr21_softmask_compact_region`. Each mode uses 1 run(s); tables report medians.

## Baseline

| Table seconds | AUTO seconds | Digest | Records | AUTO digest match |
| --- | --- | --- | --- | --- |
| 0.026127 | 0.025872 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |

## Envelope Coverage

| Mode | Flank | Requests | Compared | Unsupported | Contains CPU endpoint | Misses CPU endpoint | Contains CPU interval | Misses CPU interval |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| envelope_128_flank_32 | 32 | 232 | 128 | 104 | 128 | 0 | 4 | 124 |
| envelope_128_flank_64 | 64 | 232 | 128 | 104 | 128 | 0 | 92 | 36 |

## Contract

| Mode | Score mismatches | Endpoint mismatches | CIGAR mismatches | Total mismatches | Uses output |
| --- | --- | --- | --- | --- | --- |
| envelope_128_flank_32 | 123 | 124 | 124 | 371 | 0 |
| envelope_128_flank_64 | 36 | 36 | 36 | 108 | 0 |

## Timing

| Mode | Accelign seconds | CPU full seconds | CPU envelope seconds | Net saved | Projected full saved |
| --- | --- | --- | --- | --- | --- |
| envelope_128_flank_32 | 0.034358 | 0.007694 | 0.005434 | -0.032097 | -0.058176 |
| envelope_128_flank_64 | 0.034693 | 0.007509 | 0.006955 | -0.034139 | -0.061876 |

## Decision

The Accelign-derived envelope missed at least one CPU legacy alignment interval. Do not use this as a real path with the current flank/policy.

## Boundaries

```text
use Accelign result for output: no
skip CPU aligner.Align: no
Accelign endpoint authority: no
CPU legacy traceback remains authority: yes
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
