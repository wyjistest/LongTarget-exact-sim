# Safe-Store GPU Best-Path Remaining Bottlenecks

Baseline checkpoint:

```text
safe-store-gpu-best-path-merged-2026-05-12
```

Recommended opt-in:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

This is a characterization note only. It does not add optimization code, does
not change runtime defaults, and does not change candidate/frontier replay,
clean-gate behavior, `gpu_real`, `ordered_segmented_v3`, or
`EXACT_FRONTIER_REPLAY`.

## Runs

All runs used the CUDA sample region/locate exactness command with oracle diff.

Modes:

- legacy/default
- recommended safe-store GPU best path

Each mode used 3 runs. Tables below report median, min, max, and range.

## Top-Level Phases

| Field | Legacy median | Best-path median | Delta |
| --- | ---: | ---: | ---: |
| total_seconds | 16.3911 | 13.2479 | -3.1432 |
| sim_seconds | 14.1158 | 11.2112 | -2.9046 |
| calc_score_seconds | 1.76812 | 1.76015 | -0.00797 |
| sim_initial_scan_seconds | 9.42443 | 6.98478 | -2.43965 |
| sim_safe_workset_total_seconds | 4.3521 | 3.91427 | -0.43783 |
| sim_materialize_seconds | 0.31121 | 0.30024 | -0.01097 |
| sim_traceback_post_seconds | 0.0126038 | 0.0122687 | -0.000335 |

The largest remaining aggregate phase is still initial scan at about `6.98s`.
Safe-workset is second at about `3.91s`, and `calc_score` is stable around
`1.76s`.

## Initial Scan Breakdown

| Field | Legacy median | Best-path median | Delta |
| --- | ---: | ---: | ---: |
| sim_initial_scan_seconds | 9.42443 | 6.98478 | -2.43965 |
| sim_initial_store_rebuild_seconds | 3.13219 | 0.923525 | -2.208665 |
| sim_initial_scan_cpu_safe_store_update_seconds | 2.45747 | 0.923525 | -1.533945 |
| sim_initial_scan_cpu_safe_store_prune_seconds | 0.626935 | 0 | -0.626935 |
| sim_initial_scan_cpu_context_apply_seconds | 1.89048 | 1.88609 | -0.00439 |
| sim_initial_context_apply_candidate_seconds | 1.89037 | 1.88595 | -0.00442 |
| sim_initial_scan_d2h_seconds | 1.7982 | 1.85258 | +0.05438 |
| sim_initial_summary_result_materialize_seconds | 0.562827 | 0.600925 | +0.038098 |
| sim_initial_scan_gpu_seconds | 0.896892 | 0.889296 | -0.007596 |
| sim_initial_safe_store_gpu_precombine_prune_seconds | 0 | 0.523723 | +0.523723 |

Initial safe-store rebuild is no longer the dominant bottleneck. It falls from
about `3.13s` to about `0.92s`; CPU prune is removed from the best-path opt-in,
and the remaining safe-store update is the host materialization/index handoff
from GPU-pruned kept states.

The largest remaining initial-scan slices are now:

```text
context apply / candidate replay:  ~1.89s
initial D2H:                       ~1.85s
safe-store rebuild:                ~0.92s
CUDA initial scan kernels:         ~0.89s
summary result materialization:    ~0.60s
GPU precombine/prune:              ~0.52s
```

## Safe-Workset And Region

| Field | Legacy median | Best-path median | Delta |
| --- | ---: | ---: | ---: |
| sim_safe_workset_total_seconds | 4.3521 | 3.91427 | -0.43783 |
| sim_safe_workset_build_seconds | 0.31944 | 0.308618 | -0.010822 |
| sim_safe_workset_merge_seconds | 1.37322 | 1.16747 | -0.20575 |
| sim_region_scan_gpu_seconds | 2.53533 | 2.36995 | -0.16538 |
| sim_region_d2h_seconds | 0.6928 | 0.664055 | -0.028745 |
| sim_region_summary_bytes_d2h | 6670080 | 6670080 | 0 |

Safe-workset is not larger than initial scan, but it is the next largest
aggregate. Region GPU time is the largest reported region slice. Region D2H is
stable in bytes and remains below one second on this sample.

## Variance

| Field | Legacy range | Best-path range |
| --- | ---: | ---: |
| total_seconds | 5.2906 | 0.166 |
| sim_seconds | 5.3751 | 0.1323 |
| sim_initial_scan_seconds | 5.27382 | 0.45288 |
| sim_initial_store_rebuild_seconds | 0.07903 | 0.258514 |
| sim_initial_scan_d2h_seconds | 0.34342 | 0.27598 |
| sim_safe_workset_total_seconds | 0.01185 | 0.17271 |
| sim_region_scan_gpu_seconds | 0.03066 | 0.18295 |
| calc_score_seconds | 0.03172 | 0.01956 |

The best-path total and sim medians are stable enough to support multi-second
conclusions. Sub-second local optimizations still need repeated medians because
initial D2H, safe-store rebuild, safe-workset total, and region GPU each show
enough variance to obscure small gains.

## Answers

1. Largest remaining phase:
   Initial scan remains largest at about `6.98s`. Safe-workset is second at
   about `3.91s`.

2. Did initial safe-store rebuild stop being dominant:
   Yes. It drops from about `3.13s` to about `0.92s`; context apply/candidate
   replay and initial D2H are now larger initial-scan slices.

3. Is candidate replay/context apply the next main target:
   It is the largest remaining initial-scan CPU slice at about `1.89s`. It is a
   plausible next initial-line target, but safe-workset/region should be
   considered in parallel because they are larger aggregate work outside the
   initial scan.

4. Is safe-workset or region now larger than initial:
   No. Safe-workset total is about `3.91s`, below initial scan at about `6.98s`.
   Region GPU is about `2.37s`; it is significant but not larger than initial.

5. Is calc_score worth a side-lane:
   Maybe, but not the primary next target. It is stable around `1.76s`, which is
   now visible after the safe-store reduction, but it is smaller than initial
   scan and safe-workset.

6. Is variance still larger than expected optimization deltas:
   For sub-second changes, yes. The best-path total range is small (`0.166s`),
   but individual slices such as initial D2H, rebuild, safe-workset, and region
   GPU vary enough that future small optimizations should use repeated medians.

## Correctness And Boundary

Best-path counters in the collected runs:

```text
sim_initial_safe_store_gpu_precombine_prune_size_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_order_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_digest_mismatches=0
sim_initial_safe_store_gpu_precombine_prune_fallbacks=0
```

Clean gate status in the collected runs:

```text
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_shadow_gate_supported=0
```

No forbidden route is introduced by this characterization:

```text
gpu_real: no diff match
ordered_segmented_v3: no diff match
EXACT_FRONTIER_REPLAY: no diff match
```
