# Fasim Speed Stack Review Summary

This is a docs-only review handoff for the current Fasim speed stack. It
summarizes the opt-in path that is currently supported by evidence and the
routes that should remain paused. It adds no code, no new environment variables,
and no default enablement.

## Recommended Opt-In Stack

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
```

`FASIM_TRANSFERSTRING_TABLE=1` is the stable transferString table opt-in.

`FASIM_GPU_DP_COLUMN_AUTO=1` is the large-workload GPU DP+column candidate. It
is size-gated: small workloads remain on the table path, and large workloads can
use the compact GPU path.

`FASIM_SSW_PROFILE_CACHE=1` is the strongest current real optimization candidate.
It reuses repeated SSW query profiles without changing the alignment algorithm,
endpoint/CIGAR reconstruction, scoring, thresholds, non-overlap, or output.

## Validation-Only Gates

```bash
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_SSW_PROFILE_CACHE_VALIDATE=1
```

These are correctness audit modes, not performance modes. The SSW profile cache
validation path rebuilds the legacy profile and falls back on any score,
endpoint, or CIGAR mismatch.

## hg38_chr21_H19 Median Result

The current 3-run median from `docs/fasim_ssw_profile_cache_characterization.md`:

| Mode | Seconds | Speedup vs table-only | Notes |
| --- | ---: | ---: | --- |
| table-only | 125.490000 | 1.00x | `FASIM_TRANSFERSTRING_TABLE=1` |
| AUTO | 73.225500 | 1.71x | `FASIM_GPU_DP_COLUMN_AUTO=1` |
| AUTO + SSW profile cache | 57.590500 | 2.18x | `FASIM_SSW_PROFILE_CACHE=1` |

Cache delta vs AUTO is `15.635000s`, or `1.27x` faster than AUTO alone.

SSW profile cache telemetry:

| Metric | Value |
| --- | ---: |
| cache calls | 979,282 |
| cache hits | 979,281 |
| cache misses | 1 |
| unique keys | 1 |
| score mismatches | 0 |
| endpoint mismatches | 0 |
| CIGAR mismatches | 0 |
| digest mismatches | 0 |
| fallbacks | 0 |
| output records | 6,546 |

The output digest is clean for table-only, AUTO, AUTO+cache, and
AUTO+cache+validate.

## Review Boundaries

```text
default behavior change: no
new environment variable: no
scoring/threshold/non-overlap change: no
output semantic change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
Accelign real path: no
```

The recommended stack is still an opt-in stack. Do not default it in this review
sequence.

## Paused Or No-Go Lines

The following routes should not be merged as real output paths in the current
speed stack:

| Route | Status | Reason |
| --- | --- | --- |
| Accelign endpoint path | no-go | same-score endpoint tie-policy mismatch with SSW/Fasim |
| Accelign endpoint-envelope bridge | no-go | interval/CIGAR reconstruction mismatch and negative savings |
| Accelign score-precheck real path | no-go | call-level side replay changed candidate/output state |
| Accelign full replacement | no-go | no full traceback/CIGAR/alignment string contract |
| pre-align filtering | no-go | insufficient safe savings |
| TopK lowering | paused | not the current bottleneck and risks scoreInfo coverage |
| threshold fallback deletion | paused | fallback remains a safety boundary |
| learned detector runtime path | paused | not a proven exact-safe runtime path |
| SIM-close recommendation/default | paused | not part of the current exact speed stack |

## Suggested Review Order

Review and merge the speed stack in dependency order:

1. transferString table stack
2. GPU DP column compact/AUTO stack
3. SSW profile reuse shadow and cache opt-in stack
4. SSW profile cache characterization
5. this docs-only review summary

## Current Recommendation

For large-workload performance evaluation, use:

```bash
FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN_AUTO=1 \
FASIM_SSW_PROFILE_CACHE=1
```

For correctness audits, add validation flags only during review or debugging:

```bash
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_SSW_PROFILE_CACHE_VALIDATE=1
```
