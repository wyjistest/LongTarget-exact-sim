# Fasim GPU DP+column ScoreInfo Alignment

Base branch:

```text
fasim-gpu-dp-column-post-topk-pack-shadow
```

This stacked PR repairs the default-off `FASIM_GPU_DP_COLUMN=1` scoreInfo representation by building GPU scoreInfo from full GPU column maxima with the same CPU-compatible position grouping used by Fasim. It keeps CPU/Fasim output semantics authoritative, does not default GPU, and does not change scoring, threshold, non-overlap, or output behavior.

Each workload/mode uses 1 run. Tables report the observed values from this validation pass.

## Modes

| Mode | Binary | Environment |
| --- | --- | --- |
| legacy | x86 | `` |
| table | x86 | `FASIM_TRANSFERSTRING_TABLE=1` |
| gpu | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1` |
| gpu_validate | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Median Summary

| Workload | Mode | Total seconds | vs legacy | vs table | Window gen | transferString | DP | Column | Output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | legacy | 0.020256 | 1.00x | 1.23x | 0.003131 | 0.003019 | 0.011111 | 0.005595 | 0.000032 |
| tiny | table | 0.024957 | 0.81x | 1.00x | 0.000218 | 0.000080 | 0.014621 | 0.009713 | 0.000024 |
| tiny | gpu | 0.226204 | 0.09x | 0.11x | 0.000139 | 0.000027 | 0.000000 | 0.000000 | 0.000034 |
| tiny | gpu_validate | 0.277118 | 0.07x | 0.09x | 0.000148 | 0.000030 | 0.000000 | 0.000000 | 0.000032 |
| medium_synthetic | legacy | 0.162617 | 1.00x | 0.90x | 0.023888 | 0.023054 | 0.095554 | 0.042379 | 0.000150 |
| medium_synthetic | table | 0.145760 | 1.12x | 1.00x | 0.001147 | 0.000257 | 0.099492 | 0.044344 | 0.000144 |
| medium_synthetic | gpu | 0.524579 | 0.31x | 0.28x | 0.001076 | 0.000229 | 0.000000 | 0.000000 | 0.000142 |
| medium_synthetic | gpu_validate | 0.858601 | 0.19x | 0.17x | 0.001094 | 0.000224 | 0.000000 | 0.000000 | 0.000146 |
| window_heavy_synthetic | legacy | 0.599231 | 1.00x | 0.95x | 0.084225 | 0.080928 | 0.358487 | 0.154613 | 0.000524 |
| window_heavy_synthetic | table | 0.567613 | 1.06x | 1.00x | 0.004475 | 0.000980 | 0.391521 | 0.169574 | 0.000563 |
| window_heavy_synthetic | gpu | 1.537150 | 0.39x | 0.37x | 0.004341 | 0.000958 | 0.000000 | 0.000000 | 0.000573 |
| window_heavy_synthetic | gpu_validate | 2.983830 | 0.20x | 0.19x | 0.004201 | 0.000933 | 0.000000 | 0.000000 | 0.000552 |
| human_lnc_atlas_17kb_target | legacy | 0.063707 | 1.00x | 1.00x | 0.019013 | 0.018319 | 0.025955 | 0.018149 | 0.000000 |
| human_lnc_atlas_17kb_target | table | 0.063798 | 1.00x | 1.00x | 0.001213 | 0.000256 | 0.037720 | 0.024273 | 0.000000 |
| human_lnc_atlas_17kb_target | gpu | 0.275765 | 0.23x | 0.23x | 0.000590 | 0.000113 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_17kb_target | gpu_validate | 0.548294 | 0.12x | 0.12x | 0.000588 | 0.000118 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_508kb_target | legacy | 1.178670 | 1.00x | 0.76x | 0.315803 | 0.303563 | 0.547814 | 0.310671 | 0.000168 |
| human_lnc_atlas_508kb_target | table | 0.892980 | 1.32x | 1.00x | 0.015836 | 0.003081 | 0.555038 | 0.315749 | 0.000137 |
| human_lnc_atlas_508kb_target | gpu | 2.980090 | 0.40x | 0.30x | 0.016525 | 0.003617 | 0.000000 | 0.000000 | 0.000188 |
| human_lnc_atlas_508kb_target | gpu_validate | 6.096890 | 0.19x | 0.15x | 0.016406 | 0.003658 | 0.000000 | 0.000000 | 0.000200 |

## GPU Cost Summary

| Workload | Mode | Active | Calls | Windows | Cells | H2D bytes | D2H bytes | Kernel seconds | GPU total seconds | Validate seconds | Score mismatches | Column mismatches | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | gpu | 1 | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012319 | 0.012370 | 0.000000 | 0 | 0 | 0 |
| tiny | gpu_validate | 1 | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012316 | 0.012367 | 0.048318 | 0 | 0 | 0 |
| medium_synthetic | gpu | 1 | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012325 | 0.012439 | 0.000000 | 0 | 0 | 0 |
| medium_synthetic | gpu_validate | 1 | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.011251 | 0.011388 | 0.356198 | 0 | 0 | 0 |
| window_heavy_synthetic | gpu | 1 | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.011207 | 0.011510 | 0.000000 | 0 | 0 | 0 |
| window_heavy_synthetic | gpu_validate | 1 | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.011225 | 0.011524 | 1.421230 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | gpu | 1 | 2 | 16 | 110,077,812 | 72,372 | 32,768 | 0.014079 | 0.014190 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | gpu_validate | 1 | 2 | 16 | 110,077,812 | 72,372 | 32,768 | 0.014073 | 0.014176 | 0.108750 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | gpu | 1 | 2 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.016172 | 0.017174 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | gpu_validate | 1 | 2 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.015335 | 0.016321 | 3.097440 | 0 | 0 | 0 |

## Digest Stability

| Workload | Mode | Digest | Records | Matches legacy |
| --- | --- | --- | --- | --- |
| tiny | legacy | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | table | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | gpu | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| tiny | gpu_validate | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes |
| medium_synthetic | legacy | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | table | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | gpu | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| medium_synthetic | gpu_validate | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes |
| window_heavy_synthetic | legacy | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | table | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | gpu | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| window_heavy_synthetic | gpu_validate | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes |
| human_lnc_atlas_17kb_target | legacy | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | table | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | gpu | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_17kb_target | gpu_validate | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes |
| human_lnc_atlas_508kb_target | legacy | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | table | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | gpu | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |
| human_lnc_atlas_508kb_target | gpu_validate | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes |

## Cost Breakdown Gap

The current prototype reports H2D/D2H byte counts plus GPU kernel and GPU batch wall seconds. It does not yet expose separate CUDA init seconds, H2D seconds, D2H seconds, or CPU extension seconds. Those are the next diagnostic targets if the GPU path remains a performance candidate.

## Decision

`FASIM_GPU_DP_COLUMN=1` is validation-clean across the documented tiny, synthetic, and humanLncAtlas workloads, but this exact scoreInfo repair is slower than table-only mode because it currently recomputes/transfers full column maxima for correctness. Keep GPU DP+column default-off as a correctness prototype; the next performance step is to make GPU postTopK packing exact without the full-column D2H overhead.

Forbidden-scope check:

```text
default enablement: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
digest relaxation: no
```
