# Fasim GPU DP+column Post-TopK Pack Shadow

Base branch:

```text
fasim-gpu-dp-column-full-scoreinfo-debug
```

This stacked PR adds a default-off post-topK scoreInfo packing shadow for `FASIM_GPU_DP_COLUMN=1`. It compares CPU authoritative scoreInfo, a CPU-compatible pack built from GPU pre-topK/full-column records, and the current GPU post-topK pack. It does not change final output authority or relax validation.

Each selected workload/window uses 1 run(s). Tables report medians.

## Debug Environment

```text
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1
FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG=1
FASIM_GPU_DP_COLUMN_POST_TOPK_PACK_SHADOW=1
FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX=<selected mismatching window>
```

| Workload | Window | Raw score mismatches | ScoreInfo mismatches | CPU records | GPU pre records | GPU post records | CPU-pack mismatches | GPU-pack mismatches | Missing | Extra | Rank mismatches | Field mask | Count mismatches | Position mismatches | Score mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | 3 | 0 | 0 | 51 | 51 | 51 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | 5 | 0 | 0 | 52 | 52 | 52 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Field mask:

```text
1 = score field/rank differs
2 = position field/rank differs
4 = output record count differs
8 = exact score/position record missing or extra
```

| Workload | Digest | Records |
| --- | --- | --- |
| human_lnc_atlas_17kb_target | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| human_lnc_atlas_508kb_target | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 |

## Answers

| Workload | CPU-compatible pack matches CPU | Current GPU pack matches CPU | Missing records | Count mismatch | Next fix |
| --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | yes | yes | 0 | no | postTopK pack/rank representation is validation-clean |
| human_lnc_atlas_508kb_target | yes | yes | 0 | no | postTopK pack/rank representation is validation-clean |

## Decision

CPU-compatible packing over GPU pre-topK records and the current GPU post-topK pack both match CPU authoritative scoreInfo on the selected humanLncAtlas windows. Keep GPU DP+column default-off and use broader validation/characterization before any performance recommendation.

Forbidden-scope check:

```text
default GPU enablement: no
validation relaxation: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
speedup claim: no
```
