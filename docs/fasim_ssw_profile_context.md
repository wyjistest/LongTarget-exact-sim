# Fasim SSW ProfileContext Opt-In

This report characterizes the default-off real SSW `ProfileContext` fast path. `FASIM_SSW_PROFILE_CONTEXT=1` is active only when `FASIM_SSW_PROFILE_CACHE=1` is active. It reuses the translated query and hot cached profile context by exact query/scoring key. Validation mode reruns the legacy per-call translation/cache-lookup path and falls back on any score, endpoint, CIGAR, or digest mismatch.

Measured opt-in stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_SSW_PROFILE_CONTEXT=1
```

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

| Mode | Seconds | Speedup vs table | Digest match | Records |
| --- | --- | --- | --- | --- |
| table_only | 126.142000 | 1.00x | yes | 6546 |
| AUTO + cache | 58.178700 | 2.17x | yes | 6546 |
| AUTO + cache + ProfileContext | 57.308400 | 2.20x | yes | 6546 |
| AUTO + cache + ProfileContext validate | 85.886500 | 1.47x | yes | 6546 |

| Mode | Calls | Hits | Misses | Hit rate | Unique keys | Query saved | Lookup saved | Validate seconds | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto_cache_context | 979,282 | 979,281 | 1 | 100.00% | 1 | 1.087980 | 4.599680 | 0.000000 | 0 |
| auto_cache_context_validate | 979,282 | 979,281 | 1 | 100.00% | 1 | 0.997887 | 4.364660 | 28.191400 | 0 |

| Mode | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches | Cache fallbacks |
| --- | --- | --- | --- | --- | --- |
| auto_cache_context | 0 | 0 | 0 | 0 | 0 |
| auto_cache_context_validate | 0 | 0 | 0 | 0 | 0 |

| AUTO+cache seconds | Context seconds | Delta seconds | Context hit rate | Digest clean |
| --- | --- | --- | --- | --- |
| 58.178700 | 57.308400 | 0.870300 | 100.00% | yes |

## Decision

ProfileContext is exact-clean and faster in this run.

## Boundaries

```text
default enabled: no
requires FASIM_SSW_PROFILE_CACHE=1: yes
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
