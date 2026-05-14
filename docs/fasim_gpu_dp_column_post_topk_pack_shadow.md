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
| human_lnc_atlas_17kb_target | 3 | 0 | 1 | 51 | 51 | 44 | 0 | 44 | 9 | 2 | 44 | 15 | 1 | 44 | 44 |
| human_lnc_atlas_508kb_target | 5 | 0 | 12 | 52 | 52 | 46 | 0 | 40 | 9 | 3 | 40 | 15 | 1 | 40 | 34 |

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
| human_lnc_atlas_17kb_target | yes | no | 9 | yes | repair current GPU postTopK pack/rank representation |
| human_lnc_atlas_508kb_target | yes | no | 9 | yes | repair current GPU postTopK pack/rank representation |

## Decision

CPU-compatible packing over GPU pre-topK records matches CPU authoritative scoreInfo, while the current GPU post-topK pack still mismatches. The next PR should align GPU postTopK packing/ranking with the CPU-compatible path.

Forbidden-scope check:

```text
default GPU enablement: no
validation relaxation: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
speedup claim: no
```
