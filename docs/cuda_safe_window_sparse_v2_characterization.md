# CUDA safe-window sparse-v2 characterization

This note characterizes the existing opt-in safe-window `sparse_v2` planner on
top of `cuda-safe-window-characterization`. It does not change safe-window
defaults, planner authority, fallback behavior, validation, dispatch, or CUDA
kernels.

## Context

- Branch: `cuda-safe-window-sparse-v2-characterization`
- Base stack: `cuda-safe-window-characterization`
- Default planner: `dense`
- Diagnostic planner under test: `LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2`

The previous safe-window pass showed material coarsening inflation but high
fine-shadow mismatch counts. This pass asks whether the existing `sparse_v2`
planner reduces coarsened execution cells without worse compare-builder plans or
fallback risk.

## Inventory

| Area | Existing knobs / keys | Action |
| --- | --- | --- |
| planner mode | `LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=dense|sparse_v1|sparse_v2`, `benchmark.sim_safe_window_planner_mode` | documented and collected |
| sparse-v2 selection | `benchmark.sim_safe_window_sparse_v2_considered`, `selected`, `rejected`, `saved_cells` | documented and collected |
| geometry | raw cells, exec cells, inflated cells, max raw/exec cells | documented and collected |
| compare-builder | `benchmark.sim_safe_window_plan_{equal,better,worse}_to_builder` | documented and collected |
| fallbacks | selector/overflow/empty-plan and exact fallback counters | documented and collected |
| safe-workset and region | safe-workset timing plus region GPU/D2H counters | documented and collected |

The existing telemetry was sufficient. No code or script changes were needed.

## Commands

Baseline:

```bash
make check-benchmark-telemetry
make check-sample-cuda-sim-region-locate
```

Dense planner geometry:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 make check-benchmark-telemetry
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 make check-sample-cuda-sim-region-locate
```

Sparse-v2 geometry:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2 \
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 \
make check-benchmark-telemetry

LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2 \
LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY=1 \
make check-sample-cuda-sim-region-locate
```

Sparse-v2 compare-builder:

```bash
LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2 \
LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1 \
make check-benchmark-telemetry

LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=sparse_v2 \
LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1 \
make check-sample-cuda-sim-region-locate
```

Compare-builder timing is not a direct performance A/B because compare-builder
forces the builder path and reports `sim_safe_window_applied=0`.

## Geometry

| Field | Dense benchmark | Sparse-v2 benchmark | Dense sample | Sparse-v2 sample |
| --- | ---: | ---: | ---: | ---: |
| `sim_safe_window_exec_cells` | 12283040 | 12283040 | 503991297 | 503991297 |
| `sim_safe_window_raw_cells` | 11068507 | 11068507 | 405737653 | 405737653 |
| `sim_safe_window_coarsening_inflated_cells` | 1214533 | 1214533 | 98253644 | 98253644 |
| inflation ratio | 10.97% | 10.97% | 24.22% | 24.22% |
| `sim_safe_window_sparse_v2_considered` | 0 | 140 | 0 | 515 |
| `sim_safe_window_sparse_v2_selected` | 0 | 0 | 0 | 0 |
| `sim_safe_window_sparse_v2_rejected` | 0 | 140 | 0 | 515 |
| `sim_safe_window_sparse_v2_saved_cells` | 0 | 0 | 0 | 0 |
| `sim_safe_window_plan_cells` | 12283040 | 12283040 | 503991297 | 503991297 |
| `sim_safe_window_exact_fallbacks` | 0 | 0 | 0 | 0 |
| `sim_safe_window_fallbacks` | 0 | 0 | 0 | 0 |

`sparse_v2` considered every safe-window plan in these runs, but selected none.
It produced no saved cells and did not reduce raw, exec, plan, or inflated cell
counts.

## Timing Sample

| Field | Dense benchmark | Sparse-v2 benchmark | Dense sample | Sparse-v2 sample |
| --- | ---: | ---: | ---: | ---: |
| `sim_safe_window_gpu_seconds` | 0.00355693 | 0.262589 | 0.0320232 | 2.16256 |
| `sim_safe_window_d2h_seconds` | 0.004639 | 0.00793782 | 0.0171702 | 0.0332705 |
| `sim_safe_workset_total_seconds` | 0.534956 | 0.706905 | 4.38046 | 6.67498 |
| `sim_safe_workset_build_seconds` | 0.0365884 | 0.307601 | 0.327616 | 2.5116 |
| `sim_safe_workset_merge_seconds` | 0.0835741 | 0.0870253 | 1.47711 | 1.45727 |
| `sim_region_scan_gpu_seconds` | 0.24992 | 0.299082 | 2.51199 | 2.63905 |
| `sim_region_d2h_seconds` | 0.0662383 | 0.0620825 | 0.623603 | 0.579359 |
| `sim_region_summary_bytes_d2h` | 1764360 | 1764360 | 6670080 | 6670080 |
| `sim_seconds` | 2.05043 | 2.26127 | 12.8847 | 15.5493 |
| `total_seconds` | 4.39723 | 4.30479 | 14.9736 | 17.8712 |

Single-run wall-clock timings are noisy, but the planner-side cost signal is
not subtle: `sparse_v2` adds GPU planning time without reducing execution cells
on these samples.

## Compare-Builder

| Field | Sparse-v2 benchmark | Sparse-v2 sample |
| --- | ---: | ---: |
| expected attempts | 140 | 515 |
| `sim_safe_window_applied` | 0 | 0 |
| `sim_safe_window_gpu_builder_fallbacks` | 140 | 515 |
| `sim_safe_window_gpu_builder_passes` | 140 | 515 |
| `sim_safe_window_plan_equal_to_builder` | 135 | 508 |
| `sim_safe_window_plan_better_than_builder` | 0 | 0 |
| `sim_safe_window_plan_worse_than_builder` | 0 | 0 |
| missing comparison coverage | 5 | 7 |
| comparison coverage | 96.43% | 98.64% |
| `sim_safe_window_exact_fallbacks` | 0 | 0 |
| `sim_safe_window_fallbacks` | 0 | 0 |
| selector / overflow / empty fallbacks | 0 / 0 / 0 | 0 / 0 / 0 |

Compare-builder found no worse sparse-v2 plans in the covered comparisons.
However, because `sparse_v2` selected no sparse geometry and saved no cells, the
absence of worse plans is not enough to justify a sparse-v2 shadow gate PR.

## Decision

| Question | Answer |
| --- | --- |
| Did sparse-v2 reduce exec cells? | No. `exec_cells` is identical to dense. |
| Did sparse-v2 reduce coarsening inflation? | No. `inflated_cells` and inflation ratio are identical to dense. |
| Did sparse-v2 select sparse plans? | No. `selected=0`, `rejected=140/515`. |
| Did sparse-v2 introduce worse compare-builder plans? | No worse plans in covered comparisons. |
| Did sparse-v2 increase fallback/overflow? | No selector, overflow, empty-plan, or exact fallbacks. |
| Did sparse-v2 improve timings? | No reliable positive signal; planner GPU/build time increased. |
| Is sparse-v2 worth a shadow gate PR next? | No, not from these samples. |

## Recommendation

Do not mine a sparse-v2 shadow gate next. The existing `sparse_v2` path is
diagnostically safe in the sense that it did not show worse compare-builder
plans or fallback growth, but it also did not select sparse geometry or save any
cells on the benchmark/sample paths.

Recommended next mining target: safe-workset host merge reduction.

Reasoning:

- Region scheduler shape mergeability was zero, so region batching remains
  deferred.
- Fine geometry is blocked by high fine-shadow mismatch counts.
- Sparse-v2 selected no plans and saved no cells.
- Safe-workset merge remains consistently material on the sample path
  (`~1.3-1.5s`), and region D2H remains visible but smaller than host merge in
  these runs.

Direct region reduce/deferred counts remains a secondary candidate because
region D2H is still visible, but the stronger immediate signal is host-side
safe-workset merge cost.

## Out of scope

This pass intentionally does not:

- default `sparse_v2`
- add sparse planner behavior
- change `LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW` semantics
- change planner authority or fallback behavior
- change validation, grouping, dispatch, safe-store, or safe-workset semantics
- enable fine geometry real path
- enable region true-batch real dispatch
- add locate shared-input grouping or upload caching
- add direct region reduce or deferred counts real paths
