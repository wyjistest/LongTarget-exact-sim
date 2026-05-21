# Fasim GPU DP+column Characterization

Base branch:

```text
fasim-gpu-dp-column-prototype
```

This stacked PR characterizes the default-off `FASIM_GPU_DP_COLUMN=1` prototype with repeated median A/B runs. It does not add optimization code, change output authority, or change scoring/threshold/non-overlap behavior.

Each workload/mode uses 5 runs. Tables report medians.

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
| tiny | legacy | 0.036845 | 1.00x | 0.44x | 0.005954 | 0.005789 | 0.019043 | 0.010818 | 0.000036 |
| tiny | table | 0.016293 | 2.26x | 1.00x | 0.000129 | 0.000030 | 0.010985 | 0.005055 | 0.000022 |
| tiny | gpu | 0.185906 | 0.20x | 0.09x | 0.000147 | 0.000030 | 0.000000 | 0.000000 | 0.000030 |
| tiny | gpu_validate | 0.160415 | 0.23x | 0.10x | 0.000146 | 0.000029 | 0.000000 | 0.000000 | 0.000029 |
| medium_synthetic | legacy | 0.164076 | 1.00x | 0.90x | 0.024433 | 0.023591 | 0.095272 | 0.043752 | 0.000161 |
| medium_synthetic | table | 0.147344 | 1.11x | 1.00x | 0.001136 | 0.000261 | 0.101064 | 0.044677 | 0.000147 |
| medium_synthetic | gpu | 0.223217 | 0.74x | 0.66x | 0.001101 | 0.000231 | 0.000000 | 0.000000 | 0.000116 |
| medium_synthetic | gpu_validate | 0.295138 | 0.56x | 0.50x | 0.001096 | 0.000224 | 0.000000 | 0.000000 | 0.000117 |
| window_heavy_synthetic | legacy | 0.595844 | 1.00x | 0.88x | 0.083219 | 0.080104 | 0.357388 | 0.153237 | 0.000567 |
| window_heavy_synthetic | table | 0.522739 | 1.14x | 1.00x | 0.004049 | 0.000862 | 0.360792 | 0.156008 | 0.000522 |
| window_heavy_synthetic | gpu | 0.400104 | 1.49x | 1.31x | 0.004287 | 0.000915 | 0.000000 | 0.000000 | 0.000440 |
| window_heavy_synthetic | gpu_validate | 0.681610 | 0.87x | 0.77x | 0.004315 | 0.000936 | 0.000000 | 0.000000 | 0.000450 |
| human_lnc_atlas_17kb_target | legacy | 0.067470 | 1.00x | 0.47x | 0.019687 | 0.018949 | 0.028420 | 0.018816 | 0.000000 |
| human_lnc_atlas_17kb_target | table | 0.031931 | 2.11x | 1.00x | 0.000541 | 0.000124 | 0.019668 | 0.011460 | 0.000000 |
| human_lnc_atlas_17kb_target | gpu | 0.149162 | 0.45x | 0.21x | 0.000590 | 0.000120 | 0.000000 | 0.000000 | 0.000000 |
| human_lnc_atlas_17kb_target | gpu_validate | 0.215517 | 0.31x | 0.15x | 0.000580 | 0.000119 | 0.015059 | 0.008791 | 0.000000 |
| human_lnc_atlas_508kb_target | legacy | 1.172320 | 1.00x | 0.75x | 0.313344 | 0.301072 | 0.545661 | 0.306876 | 0.000180 |
| human_lnc_atlas_508kb_target | table | 0.879613 | 1.33x | 1.00x | 0.015406 | 0.003083 | 0.547758 | 0.309592 | 0.000164 |
| human_lnc_atlas_508kb_target | gpu | 0.479571 | 2.44x | 1.83x | 0.016358 | 0.003680 | 0.000000 | 0.000000 | 0.000106 |
| human_lnc_atlas_508kb_target | gpu_validate | 1.614220 | 0.73x | 0.54x | 0.016455 | 0.003653 | 0.541159 | 0.302401 | 0.000159 |

## GPU Cost Summary

| Workload | Mode | Active | Calls | Windows | Cells | H2D bytes | D2H bytes | Kernel seconds | GPU total seconds | Validate seconds | Score mismatches | Column mismatches | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | gpu | 1 | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012274 | 0.012329 | 0.000000 | 0 | 0 | 0 |
| tiny | gpu_validate | 1 | 1 | 4 | 49,108,768 | 17,464 | 8,192 | 0.012276 | 0.012328 | 0.009189 | 0 | 0 | 0 |
| medium_synthetic | gpu | 1 | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012256 | 0.012368 | 0.000000 | 0 | 0 | 0 |
| medium_synthetic | gpu_validate | 1 | 1 | 32 | 392,870,144 | 139,712 | 65,536 | 0.012266 | 0.012381 | 0.069230 | 0 | 0 | 0 |
| window_heavy_synthetic | gpu | 1 | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.012247 | 0.012545 | 0.000000 | 0 | 0 | 0 |
| window_heavy_synthetic | gpu_validate | 1 | 1 | 128 | 1,571,480,576 | 558,848 | 262,144 | 0.012234 | 0.012542 | 0.275156 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | gpu | 1 | 2 | 16 | 110,077,812 | 72,372 | 32,768 | 0.015351 | 0.015452 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_17kb_target | gpu_validate | 1 | 2 | 16 | 110,077,812 | 72,372 | 32,768 | 0.015358 | 0.015466 | 0.020927 | 0 | 1 | 12 |
| human_lnc_atlas_508kb_target | gpu | 1 | 2 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.016370 | 0.017386 | 0.000000 | 0 | 0 | 0 |
| human_lnc_atlas_508kb_target | gpu_validate | 1 | 2 | 416 | 3,156,184,512 | 2,075,072 | 851,968 | 0.015984 | 0.017021 | 0.573520 | 0 | 12 | 412 |

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

## Validation Finding

`FASIM_GPU_DP_COLUMN_VALIDATE=1` is clean on the tiny and synthetic workloads,
but not on the local humanLncAtlas workloads:

```text
human_lnc_atlas_17kb_target:
  column_mismatches = 1
  fallbacks = 12

human_lnc_atlas_508kb_target:
  column_mismatches = 12
  fallbacks = 412
```

A debug run on the 17kb workload showed equal max score but a shorter
GPU-derived column list:

```text
gpu_count = 44
cpu_count = 51
minScore = 72
gpuMaxScore = 90
cpuMaxScore = 90
```

This is consistent with the current bounded top-K representation still
truncating lower-score peaks that CPU `preAlign` keeps after position-order
compaction. The CUDA backend currently caps `topK` at 256, so this is a
correctness-representation limitation of the prototype rather than a simple
environment issue.

## Decision

Correctness is not clean under validation. Stop performance work and debug GPU-vs-CPU DP/column mismatches before any opt-in recommendation.

Forbidden-scope check:

```text
default enablement: no
scoring/threshold/non-overlap/output change: no
new filter/full CUDA rewrite: no
digest relaxation: no
```
