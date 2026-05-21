# Fasim fastSIM ScoreInfo Emit Decomposition

This telemetry-only report decomposes the CPU-side `fastSIM_extend_from_scoreinfo` / emit path under `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1`. It does not add optimization logic and does not change GPU kernels, AUTO policy, scoring, thresholding, non-overlap, output semantics, SIM-close, or recovery behavior.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| auto | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1` |
| auto_validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Performance

| Observed windows | Observed cells | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Digest | Records | AUTO digest match | AUTO+validate digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32,836 | 461,674,160,000 | 124.763000 | 72.812800 | 1.71x | 176.924000 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | 6546 | yes | yes |

## fastSIM Inclusive / Exclusive

| Mode | GPU emit wrapper seconds | fastSIM inclusive seconds | fastSIM exclusive seconds | external exact-column seconds | calls | scoreInfo records | records considered | records emitted | records rejected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 44.473400 | 44.447300 | 44.447300 | 24.680300 | 32,836 | 600,667 | 600,667 | 19,511 | 376,741 |
| auto_validate | 44.696200 | 44.669700 | 44.669700 | 49.734800 | 32,836 | 600,667 | 600,667 | 19,511 | 376,741 |

`fastSIM inclusive` measures only `fastSIM_extend_from_scoreinfo`; the P1 exact-column extend happens before that call and is reported as an external comparator, not a nested timer.

## Component Breakdown

| Component | Seconds | Percent of emit | Inclusive or exclusive | Notes |
| --- | --- | --- | --- | --- |
| alignment reconstruction | 43.795600 | 98.48% | exclusive | `aligner.Align` over scoreInfo-derived local windows. |
| record build / convertMyTriplex | 0.425469 | 0.96% | exclusive | Triplex construction, CIGAR traversal, identity/stability work. |
| duplicate / overlap bookkeeping | 0.073750 | 0.17% | exclusive | Sort/unique phases inside `fastSIM_extend_from_scoreinfo`. |
| candidate filter | 0.008942 | 0.02% | exclusive | Alignment score/nonzero checks and final threshold checks. |
| vector push | 0.006670 | 0.01% | exclusive | Final `triplex_list.push_back` loop. |
| scoreInfo scan | 0.008864 | 0.02% | exclusive | Outer scoreInfo record accounting. |
| allocation | 0.000550 | 0.00% | exclusive | Local container construction/reserve-visible allocation envelope. |
| output stage | 0.012558 | 0.03% | exclusive | Final stage before caller-side file formatting/write. |
| string formatting | 0.000000 | 0.00% | alias | Currently aliases materialized alignment string work inside record build. |
| CIGAR | 0.434201 | 0.98% | alias | Currently aliases CIGAR-derived work inside record build. |
| external exact-column extend | 24.680300 | 55.49% | external | P1 exact-column cost before `fastSIM_extend_from_scoreinfo`. |

## Answers

1. Exact-column extend is external to fastSIM and costs 24.680300s.
2. Inside fastSIM, alignment reconstruction costs 43.795600s and record construction costs 0.425469s.
3. Output/string formatting is not separately material at the caller file-write layer in this profile; string formatting aliases record build at 0.000000s.
4. Vector push is 0.006670s, not a leading cost.
5. Duplicate/overlap bookkeeping is 0.073750s.
6. Next PR recommendation: alignment reconstruction should be the next target.

## Boundaries

```text
optimization logic: no
GPU kernel or AUTO policy change: no
scoring/threshold/non-overlap/output semantic change: no
SIM-close/recovery change: no
validation relaxation: no
```
