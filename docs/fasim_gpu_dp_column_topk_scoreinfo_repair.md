# Fasim GPU DP+column Top-K / ScoreInfo Repair

Base branch:

```text
fasim-gpu-dp-column-mismatch-taxonomy
```

This stacked PR debugs the default-off `FASIM_GPU_DP_COLUMN=1` validation blocker by sweeping bounded top-K capacity and recording first scoreInfo field differences. It does not change final output authority, scoring, threshold, non-overlap, or output semantics.

Each workload/cap uses 1 run(s). Tables report medians.

## Debug Environment

```text
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN=1
FASIM_GPU_DP_COLUMN_VALIDATE=1
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1
FASIM_GPU_DP_COLUMN_TOPK_CAP=<cap>   # omitted for current/default
```

`fasim_gpu_dp_column_scoreinfo_field_mismatch_mask` uses:

```text
1 = score field differs
2 = position field differs
4 = scoreInfo count differs
8 = one side is missing at the first differing index
```

## Cap Sweep

| Workload | Cap | Reported cap | Total seconds | GPU total | Kernel | H2D bytes | D2H bytes | Score mismatch | ScoreInfo mismatch | Pre top-K | Post top-K | Truncated | Overflow | Fallbacks | First window | First column | CPU score | GPU score | CPU pos | GPU pos | Field mask |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | current | 256 | 0.221367 | 0.015511 | 0.015384 | 72,372 | 32,768 | 0 | 1 | 0 | 1 | 1 | 1 | 12 | 3 | 7 | 77 | 76 | 877 | 771 | 7 (score+position+count) |
| human_lnc_atlas_17kb_target | 8 | 8 | 0.215987 | 0.011368 | 0.011271 | 72,372 | 1,024 | 0 | 16 | 0 | 16 | 16 | 16 | 16 | 0 | 0 | 85 | 99 | 169 | 2750 | 7 (score+position+count) |
| human_lnc_atlas_17kb_target | 16 | 16 | 0.189307 | 0.011402 | 0.011315 | 72,372 | 2,048 | 0 | 16 | 0 | 16 | 16 | 16 | 16 | 0 | 0 | 85 | 96 | 169 | 2735 | 7 (score+position+count) |
| human_lnc_atlas_17kb_target | 32 | 32 | 0.221902 | 0.011531 | 0.011420 | 72,372 | 4,096 | 0 | 16 | 0 | 16 | 15 | 16 | 16 | 0 | 0 | 85 | 91 | 169 | 717 | 3 (score+position) |
| human_lnc_atlas_17kb_target | 64 | 64 | 0.217466 | 0.011797 | 0.011703 | 72,372 | 8,192 | 0 | 13 | 0 | 13 | 12 | 13 | 16 | 1 | 2 | 85 | 105 | 123 | 3371 | 7 (score+position+count) |
| human_lnc_atlas_17kb_target | 128 | 128 | 0.234044 | 0.012682 | 0.012574 | 72,372 | 16,384 | 0 | 5 | 0 | 5 | 5 | 5 | 16 | 3 | 2 | 74 | 90 | 694 | 713 | 7 (score+position+count) |
| human_lnc_atlas_17kb_target | 256 | 256 | 0.211782 | 0.015465 | 0.015355 | 72,372 | 32,768 | 0 | 1 | 0 | 1 | 1 | 1 | 12 | 3 | 7 | 77 | 76 | 877 | 771 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | current | 256 | 1.792630 | 0.017657 | 0.016571 | 2,075,072 | 851,968 | 0 | 12 | 0 | 12 | 11 | 12 | 412 | 5 | 12 | 69 | 75 | 1338 | 1412 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 8 | 8 | 1.588440 | 0.013094 | 0.012508 | 2,075,072 | 26,624 | 0 | 416 | 0 | 416 | 411 | 416 | 416 | 0 | 0 | 79 | 97 | 406 | 1555 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 16 | 16 | 1.618390 | 0.013109 | 0.012546 | 2,075,072 | 53,248 | 0 | 413 | 0 | 413 | 403 | 415 | 416 | 0 | 0 | 79 | 97 | 406 | 1555 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 32 | 32 | 1.554330 | 0.013264 | 0.012653 | 2,075,072 | 106,496 | 0 | 403 | 0 | 403 | 384 | 406 | 416 | 0 | 0 | 79 | 87 | 406 | 427 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 64 | 64 | 1.609130 | 0.013762 | 0.012979 | 2,075,072 | 212,992 | 0 | 316 | 0 | 316 | 285 | 336 | 416 | 0 | 0 | 79 | 84 | 406 | 421 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 128 | 128 | 1.628480 | 0.014635 | 0.013856 | 2,075,072 | 425,984 | 0 | 135 | 0 | 135 | 116 | 141 | 416 | 0 | 8 | 78 | 84 | 1458 | 1538 | 7 (score+position+count) |
| human_lnc_atlas_508kb_target | 256 | 256 | 1.606900 | 0.017844 | 0.016751 | 2,075,072 | 851,968 | 0 | 12 | 0 | 12 | 11 | 12 | 412 | 5 | 12 | 69 | 75 | 1338 | 1412 | 7 (score+position+count) |

## Digest Stability

| Workload | Cap | Digest | Records | Matches first cap |
| --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | current | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 8 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 16 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 32 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 64 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 128 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | 256 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_508kb_target | current | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 8 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 16 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 32 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 64 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 128 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | 256 | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |

## Answers

| Workload | Zero-mismatch caps | Smallest clean cap | Current/default result | Largest tested cap result |
| --- | --- | --- | --- | --- |
| human_lnc_atlas_17kb_target | none | n/a | scoreInfo=1, fallbacks=12 | 256 (256): scoreInfo=1, fallbacks=12 |
| human_lnc_atlas_508kb_target | none | n/a | scoreInfo=12, fallbacks=412 | 256 (256): scoreInfo=12, fallbacks=412 |

## Decision

No tested cap validates cleanly, while mismatches remain post-top-K with no pre-top-K score mismatch. The next PR should add selected-window full scoreInfo/full-column debug or widen the representation beyond the current bounded cap; do not continue performance work yet.

Forbidden-scope check:

```text
default GPU enablement: no
validation relaxation: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
speedup claim: no
```

