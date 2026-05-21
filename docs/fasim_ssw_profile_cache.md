# Fasim SSW Profile Cache Opt-In

This report characterizes the default-off real SSW query-profile cache. The cache reuses `ssw_init(...)` profiles by exact query/scoring key when `FASIM_SSW_PROFILE_CACHE=1` is set. Validation mode rebuilds the legacy profile and falls back on any score, endpoint, or CIGAR mismatch. `Saved build seconds` is an estimate from repeated cache hits of profiles whose miss build cost was measured.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

| Mode | Seconds | Speedup vs table | Digest match | Records |
| --- | --- | --- | --- | --- |
| table_only | 125.106000 | 1.00x | yes | 6546 |
| auto | 73.473700 | 1.70x | yes | 6546 |
| auto_cache | 57.786200 | 2.16x | yes | 6546 |
| auto_cache_validate | 100.667000 | 1.24x | yes | 6546 |

| Mode | Calls | Hits | Misses | Hit rate | Unique keys | Build seconds | Saved build seconds (est.) | Validate seconds | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto_cache | 979,282 | 979,281 | 1 | 100.00% | 1 | 0.000024 | 23.198200 | 0.000000 | 0 |
| auto_cache_validate | 979,282 | 979,281 | 1 | 100.00% | 1 | 0.000024 | 23.081700 | 41.802300 | 0 |

| Mode | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches |
| --- | --- | --- | --- | --- |
| auto_cache | 0 | 0 | 0 | 0 |
| auto_cache_validate | 0 | 0 | 0 | 0 |

| Auto seconds | Cache seconds | Delta seconds | Cache hit rate | Digest clean |
| --- | --- | --- | --- | --- |
| 73.473700 | 57.786200 | 15.687500 | 100.00% | yes |

## Decision

The default-off SSW profile cache is clean and faster in this run.

## Boundaries

```text
default enabled: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
