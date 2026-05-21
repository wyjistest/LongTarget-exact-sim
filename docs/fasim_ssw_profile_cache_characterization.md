# Fasim SSW Profile Cache Characterization

This report repeatedly characterizes the default-off real SSW query-profile cache from `FASIM_SSW_PROFILE_CACHE=1`. It adds no optimization logic and does not change defaults. Validation mode uses `FASIM_SSW_PROFILE_CACHE_VALIDATE=1` to rebuild the legacy profile and fall back on any score, endpoint, or CIGAR mismatch.

Each workload uses 3 run(s); tables report medians.

| Workload | Records | table-only s | AUTO s | AUTO+cache s | Cache delta s | AUTO+cache/table | AUTO+cache/AUTO | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 6 | 0.035544 | 0.037830 | 0.015448 | 0.022382 | 2.30x | 2.45x | yes |
| medium_synthetic | 48 | 0.142053 | 0.126722 | 0.126517 | 0.000205 | 1.12x | 1.00x | yes |
| window_heavy_synthetic | 192 | 0.531936 | 0.491394 | 0.398095 | 0.093299 | 1.34x | 1.23x | yes |
| hg38_chr21_H19 | 6,546 | 125.490000 | 73.225500 | 57.590500 | 15.635000 | 2.18x | 1.27x | yes |

| Workload | Calls | Align calls | Hits | Misses | Hit rate | Unique keys | Saved build s (est.) | Validate s | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 0 | 0 | 0 | 0 | n/a | 0 | 0.000000 | 0.000000 | 0 |
| medium_synthetic | 0 | 0 | 0 | 0 | n/a | 0 | 0.000000 | 0.000000 | 0 |
| window_heavy_synthetic | 4,992 | 4,992 | 4,991 | 1 | 99.98% | 1 | 0.130355 | 0.213058 | 0 |
| hg38_chr21_H19 | 979,282 | 979,282 | 979,281 | 1 | 100.00% | 1 | 21.344400 | 41.696400 | 0 |

| Workload | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches |
| --- | --- | --- | --- | --- |
| tiny | 0 | 0 | 0 | 0 |
| medium_synthetic | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | 0 | 0 | 0 | 0 |
| hg38_chr21_H19 | 0 | 0 | 0 | 0 |

## Decision

The cache is exact-clean and faster across all characterized workloads.

## Boundaries

```text
new optimization logic: no
default enabled: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
