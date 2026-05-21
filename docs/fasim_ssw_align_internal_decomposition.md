# Fasim SSW Align Internal Decomposition

This PR adds telemetry only. It decomposes the remaining `aligner.Align` setup
and `ssw_align` internals after the current speed stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
```

It does not add an optimization, change output, scoring, thresholds,
non-overlap behavior, GPU AUTO policy, SIM-close, recovery, or validation
behavior.

## New Telemetry

`aligner.Align` setup:

| Metric | Meaning |
| --- | --- |
| `fasim_aligner_setup_seconds` | strlen, query/ref allocation, query/ref translation, and profile cache lookup/build |
| `fasim_aligner_strlen_seconds` | query length discovery |
| `fasim_aligner_query_alloc_seconds` | per-call translated query allocation |
| `fasim_aligner_query_translate_seconds` | query ASCII-to-SSW alphabet translation |
| `fasim_aligner_ref_translate_seconds` | target ASCII-to-SSW alphabet translation |
| `fasim_aligner_profile_cache_lookup_seconds` | exact profile-key lookup, including miss build path |
| `fasim_aligner_profile_cache_hit_seconds` | hit-only lookup time |
| `fasim_aligner_profile_cache_miss_seconds` | miss lookup plus profile build insertion |

`ssw_align` internals:

| Metric | Meaning |
| --- | --- |
| `fasim_ssw_align_seconds` | existing outer `ssw_align(...)` timer |
| `fasim_ssw_forward_score_end_seconds` | forward local score/end search |
| `fasim_ssw_reverse_start_seconds` | reverse substring alignment used to recover begin coordinates |
| `fasim_ssw_cigar_seconds` | CIGAR preparation and traceback section |
| `fasim_ssw_banded_sw_seconds` | nested `banded_sw(...)` time inside the CIGAR section |
| `fasim_ssw_endpoint_bookkeeping_seconds` | copying forward/reverse best cells into returned endpoint fields |
| `fasim_ssw_byte_path_seconds` | SSE2 byte kernel time, forward plus reverse |
| `fasim_ssw_word_path_seconds` | SSE2 word kernel time, including saturation fallback |
| `fasim_ssw_fallback_calls` | byte-score saturation retries on word profile |
| `fasim_ssw_forward_calls` | forward score/end calls |
| `fasim_ssw_reverse_calls` | reverse-start calls |
| `fasim_ssw_banded_sw_calls` | `banded_sw(...)` calls |

`fasim_ssw_cigar_seconds` includes `fasim_ssw_banded_sw_seconds`; do not add
those two together as independent components.

## Small Fixture Smoke

The check target uses the existing compact hg38 soft-mask fixture plus `H19.fa`.
It is only a smoke test for telemetry wiring and exactness, not a large-workload
performance conclusion.

| Metric | Value |
| --- | ---: |
| digest match vs table-only | yes |
| records | 0 |
| aligner calls | 232 |
| cache hits | 231 |
| cache misses | 1 |
| unique cache keys | 1 |
| score mismatches | 0 |
| endpoint mismatches | 0 |
| CIGAR mismatches | 0 |
| digest mismatches | 0 |
| profile-cache fallbacks | 0 |

Observed component smoke table:

| Component | Seconds | Calls | Percent of aligner | Notes |
| --- | ---: | ---: | ---: | --- |
| aligner setup | 0.001237 | 232 | 11.21% | strlen, allocation, query/ref translate, profile cache lookup/build |
| profile cache lookup | 0.000821 | 232 | 7.44% | includes one miss build path |
| `ssw_align` | 0.009642 | 232 | 87.36% | forward, reverse-start, endpoint bookkeeping, CIGAR |
| forward score/end | 0.005361 | 232 | 48.57% | initial local score/end |
| reverse-start | 0.003168 | 232 | 28.70% | begin-coordinate recovery |
| CIGAR section | 0.001070 | 232 | 9.70% | includes `banded_sw` |
| `banded_sw` | 0.001062 | 232 | 9.62% | nested traceback DP |
| endpoint bookkeeping | 0.000008 | 232 | 0.07% | endpoint field updates |

## Real Workload Run

Run the hg38 chr21 + H19 decomposition with:

```bash
FASIM_GPU_DP_COLUMN_AUTO_HG38_DNA=/path/to/hg38_chr21.fa \
FASIM_GPU_DP_COLUMN_AUTO_HG38_RNA=/path/to/H19.fa \
FASIM_GPU_DP_COLUMN_AUTO_HG38_REPEAT=1 \
make benchmark-fasim-ssw-align-internal-decomposition
```

The benchmark script writes:

```text
docs/fasim_ssw_align_internal_decomposition.md
```

Use `FASIM_GPU_DP_COLUMN_AUTO_HG38_REPEAT=3` for median review data when time
allows.

## Decision Guide

If `query translate` or setup remains material, the next low-risk path is a
default-off `TranslatedQuery/ProfileContext` cache shadow.

If forward score/end dominates `ssw_align`, continue AVX2/Parasail or other CPU
SIMD exploration only as exact-clean shadow or default-off opt-in.

If reverse-start dominates, focus on reverse-start cache or shortcut shadows.

If CIGAR/`banded_sw` dominates, focus on CIGAR reconstruction and traceback
cost.

If costs are distributed, keep the current speed stack and avoid narrow
micro-optimizations.

## Boundaries

```text
real optimization added: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
Accelign real path: no
```
