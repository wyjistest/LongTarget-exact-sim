# CUDA Safe-Workset Best-Path Decomposition

Base branch:

```text
cuda-exact-frontier-per-request-shadow-resident-source
```

Base commit:

```text
a40ad95
```

This is a characterization note only. It does not add optimization code, does
not change runtime defaults, and does not change region dispatch, safe-store
authority, candidate/frontier replay, clean-gate behavior, `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## Modes

Legacy/default sample region/locate:

```bash
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
./scripts/run_sample_exactness_cuda.sh
```

Recommended safe-store GPU best path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
./scripts/run_sample_exactness_cuda.sh
```

Each mode used 3 runs. Tables report median values unless a range column is
shown. Run logs were written under:

```text
.tmp/cuda_safe_workset_best_path_decomp_legacy_r1..r3/
.tmp/cuda_safe_workset_best_path_decomp_best_path_r1..r3/
```

## Top-Level Medians

| Field | Legacy | Best path | Delta | Legacy range | Best range |
| --- | ---: | ---: | ---: | ---: | ---: |
| total_seconds | 16.702 | 13.1421 | -3.5599 | 7.1053 | 0.0657 |
| sim_seconds | 14.6799 | 11.0839 | -3.5960 | 7.0180 | 0.0891 |
| calc_score_seconds | 1.75111 | 1.74973 | -0.00138 | 0.03503 | 0.00463 |
| sim_initial_scan_seconds | 9.61849 | 6.80118 | -2.81731 | 6.74599 | 0.33500 |
| sim_initial_store_rebuild_seconds | 3.40202 | 0.888039 | -2.513981 | 0.40128 | 0.334155 |
| sim_safe_workset_total_seconds | 4.42741 | 4.05662 | -0.37079 | 0.48786 | 0.32415 |
| sim_materialize_seconds | 0.323488 | 0.296462 | -0.027026 | 0.040268 | 0.010654 |
| sim_traceback_post_seconds | 0.0124719 | 0.0119711 | -0.0005008 | 0.0002211 | 0.0003551 |

The best path keeps the multi-second win from the safe-store GPU stack. Initial
scan remains the largest aggregate at `6.80118s`; safe-workset is the next
largest aggregate at `4.05662s`.

The legacy run set had one large `initial_scan` outlier
(`16.2973s`), so sub-second legacy deltas should not be over-interpreted. The
best-path runs were much tighter for total and sim time.

## Initial Scan Check

| Field | Legacy | Best path | Delta |
| --- | ---: | ---: | ---: |
| sim_initial_scan_seconds | 9.61849 | 6.80118 | -2.81731 |
| sim_initial_store_rebuild_seconds | 3.40202 | 0.888039 | -2.513981 |
| sim_initial_scan_cpu_safe_store_update_seconds | 2.67981 | 0.888039 | -1.791771 |
| sim_initial_scan_cpu_safe_store_prune_seconds | 0.768235 | 0 | -0.768235 |
| sim_initial_scan_cpu_context_apply_seconds | 1.99786 | 1.96175 | -0.03611 |
| sim_initial_scan_d2h_seconds | 1.70239 | 1.71221 | +0.00982 |
| sim_initial_summary_result_materialize_seconds | 0.54352 | 0.538525 | -0.004995 |
| sim_initial_safe_store_gpu_precombine_prune_seconds | 0 | 0.493172 | +0.493172 |

Initial safe-store rebuild is no longer the dominant initial-scan slice. The
largest remaining initial-scan slices are still context apply/candidate replay
at about `1.96s` and initial D2H at about `1.71s`.

Best-path guard counters stayed clean:

| Field | Median |
| --- | ---: |
| sim_initial_safe_store_gpu_precombine_active | 1 |
| sim_initial_safe_store_gpu_precombine_resident_source_active | 1 |
| sim_initial_safe_store_gpu_precombine_summary_h2d_elided | 1 |
| sim_initial_safe_store_gpu_precombine_summary_h2d_bytes_saved | 1,432,865,216 |
| sim_initial_safe_store_gpu_precombine_prune_active | 1 |
| sim_initial_safe_store_gpu_precombine_prune_input_states | 8,831,091 |
| sim_initial_safe_store_gpu_precombine_prune_kept_states | 3,311,201 |
| sim_initial_safe_store_gpu_precombine_prune_d2h_bytes | 119,203,236 |
| sim_initial_safe_store_gpu_precombine_prune_d2h_bytes_saved | 198,716,040 |
| sim_initial_safe_store_gpu_precombine_prune_fallbacks | 0 |
| sim_initial_safe_store_gpu_precombine_prune_size_mismatches | 0 |
| sim_initial_safe_store_gpu_precombine_prune_candidate_mismatches | 0 |
| sim_initial_safe_store_gpu_precombine_prune_order_mismatches | 0 |
| sim_initial_safe_store_gpu_precombine_prune_digest_mismatches | 0 |

## Safe-Workset And Region

| Field | Legacy | Best path | Delta |
| --- | ---: | ---: | ---: |
| sim_safe_workset_total_seconds | 4.42741 | 4.05662 | -0.37079 |
| sim_safe_workset_build_seconds | 0.342352 | 0.325533 | -0.016819 |
| sim_safe_workset_merge_seconds | 1.56987 | 1.14172 | -0.42815 |
| sim_region_scan_gpu_seconds | 2.44803 | 2.48249 | +0.03446 |
| sim_region_d2h_seconds | 0.649038 | 0.653339 | +0.004301 |
| sim_region_summary_bytes_d2h | 6,670,080 | 6,670,080 | 0 |
| sim_materialize_seconds | 0.323488 | 0.296462 | -0.027026 |
| calc_score_seconds | 1.75111 | 1.74973 | -0.00138 |

In the best-path mode, safe-workset is dominated by region scan and host merge:

```text
sim_region_scan_gpu_seconds      ~= 2.48s
sim_safe_workset_merge_seconds   ~= 1.14s
sim_region_d2h_seconds           ~= 0.65s
sim_safe_workset_build_seconds   ~= 0.33s
```

The region D2H payload is only `6,670,080` bytes, so a D2H-only packing change
is unlikely to be the first safe-workset target unless it also reduces the
per-request synchronization cost.

## Safe-Workset Shape

| Field | Legacy | Best path |
| --- | ---: | ---: |
| sim_safe_workset_passes | 515 | 515 |
| sim_safe_workset_input_cells | 347,833,785 | 347,833,785 |
| sim_safe_workset_exec_cells | 435,538,804 | 435,538,804 |
| sim_safe_workset_cuda_tasks | 0 | 0 |
| sim_safe_workset_cuda_launches | 0 | 0 |
| sim_safe_workset_returned_states | 185,280 | 185,280 |
| sim_safe_workset_fallback_invalid_store | 0 | 0 |
| sim_safe_workset_fallback_no_affected_start | 0 | 0 |
| sim_safe_workset_fallback_no_workset | 0 | 0 |
| sim_safe_workset_fallback_invalid_bands | 0 | 0 |
| sim_safe_workset_fallback_scan_failure | 0 | 0 |
| sim_safe_workset_fallback_shadow_mismatch | 0 | 0 |

The safe-workset shape is identical between modes. There are no safe-workset
fallbacks in these runs.

## Region Dispatch Shape

| Field | Legacy | Best path |
| --- | ---: | ---: |
| sim_region_backend | cuda | cuda |
| sim_region_calls | 515 | 515 |
| sim_region_requests | 515 | 515 |
| sim_region_launches | 515 | 515 |
| sim_region_batch_calls | 0 | 0 |
| sim_region_batch_requests | 0 | 0 |
| sim_region_serial_fallback_requests | 0 | 0 |
| sim_region_packed_requests | 515 | 515 |
| sim_region_total_cells | 503,991,297 | 503,991,297 |
| sim_region_events_total | 88,433,400 | 88,433,400 |
| sim_region_candidate_summaries_total | 9,026,574 | 9,026,574 |
| sim_region_event_bytes_d2h | 0 | 0 |
| sim_region_summary_bytes_d2h | 6,670,080 | 6,670,080 |

Region still runs as one request per launch: `515 calls`, `515 requests`, and
`515 launches`, with no batch calls. This points more toward launch/batching or
region GPU-shape work than toward summary-byte packing.

## Safe-Window Planner

| Field | Legacy | Best path |
| --- | ---: | ---: |
| sim_safe_window_planner_mode | dense | dense |
| sim_safe_window_exec_geometry | coarsened | coarsened |
| sim_safe_window_attempts | 515 | 515 |
| sim_safe_window_selected_worksets | 515 | 515 |
| sim_safe_window_applied | 515 | 515 |
| sim_safe_window_fallbacks | 0 | 0 |
| sim_safe_window_exact_fallbacks | 0 | 0 |
| sim_safe_window_gpu_builder_fallbacks | 0 | 0 |
| sim_safe_window_count | 8,097 | 8,097 |
| sim_safe_window_affected_starts | 187,473 | 187,473 |
| sim_safe_window_coord_bytes_d2h | 13,089,344 | 13,089,344 |
| sim_safe_window_gpu_seconds | 0.0321808 | 0.0315031 |
| sim_safe_window_d2h_seconds | 0.0171462 | 0.0166363 |
| sim_safe_window_exec_bands | 515 | 515 |
| sim_safe_window_exec_cells | 503,991,297 | 503,991,297 |
| sim_safe_window_plan_bands | 515 | 515 |
| sim_safe_window_plan_cells | 503,991,297 | 503,991,297 |
| sim_safe_window_plan_fallbacks | 0 | 0 |
| sim_safe_window_plan_better_than_builder | 0 | 0 |
| sim_safe_window_plan_worse_than_builder | 0 | 0 |
| sim_safe_window_plan_equal_to_builder | 0 | 0 |

The planner is not showing fallback pressure. It always selects/applies the
dense coarsened safe-window plan, and planner GPU/D2H overhead is small. The
main signal is the resulting region geometry and per-request dispatch count,
not a planner failure mode.

## Merge Breakdown

| Field | Legacy | Best path | Delta |
| --- | ---: | ---: | ---: |
| sim_safe_workset_merge_seconds | 1.56987 | 1.14172 | -0.42815 |
| sim_safe_workset_merge_safe_store_upsert_seconds | 0.87932 | 0.637309 | -0.242011 |
| sim_safe_workset_merge_safe_store_erase_seconds | 0.863452 | 0.622652 | -0.240800 |
| sim_safe_workset_merge_safe_store_prune_seconds | 0.624669 | 0.449628 | -0.175041 |
| sim_safe_workset_merge_safe_store_upload_seconds | 0.0528063 | 0.0447744 | -0.0080319 |
| sim_safe_workset_merge_candidate_apply_seconds | 0.00950202 | 0.00905228 | -0.00044974 |
| sim_safe_workset_merge_candidate_erase_seconds | 0.00353271 | 0.00336682 | -0.00016589 |
| sim_safe_workset_merge_unique_start_keys | 185,280 | 185,280 | 0 |
| sim_safe_workset_merge_duplicate_states | 0 | 0 | 0 |
| sim_safe_workset_merge_safe_store_size_after_prune | 3,094,987 | 3,094,987 | 0 |
| sim_safe_workset_merge_prune_scanned_states | 6,261,179 | 6,261,179 | 0 |
| sim_safe_workset_merge_prune_removed_states | 3,166,192 | 3,166,192 | 0 |

Host merge is the second largest safe-workset slice. Within the reported merge
fields, safe-store erase/upsert and prune dominate; candidate apply/erase and
upload are comparatively small.

## Answers

1. Safe-workset is now the largest actionable aggregate after initial scan:
   best-path initial scan is `6.80118s`, and safe-workset total is `4.05662s`.

2. Safe-workset is dominated by region GPU scan and host merge. Region GPU is
   about `2.48s`, host merge is about `1.14s`, D2H is about `0.65s`, and build
   is about `0.33s`.

3. Region calls are still one request per launch. The median counters are
   `sim_region_calls=515`, `sim_region_requests=515`, and
   `sim_region_launches=515`; batch counters are zero.

4. Safe-window planner/geometry points to region geometry and dispatch, not
   fallback. The planner is dense/coarsened, all `515` attempts are selected and
   applied, and fallback counters are zero.

5. The next real target should be region launch/batching or region GPU-shape
   work, with safe-workset merge reduction as a second candidate. Region summary
   packing is lower priority because only `6.67 MB` is transferred, and
   `calc_score` remains a side-lane at about `1.75s`.

## Boundary Checks

Collected best-path runs reported:

```text
sim_initial_exact_frontier_shadow_gate_active=0
sim_initial_exact_frontier_per_request_shadow_active=0
sim_initial_exact_frontier_replay_enabled=0
```

The clean gate remained inactive, per-request shadow was off for this
characterization, and exact frontier replay stayed disabled.
