# Fasim Final Speed Stack Decomposition

This telemetry-only report decomposes the fastest current opt-in Fasim speed stack after AVX2 forward-only and SSW ProfileContext were characterized. It does not add optimization logic or change output, scoring, threshold, non-overlap, GPU AUTO, SIM-close, recovery, or validation behavior.

Final stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
```

`FASIM_ALIGNER_ALIGN_INTERNALS=1` is enabled only to collect decomposition telemetry.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Mode | Total seconds | Speedup vs table-only | Records | Digest | Digest match |
| --- | --- | --- | --- | --- | --- |
| table_only | 133.096000 | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes |
| final_stack | 51.343300 | 2.59x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes |

## Activation And Exactness

| Area | Active / mode | Calls / records | Hits | Misses | Fallbacks | Mismatches |
| --- | --- | --- | --- | --- | --- | --- |
| GPU AUTO | 1 | 9 | n/a | n/a | 0 | score=0, column=0 |
| AVX2 | mode=2 | forward=979,282, reverse=0 | n/a | n/a | 0 | n/a |
| SSW profile cache | 1 | 979,282 | 0 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |
| ProfileContext | 1 | 979,282 | 979,281 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |

Note: with ProfileContext active, the profile cache still backs the context, but the per-call hot reuse is represented by ProfileContext hit/miss counters. The remaining SSW profile cache miss is the initial profile build.

## Top-Level Stages

| Component | Seconds | Percent of total | Calls / bytes | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| window generation | 1.438420 | 2.80% | 8,209 | top-level | cutSequence, transferString, source transform, encoded target build |
| GPU DP column total | 0.798588 | 1.56% | 9 | inclusive | GPU DP+column path wall time including compact transfer and CPU postprocessing envelope |
| GPU kernel | 0.758698 | 1.48% | 32,836 | nested | device DP+column kernel work inside GPU DP column total |
| GPU scoreInfo reconstruct | 0.152563 | 0.30% | 600,667 | post-GPU | CPU reconstruction of compact GPU scoreInfo records |
| exact-column extend | 24.300400 | 47.33% | 2,356 | post-GPU | CPU exact-column extension after compact GPU scoring |
| fastSIM emit wrapper | 23.056800 | 44.91% | 19,511 | post-GPU | CPU emit / extension wrapper for scoreInfo-derived candidates |
| non-overlap | 0.000000 | 0.00% | n/a | top-level | final overlap pruning stage |
| caller output | 0.018037 | 0.04% | 6,546 | top-level | caller-side output formatting/write outside fastSIM record construction |

H2D bytes: `164,180,000`
D2H bytes: `67,248,128`

## CPU Emit And Align Decomposition

| Component | Seconds | Percent | Calls | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| fastSIM inclusive | 23.029000 | 44.85% | 32,836 | wrapper | full `fastSIM_extend_from_scoreinfo` inclusive time, shown as percent of total |
| fastSIM alignment reconstruction | 22.362200 | 43.55% | 979,282 | nested | `aligner.Align` over scoreInfo-derived local windows, shown as percent of total |
| fastSIM record build | 0.433370 | 0.84% | 19,511 | exclusive | record construction, convertMyTriplex, CIGAR traversal, identity/stability work |
| aligner.Align | 22.345400 | 100.00% | 979,282 | wrapper | CPU alignment reconstruction authority |
| aligner setup | 3.229240 | 14.45% | 979,282 | nested | strlen, allocation, translate, cache/context lookup |
| ProfileContext saved estimate | 7.019490 | n/a | 979,282 | telemetry estimate | query translate plus lookup seconds avoided by active ProfileContext |
| ssw_align | 18.621200 | 83.33% | 979,282 | nested | forward score/end, reverse-start, endpoint bookkeeping, and CIGAR section |
| forward score/end | 11.075200 | 49.56% | 979,282 | nested | AVX2 forward-only local score and endpoint search |
| reverse-start | 5.276650 | 23.61% | 979,282 | nested | SSE2 reverse substring alignment to recover begin coordinates |
| CIGAR section | 1.734490 | 7.76% | 979,282 | nested inclusive | CIGAR preparation plus banded traceback; includes banded_sw |
| banded_sw | 1.701690 | 7.62% | 979,282 | nested | traceback DP inside CIGAR section |

Percent basis follows the row note: fastSIM rows use percent of total runtime, while `aligner.Align` subrows use percent of `aligner.Align`.

## Decision

Largest measured candidate component: `exact-column extend` at 24.300400s (47.33% of total).
Revisit batched exact-column extend as a shadow, keeping CPU output authority.

## Boundaries

```text
optimization logic added: no
default AVX2/ProfileContext change: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
