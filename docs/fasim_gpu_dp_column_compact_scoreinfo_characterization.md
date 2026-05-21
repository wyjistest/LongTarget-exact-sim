# Fasim GPU DP+column Compact ScoreInfo Characterization

Base branch:

```text
fasim-gpu-dp-column-compact-scoreinfo-packing
```

This stacked PR characterizes the default-off `FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` path across repeated runs. It adds no GPU logic and does not change default Fasim output, scoring, threshold, non-overlap, SIM-close, or recovery behavior.

Each workload/mode uses 3 run(s). Tables report medians.

## Modes

| Mode | Binary | Environment |
| --- | --- | --- |
| table_only | x86 | `FASIM_TRANSFERSTRING_TABLE=1` |
| full_column_exact_validate | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |
| compact_scoreinfo | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` |
| compact_scoreinfo_validate | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Median Wall-Clock Summary

| Workload | Mode | Total seconds | vs table-only | vs full-column exact | Window gen | transferString | DP | Column | Output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | table_only | 0.031431 | 1.00x | 10.92x | 0.000259 | 0.000069 | 0.020153 | 0.010632 | 0.000052 |
| tiny | full_column_exact_validate | 0.343342 | 0.09x | 1.00x | 0.000147 | 0.000029 | 0.000000 | 0.000000 | 0.000034 |
| tiny | compact_scoreinfo | 0.247468 | 0.13x | 1.39x | 0.000148 | 0.000029 | 0.000000 | 0.000000 | 0.000028 |
| tiny | compact_scoreinfo_validate | 0.275856 | 0.11x | 1.24x | 0.000138 | 0.000028 | 0.000000 | 0.000000 | 0.000032 |
| medium_synthetic | table_only | 0.146598 | 1.00x | 6.61x | 0.001180 | 0.000275 | 0.100367 | 0.044433 | 0.000164 |
| medium_synthetic | full_column_exact_validate | 0.968942 | 0.15x | 1.00x | 0.001097 | 0.000231 | 0.000000 | 0.000000 | 0.000157 |
| medium_synthetic | compact_scoreinfo | 0.301345 | 0.49x | 3.22x | 0.001105 | 0.000232 | 0.000000 | 0.000000 | 0.000120 |
| medium_synthetic | compact_scoreinfo_validate | 0.390965 | 0.37x | 2.48x | 0.001095 | 0.000248 | 0.000000 | 0.000000 | 0.000122 |
| window_heavy_synthetic | table_only | 0.552780 | 1.00x | 5.54x | 0.004291 | 0.000919 | 0.381026 | 0.165396 | 0.000589 |
| window_heavy_synthetic | full_column_exact_validate | 3.063700 | 0.18x | 1.00x | 0.004321 | 0.000947 | 0.000000 | 0.000000 | 0.000674 |
| window_heavy_synthetic | compact_scoreinfo | 0.478170 | 1.16x | 6.41x | 0.004375 | 0.000930 | 0.000000 | 0.000000 | 0.000457 |
| window_heavy_synthetic | compact_scoreinfo_validate | 0.775817 | 0.71x | 3.95x | 0.004362 | 0.000948 | 0.000000 | 0.000000 | 0.000481 |
| human_lnc_atlas_17kb_target | table_only | 0.032448 | 1.00x | 14.34x | 0.000544 | 0.000111 | 0.019838 | 0.011798 | 0.000000 |
| human_lnc_atlas_17kb_target | full_column_exact_validate | 0.465201 | 0.07x | 1.00x | 0.000591 | 0.000119 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_17kb_target | compact_scoreinfo | 0.268283 | 0.12x | 1.73x | 0.000607 | 0.000117 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | 0.309049 | 0.10x | 1.51x | 0.000590 | 0.000122 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_508kb_target | table_only | 0.911891 | 1.00x | 6.77x | 0.016195 | 0.003183 | 0.566591 | 0.322248 | 0.000175 |
| human_lnc_atlas_508kb_target | full_column_exact_validate | 6.172330 | 0.15x | 1.00x | 0.016580 | 0.003686 | 0.000000 | 0.000000 | 0.000262 |
| human_lnc_atlas_508kb_target | compact_scoreinfo | 0.629208 | 1.45x | 9.81x | 0.016664 | 0.003691 | 0.000000 | 0.000000 | 0.000124 |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | 1.303670 | 0.70x | 4.73x | 0.016623 | 0.003720 | 0.000000 | 0.000000 | 0.000135 |

## GPU / Compact ScoreInfo Summary

| Workload | Mode | GPU active | Windows | Cells | H2D bytes | D2H bytes | Kernel seconds | GPU total seconds | Compact active | Compact records | Compact D2H bytes | Compact overflow/fallback windows | Full-column extend windows | Full-column extend D2H bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | table_only | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 |
| tiny | full_column_exact_validate | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.011188 | 0.011246 | 0 | 0 | 0 | 0 | 4 | 69,856 |
| tiny | compact_scoreinfo | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.011188 | 0.011243 | 1 | 78 | 8,192 | 0 | 0 | 0 |
| tiny | compact_scoreinfo_validate | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012294 | 0.012349 | 1 | 78 | 8,192 | 0 | 0 | 0 |
| medium_synthetic | table_only | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 |
| medium_synthetic | full_column_exact_validate | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.011193 | 0.011310 | 0 | 0 | 0 | 0 | 32 | 558,848 |
| medium_synthetic | compact_scoreinfo | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.011186 | 0.011296 | 1 | 624 | 65,536 | 0 | 0 | 0 |
| medium_synthetic | compact_scoreinfo_validate | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012308 | 0.012417 | 1 | 624 | 65,536 | 0 | 0 | 0 |
| window_heavy_synthetic | table_only | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | full_column_exact_validate | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.011339 | 0.011734 | 0 | 0 | 0 | 0 | 128 | 2,235,392 |
| window_heavy_synthetic | compact_scoreinfo | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.011175 | 0.011480 | 1 | 2,496 | 262,144 | 0 | 0 | 0 |
| window_heavy_synthetic | compact_scoreinfo_validate | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.012288 | 0.012587 | 1 | 2,496 | 262,144 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | table_only | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | full_column_exact_validate | 1 | 16 | 110,077,812 | 72,372 | 32,768 | 0.013995 | 0.014103 | 0 | 0 | 0 | 0 | 16 | 289,488 |
| human_lnc_atlas_17kb_target | compact_scoreinfo | 1 | 16 | 110,077,812 | 72,372 | 32,768 | 0.013986 | 0.014089 | 1 | 256 | 32,768 | 1 | 1 | 20,000 |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | 1 | 16 | 110,077,812 | 72,372 | 32,768 | 0.014003 | 0.014110 | 1 | 256 | 32,768 | 1 | 1 | 20,000 |
| human_lnc_atlas_508kb_target | table_only | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | full_column_exact_validate | 1 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.015243 | 0.016310 | 0 | 0 | 0 | 0 | 416 | 8,300,288 |
| human_lnc_atlas_508kb_target | compact_scoreinfo | 1 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.015256 | 0.016297 | 1 | 7,599 | 851,968 | 12 | 12 | 240,000 |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | 1 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.016791 | 0.017821 | 1 | 7,599 | 851,968 | 12 | 12 | 240,000 |

## Validation Summary

| Workload | Mode | Score mismatches | Column mismatches | ScoreInfo mismatches | Compact mismatches | Correctness fallbacks | Clean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | full_column_exact_validate | 0 | 0 | 0 | 0 | 0 | yes |
| tiny | compact_scoreinfo_validate | 0 | 0 | 0 | 0 | 0 | yes |
| medium_synthetic | full_column_exact_validate | 0 | 0 | 0 | 0 | 0 | yes |
| medium_synthetic | compact_scoreinfo_validate | 0 | 0 | 0 | 0 | 0 | yes |
| window_heavy_synthetic | full_column_exact_validate | 0 | 0 | 0 | 0 | 0 | yes |
| window_heavy_synthetic | compact_scoreinfo_validate | 0 | 0 | 0 | 0 | 0 | yes |
| human_lnc_atlas_17kb_target | full_column_exact_validate | 0 | 0 | 0 | 0 | 0 | yes |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | 0 | 0 | 0 | 0 | 0 | yes |
| human_lnc_atlas_508kb_target | full_column_exact_validate | 0 | 0 | 0 | 0 | 0 | yes |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | 0 | 0 | 0 | 0 | 0 | yes |

## Digest Stability

| Workload | Mode | Digest | Records | Matches table-only |
| --- | --- | --- | --- | --- |
| tiny | table_only | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | full_column_exact_validate | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | compact_scoreinfo | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | compact_scoreinfo_validate | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| medium_synthetic | table_only | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | full_column_exact_validate | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | compact_scoreinfo | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | compact_scoreinfo_validate | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| window_heavy_synthetic | table_only | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | full_column_exact_validate | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | compact_scoreinfo | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | compact_scoreinfo_validate | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| human_lnc_atlas_17kb_target | table_only | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | full_column_exact_validate | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | compact_scoreinfo | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_508kb_target | table_only | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | full_column_exact_validate | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | compact_scoreinfo | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |

## Decision

Compact scoreInfo is validation-clean and improves over full-column exact on tiny, medium_synthetic, window_heavy_synthetic, human_lnc_atlas_17kb_target, human_lnc_atlas_508kb_target. It beats table-only only on window_heavy_synthetic, human_lnc_atlas_508kb_target, while table-only still wins on medium_synthetic, human_lnc_atlas_17kb_target. Keep it default-off and treat it as a workload-sensitive performance candidate, not a recommended opt-in yet.

Forbidden-scope check:

```text
default GPU enablement: no
compact recommendation/default: no
scoring/threshold/non-overlap/output change: no
SIM-close/recovery change: no
validation relaxation: no
```
