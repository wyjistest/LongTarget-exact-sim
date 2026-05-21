# Fasim GPU DP+column Mismatch Taxonomy

Base branch:

```text
fasim-gpu-dp-column-characterization
```

This stacked PR adds diagnostics for `FASIM_GPU_DP_COLUMN=1` validation
mismatches. It does not optimize the GPU path, enable it by default, relax
validation, or change scoring/threshold/non-overlap/output behavior.

## Debug Controls

```text
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1
FASIM_GPU_DP_COLUMN_DEBUG_MAX_WINDOWS=<n>
FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX=<n>
```

`FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1` enables mismatch taxonomy telemetry. The
window filters only limit detailed stderr samples; they do not skip validation
or change fallback behavior.

## Added Telemetry

```text
fasim_gpu_dp_column_debug_enabled
fasim_gpu_dp_column_first_mismatch_window
fasim_gpu_dp_column_first_mismatch_column
fasim_gpu_dp_column_first_mismatch_cpu_score
fasim_gpu_dp_column_first_mismatch_gpu_score
fasim_gpu_dp_column_first_mismatch_cpu_position
fasim_gpu_dp_column_first_mismatch_gpu_position
fasim_gpu_dp_column_first_mismatch_cpu_count
fasim_gpu_dp_column_first_mismatch_gpu_count
fasim_gpu_dp_column_first_mismatch_tie
fasim_gpu_dp_column_score_delta_max
fasim_gpu_dp_column_scoreinfo_mismatches
fasim_gpu_dp_column_tie_mismatches
fasim_gpu_dp_column_position_mismatches
fasim_gpu_dp_column_topk_truncated_windows
fasim_gpu_dp_column_topk_overflow_windows
fasim_gpu_dp_column_pre_topk_mismatches
fasim_gpu_dp_column_post_topk_mismatches
fasim_gpu_dp_column_debug_windows_examined
```

`pre_topk_mismatches` means the raw CPU max score and GPU max score disagree.
`post_topk_mismatches` means raw max scores agree, but the CPU `scoreInfo` list
differs from the GPU-derived bounded top-K summary after position-order
compaction.

## HumanLncAtlas Debug Runs

Environment:

```text
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1
```

| Workload | Score mismatches | scoreInfo mismatches | pre-topK | post-topK | topK overflow | topK truncated | tie mismatches | position mismatches | fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| human_lnc_atlas_17kb_target | 0 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 12 |
| human_lnc_atlas_508kb_target | 0 | 12 | 0 | 12 | 12 | 11 | 0 | 12 | 412 |

Canonical output digests remained stable because validation fallback keeps
CPU/Fasim as final output authority.

## First Mismatch Samples

17kb first mismatch:

```text
window=3
first_column=7
gpu_count=44
cpu_count=51
minScore=72
gpuMaxScore=90
cpuMaxScore=90
gpu=(76,771)
cpu=(77,877)
```

508kb first mismatch:

```text
window=5
first_column=12
gpu_count=46
cpu_count=52
minScore=68
gpuMaxScore=86
cpuMaxScore=86
gpu=(75,1412)
cpu=(69,1338)
```

The detailed stderr samples show matching prefixes before the first mismatch,
then GPU lists skip lower-score CPU `scoreInfo` entries and shift later entries
forward. Example from the 17kb run:

```text
idx=5 gpu=(78,749) cpu=(78,749)
idx=6 gpu=(83,760) cpu=(83,760)
idx=7 gpu=(76,771) cpu=(77,877)
idx=8 gpu=(77,877) cpu=(80,958)
idx=9 gpu=(80,958) cpu=(75,1047)
```

## Taxonomy Answer

1. Bounded top-K truncation is the leading cause for the current mismatches.
   Raw max scores match, mismatches are post-topK, and the mismatching windows
   show topK overflow with smaller CPU `scoreInfo` peaks missing from the GPU
   summary.

2. `scoreInfo` representation is not yet complete enough. The GPU summary can
   reproduce the top max score, but it does not preserve all CPU `preAlign`
   entries needed after position-order compaction.

3. The observed mismatches are not tie/order-only. `tie_mismatches=0` on both
   humanLncAtlas runs.

4. Raw max score values are not different in these runs. `score_mismatches=0`;
   `score_delta_max` comes from the first differing `scoreInfo` entries.

5. The mismatch happens after bounded top-K / summary compaction, not before the
   raw max-score stage.

6. Next fix target: repair or widen the GPU `scoreInfo` representation so it is
   complete enough for CPU `preAlign` semantics. If that remains ambiguous, add
   a selected-window full-column debug API to compare CPU and GPU column maxima
   before top-K compaction.

## Decision

`FASIM_GPU_DP_COLUMN=1` remains a correctness prototype only. Do not recommend
or default it until validation reaches zero scoreInfo mismatches and zero
fallbacks on the humanLncAtlas workloads.

Forbidden-scope check:

```text
default enablement: no
scoring/threshold/non-overlap/output change: no
validation relaxation: no
new filter/full CUDA rewrite: no
approximate fallback: no
```
