# Fasim SSW ProfileContext Shadow

This default-off shadow estimates the cost that could be removed by hoisting translated-query and SSW profile-cache lookup work into a reusable `ProfileContext`. Runtime output remains controlled by the existing CPU `aligner.Align` path; this report adds no real optimization.

Measured opt-in stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_ALIGNER_ALIGN_INTERNALS=1
FASIM_SSW_PROFILE_CONTEXT_SHADOW=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

| Mode | Seconds | Speedup vs table | Digest match | Records |
| --- | --- | --- | --- | --- |
| table_only | 125.716000 | 1.00x | yes | 6546 |
| AUTO + cache + ProfileContext shadow | 61.587200 | 2.04x | yes | 6546 |

| Calls | Reusable calls | Unique keys | Query translate saved est. | Lookup saved est. | Total saved est. | Percent of aligner | Compared |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 979,282 | 979,281 | 1 | 0.961011 | 3.073750 | 4.034761 | 12.45% | 1,024 |

| Aligner setup | Query translate measured | Profile lookup measured | Profile cache hits | Profile cache misses | Profile cache unique keys |
| --- | --- | --- | --- | --- | --- |
| 4.435050 | 0.961012 | 3.073800 | 979,281 | 1 | 1 |

| Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches | Cache fallbacks |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 |

## Decision

The estimated setup saving is material. A future default-off real `FASIM_SSW_PROFILE_CONTEXT=1` path with validation/fallback is worth evaluating.

## Boundaries

```text
real optimization added: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
