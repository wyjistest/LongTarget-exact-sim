# Fasim GPU DP+column Compact Activation Threshold

Base branch:

```text
fasim-gpu-dp-column-compact-scoreinfo-characterization
```

This stacked PR characterizes the activation threshold for the default-off `FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` path. It adds no GPU/kernel logic and does not change default Fasim output, scoring, threshold, non-overlap, SIM-close, recovery, or validation behavior.

Each workload/mode uses 3 run(s). Tables report medians.

## Modes

| Mode | Binary | Environment |
| --- | --- | --- |
| table_only | x86 | `FASIM_TRANSFERSTRING_TABLE=1` |
| compact_scoreinfo | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1` |
| compact_scoreinfo_validate | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN=1 FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Crossover Summary

| Workload | GPU windows | DP cells | Table seconds | Compact seconds | Compact speedup | Compact validate seconds | Compact wins | Validation clean | Digest matches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 4 | 49,108,768 | 0.034956 | 0.265010 | 0.13x | 0.280373 | no | yes | yes |
| synthetic_entries_2 | 8 | 98,217,536 | 0.032597 | 0.271370 | 0.12x | 0.278532 | no | yes | yes |
| synthetic_entries_4 | 16 | 196,435,072 | 0.064783 | 0.268347 | 0.24x | 0.313269 | no | yes | yes |
| medium_synthetic | 32 | 392,870,144 | 0.148261 | 0.310250 | 0.48x | 0.354910 | no | yes | yes |
| synthetic_entries_16 | 64 | 785,740,288 | 0.297281 | 0.363967 | 0.82x | 0.510452 | no | yes | yes |
| window_heavy_synthetic | 128 | 1,571,480,576 | 0.529775 | 0.487162 | 1.09x | 0.761726 | yes | yes | yes |
| synthetic_entries_64 | 256 | 3,142,961,152 | 1.054080 | 0.714997 | 1.47x | 1.294170 | yes | yes | yes |
| synthetic_entries_128 | 512 | 6,285,922,304 | 2.087220 | 1.208630 | 1.73x | 2.284290 | yes | yes | yes |
| human_lnc_atlas_17kb_target | 16 | 110,077,812 | 0.031846 | 0.272155 | 0.12x | 0.288247 | no | yes | yes |
| human_lnc_atlas_508kb_target | 416 | 3,156,184,512 | 0.877503 | 0.639801 | 1.37x | 1.306470 | yes | yes | yes |

## GPU Cost And Overflow

| Workload | Mode | GPU active | GPU windows | DP cells | H2D bytes | D2H bytes | Kernel seconds | GPU total seconds | Compact records | Overflow windows | Compact fallback windows | Full-column fallback windows | Full-column fallback D2H bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | compact_scoreinfo | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012318 | 0.012370 | 78 | 0 | 0 | 0 | 0 |
| tiny | compact_scoreinfo_validate | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012305 | 0.012356 | 78 | 0 | 0 | 0 | 0 |
| synthetic_entries_2 | compact_scoreinfo | 1 | 8 | 98,217,536 | 34,928 | 16,384 | 0.012316 | 0.012373 | 156 | 0 | 0 | 0 | 0 |
| synthetic_entries_2 | compact_scoreinfo_validate | 1 | 8 | 98,217,536 | 34,928 | 16,384 | 0.012306 | 0.012366 | 156 | 0 | 0 | 0 | 0 |
| synthetic_entries_4 | compact_scoreinfo | 1 | 16 | 196,435,072 | 69,856 | 32,768 | 0.012322 | 0.012397 | 312 | 0 | 0 | 0 | 0 |
| synthetic_entries_4 | compact_scoreinfo_validate | 1 | 16 | 196,435,072 | 69,856 | 32,768 | 0.012308 | 0.012383 | 312 | 0 | 0 | 0 | 0 |
| medium_synthetic | compact_scoreinfo | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012296 | 0.012421 | 624 | 0 | 0 | 0 | 0 |
| medium_synthetic | compact_scoreinfo_validate | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012305 | 0.012421 | 624 | 0 | 0 | 0 | 0 |
| synthetic_entries_16 | compact_scoreinfo | 1 | 64 | 785,740,288 | 279,424 | 131,072 | 0.012291 | 0.012469 | 1,248 | 0 | 0 | 0 | 0 |
| synthetic_entries_16 | compact_scoreinfo_validate | 1 | 64 | 785,740,288 | 279,424 | 131,072 | 0.012301 | 0.012481 | 1,248 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | compact_scoreinfo | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.012278 | 0.012588 | 2,496 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | compact_scoreinfo_validate | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.012287 | 0.012589 | 2,496 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | compact_scoreinfo | 1 | 256 | 3,142,961,152 | 1,117,696 | 524,288 | 0.012353 | 0.012920 | 4,992 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | compact_scoreinfo_validate | 1 | 256 | 3,142,961,152 | 1,117,696 | 524,288 | 0.012383 | 0.012977 | 4,992 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | compact_scoreinfo | 1 | 512 | 6,285,922,304 | 2,235,392 | 1,048,576 | 0.012677 | 0.013796 | 9,984 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | compact_scoreinfo_validate | 1 | 512 | 6,285,922,304 | 2,235,392 | 1,048,576 | 0.012664 | 0.013737 | 9,984 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | compact_scoreinfo | 1 | 16 | 110,077,812 | 72,372 | 32,768 | 0.015391 | 0.015489 | 256 | 0 | 1 | 1 | 20,000 |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | 1 | 16 | 110,077,812 | 72,372 | 32,768 | 0.015407 | 0.015509 | 256 | 0 | 1 | 1 | 20,000 |
| human_lnc_atlas_508kb_target | compact_scoreinfo | 1 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.016779 | 0.017752 | 7,599 | 0 | 12 | 12 | 240,000 |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | 1 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.016813 | 0.017850 | 7,599 | 0 | 12 | 12 | 240,000 |

## Validation And Digest

| Workload | Mode | Digest | Records | Matches table-only | Score mismatches | Column mismatches | ScoreInfo mismatches | Compact mismatches | Correctness fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | table_only | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| tiny | compact_scoreinfo | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| tiny | compact_scoreinfo_validate | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_2 | table_only | `sha256:dee41057db6ca940ba8e67b43284912b3d5fbdc37b9498d584a0ce35e2102caf` | 12 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_2 | compact_scoreinfo | `sha256:dee41057db6ca940ba8e67b43284912b3d5fbdc37b9498d584a0ce35e2102caf` | 12 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_2 | compact_scoreinfo_validate | `sha256:dee41057db6ca940ba8e67b43284912b3d5fbdc37b9498d584a0ce35e2102caf` | 12 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_4 | table_only | `sha256:ea6ad511d97fea1dcde6193b5e0337d3c5221d93351303fdfdac4c49e86a1a5f` | 24 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_4 | compact_scoreinfo | `sha256:ea6ad511d97fea1dcde6193b5e0337d3c5221d93351303fdfdac4c49e86a1a5f` | 24 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_4 | compact_scoreinfo_validate | `sha256:ea6ad511d97fea1dcde6193b5e0337d3c5221d93351303fdfdac4c49e86a1a5f` | 24 | yes | 0 | 0 | 0 | 0 | 0 |
| medium_synthetic | table_only | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes | 0 | 0 | 0 | 0 | 0 |
| medium_synthetic | compact_scoreinfo | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes | 0 | 0 | 0 | 0 | 0 |
| medium_synthetic | compact_scoreinfo_validate | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_16 | table_only | `sha256:76af10cb2410cbf476a15e077e94914308b2c25c9a0f62efc4f48fba9ec5544a` | 96 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_16 | compact_scoreinfo | `sha256:76af10cb2410cbf476a15e077e94914308b2c25c9a0f62efc4f48fba9ec5544a` | 96 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_16 | compact_scoreinfo_validate | `sha256:76af10cb2410cbf476a15e077e94914308b2c25c9a0f62efc4f48fba9ec5544a` | 96 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | table_only | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | compact_scoreinfo | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | compact_scoreinfo_validate | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | table_only | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | compact_scoreinfo | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | compact_scoreinfo_validate | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | table_only | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | compact_scoreinfo | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | compact_scoreinfo_validate | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | table_only | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | compact_scoreinfo | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | compact_scoreinfo_validate | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | table_only | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | compact_scoreinfo | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes | 0 | 0 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | compact_scoreinfo_validate | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | yes | 0 | 0 | 0 | 0 | 0 |

## Threshold Interpretation

The synthetic sweep shows a size crossover between synthetic_entries_16 (64 GPU windows, 785,740,288 DP cells) and window_heavy_synthetic (128 GPU windows, 1,571,480,576 DP cells).

Predictor read:

```text
windows: useful coarse gate
DP cells: best current threshold predictor
H2D/D2H bytes: correlated with windows in this sweep
overflow/full-column fallback: report and monitor; not used as a production selector here
```

A future default-off size-gated policy can be designed around observed GPU windows or DP cells, with DP cells preferred because it directly captures the scored workload while H2D/D2H bytes mostly scale with windows in this sweep.

## Decision

Compact GPU is validation-clean and shows a workload-size crossover: synthetic wins on window_heavy_synthetic, synthetic_entries_64, synthetic_entries_128, 508kb real corpus wins, and 17kb real corpus still favors table-only. Next PR may design a default-off size-gated `FASIM_GPU_DP_COLUMN_AUTO=1` policy; do not recommend/default GPU DP+column yet.

Future policy questions:

```text
FASIM_GPU_DP_COLUMN_AUTO=1: design-only candidate, not implemented here
FASIM_GPU_DP_COLUMN_MIN_CELLS=<n>: candidate gate
FASIM_GPU_DP_COLUMN_MIN_WINDOWS=<n>: secondary candidate gate
manual opt-in only: remains current behavior
```

Forbidden-scope check:

```text
default GPU DP+column: no
new CUDA/kernel logic: no
scoring/threshold/non-overlap/output change: no
SIM-close/recovery change: no
validation relaxation: no
```
