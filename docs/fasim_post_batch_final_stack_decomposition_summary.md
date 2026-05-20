# Fasim Post-Batch Final Stack Decomposition Summary

This docs-only summary consolidates the post-batch decomposition runs for
`hg38_chr21_H19` and `hg38_chr11_H19`. It adds no optimization logic, no new
environment variables, and no default enablement.

Post-batch stack under decomposition:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
```

`FASIM_ALIGNER_ALIGN_INTERNALS=1` is enabled only for telemetry collection.

## Workload Summary

| Workload | Table-only | Post-batch final stack | Speedup | Records | Digest match | Fallbacks / mismatches |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| hg38_chr21_H19 | 131.974000 | 27.336500 | 4.83x | 6,546 | yes | 0 |
| hg38_chr11_H19 | 451.927000 | 91.022100 | 4.97x | 20,607 | yes | 0 |

Detailed reports:

- `docs/fasim_post_batch_final_stack_decomposition.md`
- `docs/fasim_post_batch_final_stack_decomposition_chr11.md`

## Largest Remaining Component

| Workload | Largest measured component | Seconds | Percent of total | Next decision |
| --- | --- | ---: | ---: | --- |
| hg38_chr21_H19 | fastSIM emit wrapper | 23.159400 | 84.72% | decompose CPU emit / alignment reconstruction |
| hg38_chr11_H19 | fastSIM emit wrapper | 78.799800 | 86.57% | decompose CPU emit / alignment reconstruction |

Both workloads point to the same next bottleneck family. The exact-column batch
path is no longer the large remaining block.

## Exact-Column Batch Status

| Workload | Requests | Cells | Batch total | Kernel | Percent of total | Fallbacks / mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| hg38_chr21_H19 | 2,356 | 33,125,360,000 | 0.138365 | 0.115769 | 0.51% | 0 |
| hg38_chr11_H19 | 6,356 | 89,365,360,000 | 0.377975 | 0.325825 | 0.42% | 0 |

The post-batch results confirm that `FASIM_EXACT_COLUMN_EXTEND_BATCH=1` removed
the previous exact-column extend bottleneck. Transfer, unpack, and apply costs
are small relative to total runtime on both workloads.

## CPU Emit And Align Snapshot

| Workload | fastSIM inclusive | alignment reconstruction | aligner.Align | ssw_align | forward score/end | reverse-start | CIGAR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hg38_chr21_H19 | 23.132100 | 22.464700 | 22.448000 | 18.742400 | 11.116800 | 5.319520 | 1.739220 |
| hg38_chr11_H19 | 78.703100 | 76.432400 | 76.375300 | 63.763600 | 37.817700 | 18.106500 | 5.896470 |

The remaining CPU emit cost is dominated by alignment reconstruction, and
`ssw_align` remains the largest nested part of `aligner.Align`.

## Decision

Do not add another optimization directly from this result. The next
performance PR, if any, should first decompose CPU emit / alignment
reconstruction in the batch-enabled stack. Candidate follow-up questions:

```text
Is the remaining cost mostly ssw_align forward score/end?
Is reverse-start now large enough for a shortcut/cache shadow?
Is CIGAR still too small to matter?
Is output/record construction still secondary?
```

## Boundaries

```text
optimization logic added: no
default behavior change: no
new environment variable: no
scoring/threshold/non-overlap change: no
output semantic change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext behavior change: no
SIM-close/recovery change: no
validation relaxation: no
```
