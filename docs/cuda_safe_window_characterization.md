# CUDA safe-window characterization

This note characterizes the existing safe-window planner diagnostics on top of
`cuda-region-shape-characterization`. It does not change safe-window defaults,
planner authority, dispatch, grouping, validation, fallback behavior, or CUDA
kernels.

## Context

- Branch: `cuda-safe-window-characterization`
- Base stack: `cuda-region-shape-characterization`
- Baseline behavior: safe-window is already enabled by default when locate has a
  mirrored GPU safe-store; `LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW=0` is the
  disable knob.
- Diagnostic knobs used independently:
  - `LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1`
  - `LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1`
  - `LONGTARGET_SIM_CUDA_SAFE_WINDOW_FINE_SHADOW=1`

## Inventory

| Area | Existing knobs / keys | Action |
| --- | --- | --- |
| safe-window enablement | `LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW`, `benchmark.sim_safe_window_applied`, `benchmark.sim_safe_window_selected_worksets` | documented and collected |
| planner backend | `LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER`, `benchmark.sim_safe_window_planner_mode` | documented and collected |
| compare-builder | `LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER`, `benchmark.sim_safe_window_plan_{better,worse,equal}_to_builder` | documented and collected |
| geometry telemetry | `LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY`, raw/exec/coarsening/sparse-v2 counters | documented and collected |
| fine shadow | `LONGTARGET_SIM_CUDA_SAFE_WINDOW_FINE_SHADOW`, `benchmark.sim_safe_window_fine_shadow_*` | documented and collected |
| fallbacks | selector/overflow/empty plan and exact fallback split counters | documented and collected |
| safe-workset geometry | input/exec bands and cells, returned states, CUDA task/launch counters | documented and collected |
| safe-workset timing | build/merge/total seconds and locate umbrella time | documented and collected |

The existing telemetry was sufficient for this pass; no code or script changes
were needed.

## Commands

Baseline:

```bash
make check-benchmark-telemetry
make check-sample-cuda-sim-region-locate
```

Compare-builder:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1 make check-benchmark-telemetry
LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1 make check-sample-cuda-sim-region-locate
```

Geometry telemetry:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 make check-benchmark-telemetry
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 make check-sample-cuda-sim-region-locate
```

Fine shadow:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_FINE_SHADOW=1 make check-benchmark-telemetry
LONGTARGET_SIM_CUDA_SAFE_WINDOW_FINE_SHADOW=1 make check-sample-cuda-sim-region-locate
```

The diagnostic modes were run separately. They were not combined.

## Benchmark path

| Field / mode | baseline | compare-builder | geometry | fine-shadow |
| --- | ---: | ---: | ---: | ---: |
| `sim_safe_window_applied` | 140 | 0 | 140 | 140 |
| `sim_safe_window_selected_worksets` | 140 | 0 | 140 | 140 |
| `sim_safe_window_gpu_builder_fallbacks` | 0 | 140 | 0 | 0 |
| `sim_safe_window_exact_fallbacks` | 0 | 0 | 0 | 0 |
| `sim_safe_window_fallbacks` | 0 | 0 | 0 | 0 |
| `sim_safe_window_plan_equal_to_builder` | 0 | 135 | 0 | 0 |
| `sim_safe_window_plan_better_than_builder` | 0 | 0 | 0 | 0 |
| `sim_safe_window_plan_worse_than_builder` | 0 | 0 | 0 | 0 |
| `sim_safe_window_exec_cells` | 12283040 | 0 | 12283040 | 12283040 |
| `sim_safe_window_raw_cells` | 0 | 0 | 11068507 | 0 |
| `sim_safe_window_coarsening_inflated_cells` | 0 | 0 | 1214533 | 0 |
| coarsening inflation / raw | n/a | n/a | 10.97% | n/a |
| `sim_safe_window_fine_shadow_calls` | 0 | 0 | 0 | 140 |
| `sim_safe_window_fine_shadow_mismatches` | 0 | 0 | 0 | 139 |
| `sim_safe_workset_total_seconds` | 0.379789 | 0.515985 | 0.374658 | 2.4078 |
| `sim_safe_workset_build_seconds` | 0.035452 | 0.0428608 | 0.0355937 | 0.0354999 |
| `sim_safe_workset_merge_seconds` | 0.0790608 | 0.0866398 | 0.0799378 | 0.0796522 |
| `sim_region_scan_gpu_seconds` | 0.251524 | 0.37417 | 0.246618 | 0.246447 |
| `sim_region_d2h_seconds` | 0.0707971 | 0.0624425 | 0.0667261 | 0.0697048 |
| `sim_seconds` | 7.79249 | 2.03115 | 1.93057 | 3.91488 |
| `total_seconds` | 9.87327 | 4.10983 | 4.01981 | 6.00206 |

## Sample path

| Field / mode | baseline | compare-builder | geometry | fine-shadow |
| --- | ---: | ---: | ---: | ---: |
| `sim_safe_window_applied` | 515 | 0 | 515 | 515 |
| `sim_safe_window_selected_worksets` | 515 | 0 | 515 | 515 |
| `sim_safe_window_gpu_builder_fallbacks` | 0 | 515 | 0 | 0 |
| `sim_safe_window_exact_fallbacks` | 0 | 0 | 0 | 0 |
| `sim_safe_window_fallbacks` | 0 | 0 | 0 | 0 |
| `sim_safe_window_plan_equal_to_builder` | 0 | 508 | 0 | 0 |
| `sim_safe_window_plan_better_than_builder` | 0 | 0 | 0 | 0 |
| `sim_safe_window_plan_worse_than_builder` | 0 | 0 | 0 | 0 |
| `sim_safe_window_exec_cells` | 503991297 | 0 | 503991297 | 503991297 |
| `sim_safe_window_raw_cells` | 0 | 0 | 405737653 | 0 |
| `sim_safe_window_coarsening_inflated_cells` | 0 | 0 | 98253644 | 0 |
| coarsening inflation / raw | n/a | n/a | 24.22% | n/a |
| `sim_safe_window_fine_shadow_calls` | 0 | 0 | 0 | 515 |
| `sim_safe_window_fine_shadow_mismatches` | 0 | 0 | 0 | 470 |
| `sim_safe_workset_total_seconds` | 4.38419 | 3.96017 | 4.36768 | 30.7183 |
| `sim_safe_workset_build_seconds` | 0.323462 | 0.264338 | 0.330695 | 0.324418 |
| `sim_safe_workset_merge_seconds` | 1.36835 | 1.26371 | 1.38278 | 1.45386 |
| `sim_region_scan_gpu_seconds` | 2.58542 | 2.36734 | 2.59315 | 2.6592 |
| `sim_region_d2h_seconds` | 0.62127 | 0.65061 | 0.616901 | 0.598713 |
| `sim_region_summary_bytes_d2h` | 6670080 | 6668244 | 6670080 | 6670080 |
| `sim_seconds` | 12.7568 | 12.8278 | 12.8247 | 38.7758 |
| `total_seconds` | 14.8235 | 14.9251 | 14.9341 | 41.007 |

## Interpretation

1. Safe-workset host merge remains material. On the sample path,
   `sim_safe_workset_merge_seconds` is about `1.26-1.45` seconds across modes,
   while `sim_region_d2h_seconds` is about `0.60-0.65` seconds. The umbrella
   `sim_safe_workset_total_seconds` stays near `4` seconds in non-fine-shadow
   modes.

2. Compare-builder does not show a worse plan on these runs. It reports
   `135/140` equal comparisons on the benchmark path and `508/515` on the sample
   path, with zero better/worse comparisons and zero exact fallbacks. The missing
   comparison rows should be treated as coverage gaps, not as proof of mismatch.

3. Coarsening inflation is substantial. Geometry telemetry reports `1,214,533`
   inflated cells on the benchmark path and `98,253,644` on the sample path,
   which is about `10.97%` and `24.22%` of raw planned cells respectively.

4. Fine-shadow is not ready to become a real path. It reports `139/140`
   mismatches on the benchmark path and `470/515` on the sample path. It is also
   expensive as a diagnostic: sample `total_seconds` increases from `14.8235` to
   `41.007`.

5. Exact fallbacks are not the current blocker. All modes report zero
   `sim_safe_window_exact_fallbacks`, zero selector/overflow/empty-plan
   fallbacks, and zero store invalidations.

## Recommendation

The next mining target should be safe-window geometry characterization with an
opt-in sparse planner mode, not fine geometry real execution.

Recommended next step:

```text
docs/cuda_safe_window_sparse_v2_characterization.md
```

Run `LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2` with geometry telemetry
and compare-builder diagnostics on the same benchmark/sample paths. The question
is whether the existing sparse-v2 planner can reduce coarsened execution cells
while preserving compare-builder coverage and exactness.

Deferred:

- Fine geometry real/default path: blocked by high fine-shadow mismatch counts.
- Region bucketed true-batch shadow: previous shape characterization found zero
  estimated launch reduction.
- Direct region reduce/deferred counts: still plausible because region D2H is
  visible, but host merge and safe-window geometry are stronger immediate
  signals.
- Locate shared-input grouping: still lacks nonzero locate batch evidence from
  these default/sample runs.

## Out of scope

This pass intentionally does not:

- change `LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW` semantics
- make compare-builder default
- make fine geometry default
- trust a new GPU planner
- add sparse planner behavior
- change dispatch, grouping, fallback, validation, or planner authority
- add region true-batch real dispatch
- add locate shared-input grouping or upload caching
- skip validation, deep compare, or input checks
- add direct region reduce or deferred counts real paths
