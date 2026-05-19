# Fasim SSW ProfileContext Characterization

This report repeatedly characterizes the default-off real SSW `ProfileContext` opt-in from `FASIM_SSW_PROFILE_CONTEXT=1`. It adds no optimization logic and does not change defaults. `ProfileContext` is only active with `FASIM_SSW_PROFILE_CACHE=1`; validation mode reruns the legacy per-call lookup/translation path and falls back on score, endpoint, CIGAR, or digest mismatch.

Measured modes:

```bash
# AUTO + cache
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1

# AUTO + cache + ProfileContext
FASIM_SSW_PROFILE_CONTEXT=1

# AUTO + cache + ProfileContext validate
FASIM_SSW_PROFILE_CONTEXT_VALIDATE=1
```

Each workload uses 3 run(s); tables report medians.

| Workload | Records | AUTO+cache s | AUTO+cache+context s | Delta s | Context/AUTO+cache | Validate s | Digest clean | Output digest | Context exercised |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 6 | 0.282644 | 0.256532 | 0.026112 | 1.10x | 0.254937 | yes | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 | yes |
| medium_synthetic | 48 | 0.265335 | 0.286708 | -0.021373 | 0.93x | 0.334156 | yes | sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae | yes |
| window_heavy_synthetic | 192 | 0.416814 | 0.410804 | 0.006010 | 1.01x | 0.537975 | yes | sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c | yes |
| hg38_chr21_H19 | 6,546 | 58.144600 | 56.764600 | 1.380000 | 1.02x | 85.741700 | yes | sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26 | yes |

| Workload | Aligner s | Align calls | Context calls | Hits | Misses | Hit rate | Unique keys | Query saved s | Lookup saved s | Validate overhead s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 0.004606 | 156 | 156 | 155 | 1 | 99.36% | 1 | 0.000162 | 0.000764 | 0.004389 |
| medium_synthetic | 0.035287 | 1,248 | 1,248 | 1,247 | 1 | 99.92% | 1 | 0.001212 | 0.005530 | 0.035292 |
| window_heavy_synthetic | 0.140567 | 4,992 | 4,992 | 4,991 | 1 | 99.98% | 1 | 0.005246 | 0.024586 | 0.140665 |
| hg38_chr21_H19 | 28.037900 | 979,282 | 979,282 | 979,281 | 1 | 100.00% | 1 | 1.028250 | 4.720130 | 28.127200 |

| Workload | Score mismatches | Endpoint mismatches | CIGAR mismatches | Digest mismatches | Fallbacks |
| --- | --- | --- | --- | --- | --- |
| tiny | 0 | 0 | 0 | 0 | 0 |
| medium_synthetic | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | 0 | 0 | 0 | 0 | 0 |
| hg38_chr21_H19 | 0 | 0 | 0 | 0 | 0 |

## Decision

`FASIM_SSW_PROFILE_CONTEXT=1` is exact-clean, but median runtime was not faster on medium_synthetic. Keep it optional and do not promote it to the core recommended speed stack from this report.

## Boundaries

```text
new optimization logic: no
default enabled: no
requires FASIM_SSW_PROFILE_CACHE=1: yes
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
Accelign real path change: no
validation relaxation: no
```
