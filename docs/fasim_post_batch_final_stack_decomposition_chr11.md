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

Workload: `hg38_chr11_H19`. Each mode uses 1 run(s); tables report medians.

## Performance

| Mode | Total seconds | Speedup vs table-only | Records | Digest | Digest match |
| --- | --- | --- | --- | --- | --- |
| table_only | 451.927000 | 1.00x | 20,607 | `sha256:0ae481985f0a060873f983cb80c2fb2b75a1fc4ff153b4492868376bb31d7310` | yes |
| final_stack | 91.022100 | 4.97x | 20,607 | `sha256:0ae481985f0a060873f983cb80c2fb2b75a1fc4ff153b4492868376bb31d7310` | yes |

## Activation And Exactness

| Area | Active / mode | Calls / records | Hits | Misses | Fallbacks | Mismatches |
| --- | --- | --- | --- | --- | --- | --- |
| GPU AUTO | 1 | 27 | n/a | n/a | 0 | score=0, column=0 |
| exact-column batch | 1 | 6,356 | n/a | n/a | 0 | score=0, endpoint=0, scoreInfo=0, digest=0 |
| AVX2 | mode=2 | forward=3,265,277, reverse=0 | n/a | n/a | 0 | n/a |
| SSW profile cache | 1 | 3,265,277 | 0 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |
| ProfileContext | 1 | 3,265,277 | 3,265,276 | 1 | 0 | score=0, endpoint=0, cigar=0, digest=0 |

Note: with ProfileContext active, the profile cache still backs the context, but the per-call hot reuse is represented by ProfileContext hit/miss counters. The remaining SSW profile cache miss is the initial profile build.

## Top-Level Stages

| Component | Seconds | Percent of total | Calls / bytes | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| window generation | 5.108000 | 5.61% | 27,460 | top-level | cutSequence, transferString, source transform, encoded target build |
| GPU DP column total | 2.820350 | 3.10% | 27 | inclusive | GPU DP+column path wall time including compact transfer and CPU postprocessing envelope |
| GPU kernel | 2.696020 | 2.96% | 109,840 | nested | device DP+column kernel work inside GPU DP column total |
| GPU scoreInfo reconstruct | 0.470155 | 0.52% | 1,964,093 | post-GPU | CPU reconstruction of compact GPU scoreInfo records |
| exact-column extend stage | 0.377975 | 0.42% | 6,356 | post-GPU | exact-column extend stage timer; equals the batch backend envelope when batch path is active |
| exact-column batch total | 0.377975 | 0.42% | 6,356 | post-GPU | real batched exact-column extend path, including pack/transfer/kernel/unpack/apply |
| exact-column batch kernel | 0.325825 | 0.36% | 89,365,360,000 | nested | device exact-column extend kernel inside batch total |
| fastSIM emit wrapper | 78.799800 | 86.57% | 64,616 | post-GPU | CPU emit / extension wrapper for scoreInfo-derived candidates |
| non-overlap | 0.000000 | 0.00% | n/a | top-level | final overlap pruning stage |
| caller output | 0.062492 | 0.07% | 20,607 | top-level | caller-side output formatting/write outside fastSIM record construction |

H2D bytes: `549,200,000`
D2H bytes: `224,952,320`

## Exact-Column Batch Breakdown

| Component | Seconds | Percent of total | Requests / cells | Notes |
| --- | --- | --- | --- | --- |
| batch total | 0.377975 | 0.42% | 6,356 | inclusive pack, transfer, kernel, unpack, and apply time |
| pack | 0.006221 | 0.01% | 6,356 | host request packing |
| H2D | 0.005214 | 0.01% | n/a | host-to-device transfer |
| kernel | 0.325825 | 0.36% | 89,365,360,000 | device batched exact-column work |
| D2H | 0.016476 | 0.02% | n/a | device-to-host transfer |
| unpack | 0.076578 | 0.08% | 6,356 | host result unpacking |
| apply | 0.001749 | 0.00% | 6,356 | feeding batch results into the existing downstream path |

Batch cells: `89,365,360,000`
Max cells/request: `14,060,000`

## CPU Emit And Align Decomposition

| Component | Seconds | Percent | Calls | Scope | Notes |
| --- | --- | --- | --- | --- | --- |
| fastSIM inclusive | 78.703100 | 86.47% | 109,840 | wrapper | full `fastSIM_extend_from_scoreinfo` inclusive time, shown as percent of total |
| fastSIM alignment reconstruction | 76.432400 | 83.97% | 3,265,277 | nested | `aligner.Align` over scoreInfo-derived local windows, shown as percent of total |
| fastSIM record build | 1.448080 | 1.59% | 64,616 | exclusive | record construction, convertMyTriplex, CIGAR traversal, identity/stability work |
| aligner.Align | 76.375300 | 100.00% | 3,265,277 | wrapper | CPU alignment reconstruction authority |
| aligner setup | 10.986500 | 14.38% | 3,265,277 | nested | strlen, allocation, translate, cache/context lookup |
| ProfileContext saved estimate | 23.470830 | n/a | 3,265,277 | telemetry estimate | query translate plus lookup seconds avoided by active ProfileContext |
| ssw_align | 63.763600 | 83.49% | 3,265,277 | nested | forward score/end, reverse-start, endpoint bookkeeping, and CIGAR section |
| forward score/end | 37.817700 | 49.52% | 3,265,277 | nested | AVX2 forward-only local score and endpoint search |
| reverse-start | 18.106500 | 23.71% | 3,265,277 | nested | SSE2 reverse substring alignment to recover begin coordinates |
| CIGAR section | 5.896470 | 7.72% | 3,265,277 | nested inclusive | CIGAR preparation plus banded traceback; includes banded_sw |
| banded_sw | 5.783130 | 7.57% | 3,265,277 | nested | traceback DP inside CIGAR section |

Percent basis follows the row note: fastSIM rows use percent of total runtime, while `aligner.Align` subrows use percent of `aligner.Align`.

## Decision

Largest measured candidate component: `fastSIM emit wrapper` at 78.799800s (86.57% of total).
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
