# Fasim Final Speed Stack Summary

This docs-only handoff summarizes the current Fasim speed stack after the
exact-column extend batch opt-in characterization. It adds no code, no new
environment variables, and no default enablement.

## Recommended Large-Workload Opt-In

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

`FASIM_TRANSFERSTRING_TABLE=1` is the stable transferString table opt-in.

`FASIM_GPU_DP_COLUMN_AUTO=1` is the size-gated GPU DP+column path. Small
workloads can remain on the table path; large workloads can use the compact GPU
path without changing output authority.

`FASIM_SSW_PROFILE_CACHE=1` reuses repeated SSW query profiles while preserving
legacy alignment scoring, endpoint, CIGAR, threshold, non-overlap, and output
semantics.

`FASIM_EXACT_COLUMN_EXTEND_BATCH=1` is the strongest current large-workload
opt-in. It batches exact-column extend work after the GPU DP column path and
keeps CPU fallback/validation authority available.

## Optional Add-Ons

```bash
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
```

`FASIM_SSW_AVX2=1` defaults to the characterized forward-only mode when no
`FASIM_SSW_AVX2_MODE` is set. It remains optional and default-off.

`FASIM_SSW_PROFILE_CONTEXT=1` is exact-clean and can stack with AVX2, but its
measured gain is smaller than the exact-column batch path. Keep it optional.

## Validation-Only Gates

```bash
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_SSW_PROFILE_CACHE_VALIDATE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1
```

These are correctness audit modes, not performance modes. In particular,
`FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` reruns CPU exact-column work as the
comparison authority, so its runtime is expected to return near the non-batch
final stack.

## hg38_chr21_H19 Median Result

The current 3-run median from
`docs/fasim_exact_column_extend_batch_characterization.md`:

| Mode | Seconds | Speedup vs table-only | Speedup vs final stack | Records | Digest clean |
| --- | ---: | ---: | ---: | ---: | --- |
| table-only | 131.579000 | 1.00x | n/a | 6,546 | yes |
| final stack | 51.030900 | 2.58x | 1.00x | 6,546 | yes |
| final stack + exact-column batch | 27.011300 | 4.87x | 1.89x | 6,546 | yes |
| final stack + exact-column batch + validate | 51.132300 | 2.57x | 1.00x | 6,546 | yes |

The clean output digest for all four modes is:

```text
sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26
```

Exact-column batch telemetry for the fastest mode:

| Metric | Value |
| --- | ---: |
| requests | 2,356 |
| cells | 33,125,360,000 |
| max cells/request | 14,060,000 |
| batch total seconds | 0.139044 |
| kernel seconds | 0.115943 |
| validate seconds | 0.000000 |
| score mismatches | 0 |
| endpoint mismatches | 0 |
| scoreInfo mismatches | 0 |
| digest mismatches | 0 |
| batch fallbacks | 0 |
| GPU fallbacks | 0 |

## Review Boundaries

```text
default behavior change: no
new environment variable: no
scoring/threshold/non-overlap change: no
output semantic change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext behavior change: no
SIM-close/recovery change: no
validation relaxation: no
Accelign real path: no
Parasail real path: no
AVX512: no
```

The speed stack remains opt-in. Do not default any of these paths from this
summary.

## Paused Or No-Go Lines

The following routes should not be merged as real output paths in the current
speed stack:

| Route | Status | Reason |
| --- | --- | --- |
| Accelign endpoint path | no-go | same-score endpoint tie-policy mismatch with SSW/Fasim |
| Accelign endpoint-envelope bridge | no-go | interval/CIGAR reconstruction mismatch and negative savings |
| Accelign score-precheck real path | no-go | call-level side replay changed candidate/output state |
| Accelign full replacement | no-go | no full traceback/CIGAR/alignment string contract |
| Parasail real path | no-go | score/endpoints clean, but CIGAR and digest mismatch in the current adapter |
| AVX512 | paused | AVX2 already showed path-specific behavior; no evidence to expand width yet |
| pre-align filtering | no-go | insufficient safe savings |
| TopK lowering | paused | not the current bottleneck and risks scoreInfo coverage |
| threshold fallback deletion | paused | fallback remains a safety boundary |
| learned detector runtime path | paused | not a proven exact-safe runtime path |
| SIM-close recommendation/default | paused | not part of the current exact speed stack |

## Suggested Review Order

Review and merge the speed stack in dependency order:

1. transferString table stack
2. GPU DP column compact/AUTO stack
3. SSW profile cache stack
4. AVX2 forward-only and ProfileContext optional add-ons
5. exact-column extend batch stack
6. this docs-only final summary

## Current Recommendation

For large-workload performance evaluation, use:

```bash
FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN_AUTO=1 \
FASIM_SSW_PROFILE_CACHE=1 \
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional add-ons can be layered when supported by the target CPU/workload:

```bash
FASIM_SSW_AVX2=1 \
FASIM_SSW_PROFILE_CONTEXT=1
```

For correctness audits, add validation flags only during review or debugging:

```bash
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_SSW_PROFILE_CACHE_VALIDATE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1
```

## Next Performance Step

Do not add another optimization directly from this summary. If performance work
continues, first run a post-batch decomposition to identify the largest remaining
component inside the 27s stack.
