# Fasim Aligner Result-Cache Shadow

This checkpoint characterizes whether repeated identical `aligner.Align` requests inside
legacy `fastSIM_extend_from_scoreinfo` are common enough to justify a future exact result
cache. The shadow is observation-only: every legacy `aligner.Align` call still executes,
cached results are never used for runtime output, and duplicate request results are only
compared against the first observed result for the same exact key.

Boundary: no real result cache, no default enablement, no output change, no scoring,
threshold, non-overlap, GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior
change.

## Context

Previous fastSIM emit work ruled out larger precompute routes:

| Direction | Decision | Reason |
| --- | --- | --- |
| Full upfront precompute | no-go | `scoreInfo`-derived request generation overproduces state-skipped calls. |
| Bounded pipeline | no-go | Independent segments are too short; p50/p90/p99/max is 1/4/4/4. |
| Result-cache shadow | shadow-only | Contract is clean, but observed reuse is too low for a real path. |

The result-cache shadow differs from precompute: it does not predict future requests or
change fastSIM ordering. It only asks whether a legacy request has already been computed
with an identical key.

## Key

The exact request key includes:

| Component | Purpose |
| --- | --- |
| query hash and length | Distinguishes read/query content. |
| target hash and length | Distinguishes reference slice content. |
| filter and `maskLen` fields | Preserves aligner request shape. |
| scoring and gap fingerprint | Preserves scoring semantics. |
| AVX2 mode | Keeps SIMD mode-specific behavior out of a shared key. |

## Workloads

All rows are single-run characterizations. The shadow run keeps runtime output on the
legacy path, so digest equality means the shadow did not perturb output.

| Workload | Calls | Unique keys | Duplicate calls | Duplicate fraction | Est saved seconds | Memory estimate bytes | Mismatches | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hg38_chr21_H19 | 979,282 | 882,894 | 96,388 | 9.84% | 2.720290 | 232,819,224 | 0 | yes |
| hg38_chr11_H19 | 3,265,277 | 3,069,999 | 195,278 | 5.98% | 4.695390 | 809,553,314 | 0 | yes |

## Timing

| Workload | Table-only seconds | Final stack seconds | Result-cache shadow seconds | Align CPU seconds | Est saved seconds |
| --- | --- | --- | --- | --- | --- |
| hg38_chr21_H19 | 142.986000 | 28.535400 | 39.125700 | 24.973100 | 2.720290 |
| hg38_chr11_H19 | 450.720000 | 98.026300 | 130.334000 | 82.158100 | 4.695390 |

## Correctness

| Field | chr21 mismatches | chr11 mismatches | Notes |
| --- | --- | --- | --- |
| score | 0 | 0 | Duplicate request score matches first-seen result. |
| endpoint | 0 | 0 | Compares ref/read begin and end fields. |
| CIGAR | 0 | 0 | Compares CIGAR string. |
| digest | 0 | 0 | Runtime digest is unchanged because shadow output is not used. |

## Decision

The result-cache contract is clean, but the performance signal is not strong enough for
`FASIM_ALIGNER_RESULT_CACHE=1`.

On chr21, duplicates are 9.84% with about 2.72s estimated saved time and about 233MB of
estimated cache memory. On chr11, the duplicate fraction drops to 5.98%; absolute estimated
savings rise only to about 4.70s while estimated memory grows to about 810MB. A real cache
would add key hashing, lookup, insertion, result/CIGAR storage, memory pressure, and
validate/fallback overhead, so it would not capture the full estimate.

Do not implement a real result-cache path from this evidence. Keep the shadow as the
closing checkpoint for the fastSIM precompute/cache line unless a broader production
workload later shows much higher reuse with acceptable bounded memory.

## Boundaries

```text
real result cache added: no
skips aligner.Align in runtime path: no
uses cached result for runtime output: no
default enabled: no
scoring/threshold/non-overlap/output changed: no
GPU AUTO / SSW / AVX2 / ProfileContext changed: no
SIM-close / recovery changed: no
```
