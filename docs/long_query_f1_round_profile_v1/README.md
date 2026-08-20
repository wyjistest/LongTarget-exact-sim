# Long-query F1 per-round profile v1

## Decision

```text
per-round telemetry mechanism       PASS
complete output exactness           PASS
host round scheduling bottleneck    NO
dual-contract kernel authorization  NO
next kernel focus                   main scoreInfo DP
```

This default-off profiling epoch records one owner row per global F1 batch.
The owner stores exact forward/reverse call wall, CUDA kernel, H2D, and D2H
times for each consumer round, plus host descriptor, apply, compaction, and
retirement times.  Non-owner task rows keep empty timing vectors.  Existing
per-task attempt counts and aggregate timing fields are unchanged.

Enable it with:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_ROUND_PROFILE=1
```

Source and binary binding:

```text
source commit  03903c94e0fab7ff74913aca46e2646b9b13f060
binary SHA-256 f672bcadbe52018354fd4f96d6c66b4f5037940c3983030b1ee28199c045f7aa
rebuild equal  yes
```

## Representative profile

The input was the 8000 nt boundary query against the frozen 2 Mb chr22 target.
The exact uint8 min-score path was enabled.  All 10,368 F1 rows passed, three
batch-owner rows were found at task indexes 0, 4096, and 8192, and the complete
`TFOsorted` SHA-256 remained:

```text
238ce9019d325d40d24c7f153b7943df2e8ace12b4ea5a1ae7074fe61bf24492
```

The sum of owner round GPU times was `8.064679006 s`; the old distributed
aggregate was `8.064679102 s`, an absolute difference of `9.53e-8 s`.

| Round | Active groups | Forward | Reverse | GPU seconds | GPU share |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 217,424 | 217,424 | 185,191 | 6.057046 | 75.11% |
| 1 | 52,128 | 52,128 | 4,046 | 0.856501 | 10.62% |
| 2 | 52,128 | 52,128 | 3,114 | 0.616611 | 7.65% |
| 3 | 52,128 | 52,128 | 2,976 | 0.482038 | 5.98% |
| deferred | 0 | 0 | 22,097 | 0.052484 | 0.65% |

Round-0 retirement leaves 23.98% of groups active.  The profiled host work for
descriptor creation, score application, reverse compaction, reverse
application, and retirement totals `0.113398 s`, only 1.41% of F1 GPU time.
Moving the same consumer state machine to the GPU without reducing DP or state
traffic therefore has no useful performance case.

## Nsight Systems attribution

Nsight Systems 2024.2.3 independently attributed total GPU kernel time:

| Stage | GPU share | Kernel time |
| --- | ---: | ---: |
| F1 forward byte | 41.02% | 6.909338 s |
| main byte-profile scoreInfo | 40.36% | 6.799495 s |
| uint8 min-score fast pass | 10.78% | 1.815380 s |
| F1 reverse byte | 6.91% | 1.164687 s |
| min-score word16 replay | 0.91% | 0.153471 s |
| all remaining kernels | 0.03% | 0.004229 s |

CUDA API launch time was `0.006112 s` and memcpy API time was `0.037504 s`.
The large `cudaEventSynchronize` time is waiting for these kernels, not host
orchestration work.

## Dual-contract bound

After the uint8 min-score improvement:

```text
main scoreInfo GPU                   6.799495 s
uint8 + word16 replay min-score GPU  1.968858 s
combined                             8.768352 s
```

Even making min-score completely free can reduce this combined time by only
22.45%.  The preregistered dual-contract gate requires at least 20%, so a
dual-state kernel may add at most `0.215187 s` over the current main scoreInfo
kernel.  It would need to execute the independent legacy recurrence at roughly
9.15 times lower incremental cost while causing no slowdown to main scoreInfo.

That is too little engineering margin to authorize a dual-state kernel from
this profile.  Nsight Compute is also unavailable on this host, so occupancy,
register, and stall metrics have not been measured.  Dual-contract remains a
no-go before kernel unless an independent full-concat/resource profile changes
this bound.

## Next focus

The largest independent target is main scoreInfo DP, followed closely by F1
forward.  Main scoreInfo redesign should be considered only after collecting
resource metrics on a host with Nsight Compute.  F1 kernel work remains
conditional on a design that reduces recurrence cells or global state traffic;
removing barriers alone cannot pass a meaningful gate.

Machine-readable values are in `profile.json`; the committed Nsight table is
`kernel_summary.csv`.
