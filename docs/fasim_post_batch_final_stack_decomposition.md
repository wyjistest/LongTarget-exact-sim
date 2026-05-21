# Fasim Post-Batch Final Stack Decomposition

This telemetry-only report decomposes the post-batch Fasim speed stack after `FASIM_EXACT_COLUMN_EXTEND_BATCH=1` removed the previous exact-column extend bottleneck. It does not add optimization logic or change output, scoring, threshold, non-overlap, GPU AUTO, SSW, SIM-close, recovery, or validation behavior.

Post-batch stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
```

`FASIM_ALIGNER_ALIGN_INTERNALS=1` is enabled only to collect decomposition telemetry.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Mode | Total seconds | Speedup vs table-only | Records | Digest | Digest match |
| --- | --- | --- | --- | --- | --- |
| table_only | 131.974000 | 1.00x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes |
| final_stack | 27.336500 | 4.83x | 6,546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes |

## Activation And Exactness

| Area | Active / mode | Calls / records | Hits | Misses | Fallbacks | Mismatches |
| --- | --- | --- | --- | --- | --- | --- |
| GPU AUTO | 1 | 9 | n/a | n/a | 0 | score=0, column=0 |
| exact-column batch | 1 | 2,356 | n/a | n/a | 0 | score=0, endpoint=0, scoreInfo=0, digest=0 |
| AVX2 | mode=2 | forward=979,282, reverse=0 | n/a | n/a | 0 | n/a |
| SSW profile cache | 1 | 979,282 | 0 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |
| ProfileContext | 1 | 979,282 | 979,281 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |

Note: with ProfileContext active, the profile cache still backs the context, but the per-call hot reuse is represented by ProfileContext hit/miss counters. The remaining SSW profile cache miss is the initial profile build.

## Top-Level Stages

| Component | Seconds | Percent of total | Calls / bytes | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| window generation | 1.490360 | 5.45% | 8,209 | top-level | cutSequence, transferString, source transform, encoded target build |
| GPU DP column total | 0.854681 | 3.13% | 9 | inclusive | GPU DP+column path wall time including compact transfer and CPU postprocessing envelope |
| GPU kernel | 0.816235 | 2.99% | 32,836 | nested | device DP+column kernel work inside GPU DP column total |
| GPU scoreInfo reconstruct | 0.138403 | 0.51% | 600,667 | post-GPU | CPU reconstruction of compact GPU scoreInfo records |
| exact-column extend stage | 0.138365 | 0.51% | 2,356 | post-GPU | exact-column extend stage timer; equals the batch backend envelope when batch path is active |
| exact-column batch total | 0.138365 | 0.51% | 2,356 | post-GPU | real batched exact-column extend path, including pack/transfer/kernel/unpack/apply |
| exact-column batch kernel | 0.115769 | 0.42% | 33,125,360,000 | nested | device exact-column extend kernel inside batch total |
| fastSIM emit wrapper | 23.159400 | 84.72% | 19,511 | post-GPU | CPU emit / extension wrapper for scoreInfo-derived candidates |
| non-overlap | 0.000000 | 0.00% | n/a | top-level | final overlap pruning stage |
| caller output | 0.016543 | 0.06% | 6,546 | top-level | caller-side output formatting/write outside fastSIM record construction |

H2D bytes: `164,180,000`
D2H bytes: `67,248,128`

## Exact-Column Batch Breakdown

| Component | Seconds | Percent of total | Requests / cells | Notes |
| --- | --- | --- | --- | --- |
| batch total | 0.138365 | 0.51% | 2,356 | inclusive pack, transfer, kernel, unpack, and apply time |
| pack | 0.002509 | 0.01% | 2,356 | host request packing |
| H2D | 0.001770 | 0.01% | n/a | host-to-device transfer |
| kernel | 0.115769 | 0.42% | 33,125,360,000 | device batched exact-column work |
| D2H | 0.006262 | 0.02% | n/a | device-to-host transfer |
| unpack | 0.027851 | 0.10% | 2,356 | host result unpacking |
| apply | 0.000514 | 0.00% | 2,356 | feeding batch results into the existing downstream path |

Batch cells: `33,125,360,000`
Max cells/request: `14,060,000`

## CPU Emit And Align Decomposition

| Component | Seconds | Percent | Calls | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| fastSIM inclusive | 23.132100 | 84.62% | 32,836 | wrapper | full `fastSIM_extend_from_scoreinfo` inclusive time, shown as percent of total |
| fastSIM alignment reconstruction | 22.464700 | 82.18% | 979,282 | nested | `aligner.Align` over scoreInfo-derived local windows, shown as percent of total |
| fastSIM record build | 0.429920 | 1.57% | 19,511 | exclusive | record construction, convertMyTriplex, CIGAR traversal, identity/stability work |
| aligner.Align | 22.448000 | 100.00% | 979,282 | wrapper | CPU alignment reconstruction authority |
| aligner setup | 3.223340 | 14.36% | 979,282 | nested | strlen, allocation, translate, cache/context lookup |
| ProfileContext saved estimate | 5.078550 | n/a | 979,282 | telemetry estimate | query translate plus lookup seconds avoided by active ProfileContext |
| ssw_align | 18.742400 | 83.49% | 979,282 | nested | forward score/end, reverse-start, endpoint bookkeeping, and CIGAR section |
| forward score/end | 11.116800 | 49.52% | 979,282 | nested | AVX2 forward-only local score and endpoint search |
| reverse-start | 5.319520 | 23.70% | 979,282 | nested | SSE2 reverse substring alignment to recover begin coordinates |
| CIGAR section | 1.739220 | 7.75% | 979,282 | nested inclusive | CIGAR preparation plus banded traceback; includes banded_sw |
| banded_sw | 1.706190 | 7.60% | 979,282 | nested | traceback DP inside CIGAR section |

Percent basis follows the row note: fastSIM rows use percent of total runtime, while `aligner.Align` subrows use percent of `aligner.Align`.

## Decision

Largest measured candidate component: `fastSIM emit wrapper` at 23.159400s (84.72% of total).
Decompose CPU emit and alignment reconstruction before any real-path change.

## Boundaries

```text
optimization logic added: no
default batch enablement change: no
default AVX2/ProfileContext change: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
