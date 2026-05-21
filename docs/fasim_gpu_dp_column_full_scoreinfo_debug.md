# Fasim GPU DP+column Full ScoreInfo Debug

Base branch:

```text
fasim-gpu-dp-column-topk-scoreinfo-repair
```

This stacked PR adds selected-window full scoreInfo diagnostics for the default-off `FASIM_GPU_DP_COLUMN=1` validation blocker. It does not change scoring, threshold, non-overlap, output semantics, validation rules, or GPU default behavior.

Each selected workload/window uses 1 run(s). Tables report medians.

## Debug Environment

```text
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1
FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG=1
FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX=<selected mismatching window>
FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS=<bounded print sample>
```

| Workload | Requested window | Debug window | Raw score mismatches | ScoreInfo mismatches | Pre top-K | Post top-K | Fallbacks | Full column mismatches | Column delta max | CPU records | GPU pre-topK records | GPU post-topK records | CPU rec missing pre | CPU rec missing post | First rank | Score delta | Position delta | Count delta | Set mismatches | Field mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | 3 | 3 | 0 | 1 | 0 | 1 | 12 | 0 | 0 | 51 | 51 | 44 | 0 | 0 | 7 | -1 | -106 | -7 | 0 | 3 |
| human_lnc_atlas_508kb_target | 5 | 5 | 0 | 12 | 0 | 12 | 412 | 0 | 0 | 52 | 52 | 46 | 0 | 1 | 12 | 6 | 74 | -6 | 0 | 3 |

Telemetry notes:

- `Full column mismatches` compares CPU full column max scores against GPU full column max scores before top-K.
- `Set mismatches` is the exact score/position symmetric difference between CPU scoreInfo and GPU pre-topK scoreInfo.
- `Count delta` is `GPU post-topK scoreInfo count - CPU scoreInfo count`; `scoreInfo` itself stores only score and position.
- `CPU rec missing pre/post` checks whether the first mismatching CPU score/position record exists in GPU pre-topK or post-topK records.

| Workload | Digest | Records |
| --- | --- | --- |
| human_lnc_atlas_17kb_target | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| human_lnc_atlas_508kb_target | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 |

## Answers

| Workload | Full column identical | CPU record present pre-topK | Lost/changed post-topK | Field delta observed | Next fix |
| --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | yes | yes | no | yes | repair scoreInfo field mapping |
| human_lnc_atlas_508kb_target | yes | yes | yes | yes | repair top-K ranking/packing or include required records |

## Decision

The first mismatching CPU scoreInfo record is present before top-K but absent after bounded top-K/packing. The next PR should repair top-K ranking/representation or compact all required records.

Forbidden-scope check:

```text
default GPU enablement: no
validation relaxation: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
speedup claim: no
```
