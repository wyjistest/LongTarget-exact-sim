# CUDA sample initial-scan composition

Date: 2026-05-09

Base: `cuda-initial-critical-path-telemetry`

This is a docs-only audit of what the sample path's 8-9 second
`benchmark.sim_initial_scan_seconds` consists of. It does not add an
optimization, does not change initial scan dispatch, and does not change
candidate replay, safe-store behavior, region dispatch, planner authority,
validation, fallback, or CUDA kernels.

## Question

PR #12 showed that the sample path is dominated by initial scan rather than
region D2H. PR #13 surfaced/gated existing initial critical-path fields. This
pass uses those fields to answer:

```text
sample 的 8-9 秒 initial scan 到底由什么构成？
```

## Method

The sample region-locate exactness path was run five times with the default
stack mode:

```text
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
```

Each run used a unique `.tmp/sample_initial_scan_composition/<timestamp>/...`
output directory and passed the sample exactness diff. No direct-region-reduce,
deferred-count, validation, packed-summary, chunked handoff, or initial-reducer
opt-in was enabled.

## Per-run composition

| run | initial | GPU | D2H | CPU merge | context apply | safe-store update | safe-store prune | safe-store upload | summary materialize | residual after GPU+D2H+CPU | residual after summary materialize |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 14.228100 | 0.892352 | 1.667180 | 4.803520 | 1.616870 | 2.245330 | 0.767066 | 0.174044 | 0.521116 | 6.865048 | 6.343932 |
| 2 | 8.430470 | 0.902135 | 1.658290 | 4.654320 | 1.617640 | 2.138590 | 0.741032 | 0.156853 | 0.525299 | 1.215725 | 0.690426 |
| 3 | 8.505170 | 0.872433 | 1.670060 | 4.892780 | 1.622400 | 2.214920 | 0.780023 | 0.275216 | 0.529397 | 1.069897 | 0.540500 |
| 4 | 8.540930 | 0.929669 | 1.676870 | 4.848270 | 1.638750 | 2.257780 | 0.813918 | 0.137609 | 0.532074 | 1.086121 | 0.554047 |
| 5 | 8.259990 | 0.906622 | 1.677560 | 4.577710 | 1.599530 | 2.165990 | 0.774563 | 0.037428 | 0.533590 | 1.098098 | 0.564508 |

Run 1 is an outlier in total initial wall time. The subphase fields are close
to the other runs, but `sim_initial_scan_seconds` contains about `6.3s` of
unattributed wall time after the visible major phases and summary
materialization. The stable interpretation below therefore focuses on runs 2-5
and uses the median table only as a coarse summary.

## Median composition

| field | median | min | max | max-min | pct of median initial |
| --- | ---: | ---: | ---: | ---: | ---: |
| `sim_initial_scan_seconds` | 8.505170 | 8.259990 | 14.228100 | 5.968110 | 100.0 |
| `sim_initial_scan_cpu_merge_seconds` | 4.803520 | 4.577710 | 4.892780 | 0.315070 | 56.5 |
| `sim_initial_scan_d2h_seconds` | 1.670060 | 1.658290 | 1.677560 | 0.019270 | 19.6 |
| `sim_initial_scan_gpu_seconds` | 0.902135 | 0.872433 | 0.929669 | 0.057236 | 10.6 |
| `sim_initial_summary_result_materialize_seconds` | 0.529397 | 0.521116 | 0.533590 | 0.012474 | 6.2 |
| `sim_initial_scan_wait_seconds` | 0.010881 | 0.010875 | 0.010910 | 0.000035 | 0.1 |
| `sim_initial_scan_sync_wait_seconds` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0 |
| `sim_initial_scan_count_copy_seconds` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0 |
| `sim_initial_scan_base_upload_seconds` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0 |
| `sim_initial_scan_tail_seconds` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0 |

The median visible major subtotal is:

```text
GPU + D2H + CPU merge = 7.363052s
initial - (GPU + D2H + CPU merge) = 1.098098s
initial - (GPU + D2H + CPU merge + summary materialize) = 0.564508s
```

So the stable 8-9s sample initial scan is approximately:

```text
CPU merge / replay / safe-store maintenance   ~4.8s
initial D2H                                   ~1.67s
initial CUDA scan kernels                     ~0.90s
summary result materialization                ~0.53s
remaining host wrapper / unaccounted wall     ~0.55-0.69s on stable runs
```

## CPU merge breakdown

| field | median | pct of median initial | note |
| --- | ---: | ---: | --- |
| `sim_initial_scan_cpu_context_apply_seconds` | 1.617640 | 19.0 | Applies row-run summaries into exact candidate/frontier context. |
| `sim_initial_scan_cpu_safe_store_update_seconds` | 2.214920 | 26.0 | Merges initial summaries into the host safe candidate-state store. |
| `sim_initial_scan_cpu_safe_store_prune_seconds` | 0.774563 | 9.1 | Prunes the host safe-store after update. |
| `sim_initial_scan_cpu_safe_store_upload_seconds` | 0.156853 | 1.8 | Uploads the safe-store mirror for safe-workset locate. |
| `update + prune` | 2.994943 | 35.2 | CPU-side safe-store rebuild subtotal. |

The CPU merge subtotal closes tightly to `sim_initial_scan_cpu_merge_seconds`:

```text
median context + update + prune + upload = 4.763976s
median cpu_merge - median subtotal       = 0.039544s
per-run cpu_merge - subtotal             ~= 0.0002s
```

The median subtraction gap is mostly a median-of-components artifact; per-run
CPU merge accounting closes to within about `0.0002s`.

## What the 8-9 seconds are not

On this sample/default path:

```text
sim_initial_scan_count_copy_seconds = 0
sim_initial_scan_base_upload_seconds = 0
sim_initial_scan_sync_wait_seconds = 0
sim_initial_scan_tail_seconds = 0
sim_initial_run_summary_pipeline_seconds = 0
```

The current default path is not spending visible time in count-copy, base-upload,
explicit initial sync-wait, tail, hash/segmented reduce, or top-K reducer
telemetry. The main story is CPU replay/safe-store maintenance first, then D2H,
then CUDA scan kernels, then result materialization and residual host overhead.

## Interpretation

The next optimization target should not be another transfer-only change. Initial
D2H is visible at about `1.67s`, but CPU merge is much larger at about `4.8s`.
Within CPU merge, safe-store update/prune account for about `3.0s`, and context
apply accounts for about `1.6s`.

The remaining `~0.55-0.69s` stable residual after summary materialization is
real from the current telemetry perspective: `sim_initial_scan_seconds` wraps
all of `enumerateInitialSimCandidates()`, while the exposed subfields only cover
CUDA-reported GPU/D2H, CPU merge, and selected materialization/copy counters.
This residual likely includes host-side wrapper work around the CUDA call,
result bookkeeping, vector ownership/copy effects, and other un-attributed
overhead. It should be treated as a telemetry gap before being treated as an
optimization target.

## Recommendation

For sample initial scan, prioritize characterization or redesign around:

```text
1. CPU safe-store update/prune (~3.0s median)
2. CPU context apply (~1.6s median)
3. initial D2H (~1.67s median), only if a design also avoids CPU replay bottlenecks
4. residual host wrapper/materialization telemetry (~0.55-0.69s on stable runs)
```

Safe-store upload alone is not a strong standalone target at this point:
`sim_initial_scan_cpu_safe_store_upload_seconds` is about `0.16s` median and is
noisy. Optimizing it without reducing update/prune/context apply is unlikely to
move the sample wall-clock enough to survive the variance seen in PR #12.
