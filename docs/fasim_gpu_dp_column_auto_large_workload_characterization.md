# Fasim GPU DP+column AUTO Large Workload Characterization

Base branch:

```text
fasim-gpu-dp-column-auto-policy
```

This stacked PR characterizes the default-off `FASIM_GPU_DP_COLUMN_AUTO=1` policy on larger synthetic and optional real-corpus workloads. It adds no GPU logic and does not change default Fasim output, scoring, thresholds, non-overlap behavior, SIM-close, recovery, or validation behavior.

Each workload/mode uses 3 run(s). Tables report medians.

## Modes

| Mode | Binary | Environment |
| --- | --- | --- |
| table_only | cuda | `FASIM_TRANSFERSTRING_TABLE=1` |
| auto | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1` |
| auto_validate | cuda | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_VALIDATE=1` |

## Workloads

| Workload | Kind | Description |
| --- | --- | --- |
| tiny | synthetic | current testDNA/H19 smoke fixture |
| window_heavy_synthetic | synthetic | 32-entry deterministic testDNA/H19 scale-up |
| synthetic_entries_64 | synthetic | 64-entry deterministic testDNA/H19 scale-up |
| synthetic_entries_128 | synthetic | 128-entry deterministic testDNA/H19 scale-up |

## AUTO Summary

| Workload | AUTO windows | AUTO DP cells | Table seconds | AUTO seconds | AUTO speedup | AUTO+validate seconds | Requested | Active | Selected path | Disabled reason | Validation clean | Digest matches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 4 | 49,108,768 | 0.036189 | 0.043521 | n/a | 0.033953 | 1 | 0 | table | below_threshold | yes | yes |
| window_heavy_synthetic | 128 | 1,571,480,576 | 0.531742 | 0.489474 | 1.09x | 0.772124 | 1 | 1 | compact_gpu | none | yes | yes |
| synthetic_entries_64 | 256 | 3,142,961,152 | 1.050750 | 0.727924 | 1.44x | 1.278500 | 1 | 1 | compact_gpu | none | yes | yes |
| synthetic_entries_128 | 512 | 6,285,922,304 | 2.045580 | 1.198260 | 1.71x | 2.303120 | 1 | 1 | compact_gpu | none | yes | yes |

## Stage And GPU Cost

| Workload | Mode | Total seconds | Window gen | DP seconds | Column seconds | GPU active | GPU windows | GPU cells | Kernel seconds | GPU total seconds | H2D bytes | D2H bytes | Compact fallback windows | Full-column fallback windows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | auto | 0.043521 | 0.000330 | 0.028305 | 0.014165 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 |
| tiny | auto_validate | 0.033953 | 0.000285 | 0.021131 | 0.011978 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | auto | 0.489474 | 0.004301 | 0.000000 | 0.000000 | 1 | 128 | 1,571,480,576 | 0.012279 | 0.012578 | 558,848 | 262,144 | 0 | 0 |
| window_heavy_synthetic | auto_validate | 0.772124 | 0.004204 | 0.000000 | 0.000000 | 1 | 128 | 1,571,480,576 | 0.012281 | 0.012597 | 558,848 | 262,144 | 0 | 0 |
| synthetic_entries_64 | auto | 0.727924 | 0.008629 | 0.000000 | 0.000000 | 1 | 256 | 3,142,961,152 | 0.012356 | 0.012927 | 1,117,696 | 524,288 | 0 | 0 |
| synthetic_entries_64 | auto_validate | 1.278500 | 0.008643 | 0.000000 | 0.000000 | 1 | 256 | 3,142,961,152 | 0.012336 | 0.012907 | 1,117,696 | 524,288 | 0 | 0 |
| synthetic_entries_128 | auto | 1.198260 | 0.017036 | 0.000000 | 0.000000 | 1 | 512 | 6,285,922,304 | 0.012662 | 0.013754 | 2,235,392 | 1,048,576 | 0 | 0 |
| synthetic_entries_128 | auto_validate | 2.303120 | 0.017037 | 0.000000 | 0.000000 | 1 | 512 | 6,285,922,304 | 0.012670 | 0.013784 | 2,235,392 | 1,048,576 | 0 | 0 |

## Validation And Digest

| Workload | Mode | Digest | Records | Matches table-only | Score mismatches | Column mismatches | ScoreInfo mismatches | Compact mismatches | Correctness fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | table_only | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| tiny | auto | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| tiny | auto_validate | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | table_only | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | auto | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| window_heavy_synthetic | auto_validate | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | table_only | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | auto | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_64 | auto_validate | `sha256:0bebe256cdb89fd0235264e3c9889484721532fd78c281e19c8b5023000edc5e` | 384 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | table_only | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | auto | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |
| synthetic_entries_128 | auto_validate | `sha256:efb0934a7233a450eed5423eca5499fa44c096c2caecfec32d41cc87ecf12822` | 768 | yes | 0 | 0 | 0 | 0 | 0 |

## Decision

`FASIM_GPU_DP_COLUMN_AUTO=1` correctly keeps below-threshold workloads on the table path and selects compact GPU for threshold-matching workloads. It beats table-only medians on: window_heavy_synthetic, synthetic_entries_64, synthetic_entries_128. Keep AUTO as a large-workload opt-in candidate; do not default GPU from this PR. No optional real-corpus workload was available in this run, so the result does not support a whole-genome or real-corpus order-of-magnitude claim.

Forbidden-scope check:

```text
new GPU/kernel logic: no
default GPU DP+column: no
scoring/threshold/non-overlap/output change: no
SIM-close/recovery change: no
validation relaxation: no
```
