# Fasim SSW Align Internal Decomposition

This telemetry-only report decomposes the remaining `aligner.Align` setup and `ssw_align` internals after the current speed stack. It does not add an optimization, change output, scoring, thresholds, non-overlap behavior, GPU AUTO policy, SIM-close, recovery, or validation behavior.

Measured opt-in stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_ALIGNER_ALIGN_INTERNALS=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

| Mode | Seconds | Speedup vs table | Digest match | Records |
| --- | --- | --- | --- | --- |
| table_only | 125.651000 | 1.00x | yes | 6546 |
| AUTO + cache + decomposition | 58.472300 | 2.15x | yes | 6546 |

## Required Component Table

| Component | Seconds | Calls | Percent of aligner | Notes |
| --- | --- | --- | --- | --- |
| aligner setup | 4.762010 | 979,282 | 16.25% | strlen, allocation, query/ref translate, and profile cache lookup/build |
| strlen(query) | 0.041620 | 979,282 | 0.14% | query length discovery |
| query allocation | 0.168009 | 979,282 | 0.57% | translated query buffer allocation |
| query translate | 1.274760 | 979,282 | 4.35% | ASCII bases to SSW alphabet |
| ref translate | 0.045880 | 979,282 | 0.16% | short target translation |
| profile cache lookup | 3.095920 | 979,282 | 10.57% | exact query/scoring key map lookup, including miss build path |
| profile cache hit | 3.095870 | 979,281 | 10.57% | hit-only lookup time |
| profile cache miss | 0.000054 | 1 | 0.00% | miss lookup plus profile build insertion |
| ssw_align | 24.004600 | 979,282 | 81.94% | SSW forward, reverse-start, endpoint bookkeeping, and CIGAR section |
| forward score/end | 17.020000 | 979,282 | 58.09% | initial local score and endpoint search |
| reverse-start | 5.165920 | 979,282 | 17.63% | reverse substring alignment to recover begin coordinates |
| CIGAR section | 1.687120 | 979,282 | 5.76% | CIGAR preparation plus banded traceback; includes banded_sw below |
| banded_sw | 1.653630 | 979,282 | 5.64% | nested core traceback DP inside CIGAR section |
| endpoint bookkeeping | 0.032552 | 979,282 | 0.11% | copy forward/reverse best cells into returned endpoint fields |

## SIMD Path Mix

| Path | Seconds | Calls | Percent of ssw_align | Notes |
| --- | --- | --- | --- | --- |
| byte path | 19.876800 | n/a | 82.80% | SSE2 byte kernel calls, forward plus reverse when byte path is valid |
| word path | 0.000000 | n/a | 0.00% | SSE2 word kernel calls, including saturation fallback |
| word fallback | n/a | 0 | n/a | byte score saturated at 255 and retried with word profile |

## Call Shape And Correctness

| Align calls | Emitted records | Rejected records | Cache hits | Cache misses | Unique keys | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 979,282 | 19,511 | 376,741 | 979,281 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

## Decision Guide

Setup remains material. A future `TranslatedQuery/ProfileContext` cache shadow is worth evaluating before touching traceback semantics.

## Boundaries

```text
real optimization added: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
