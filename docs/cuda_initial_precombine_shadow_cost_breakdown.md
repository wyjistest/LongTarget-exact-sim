# CUDA initial precombine shadow cost breakdown

Date: 2026-05-09

Base: `cuda-initial-precombine-shadow-characterization`

This pass adds telemetry-only cost breakdowns around the default-off initial
safe-store precombine shadow. It does not add a real precombine path, does not
change default behavior, and does not change initial dispatch, safe-store
update/prune/upload semantics, candidate replay order, region dispatch, planner
authority, validation, fallback, or output behavior.

## Question

PR #17 showed that the precombine shadow is exact on covered paths and sees a
high duplicate-start ratio, but its host-side build cost is almost equal to the
legacy authoritative safe-store update:

```text
sample shadow/update = 97.96%
matrix shadow/update = 98.48%
```

This pass asks whether that cost is dominated by the precombine grouping/build
itself or by the shadow-only comparison/digest/order checks.

## Method

New telemetry splits the existing shadow helper into low-overhead block timers:

```text
benchmark.sim_initial_safe_store_precombine_shadow_build_seconds
benchmark.sim_initial_safe_store_precombine_shadow_alloc_seconds
benchmark.sim_initial_safe_store_precombine_shadow_group_build_seconds
benchmark.sim_initial_safe_store_precombine_shadow_compare_seconds
benchmark.sim_initial_safe_store_precombine_shadow_order_compare_seconds
benchmark.sim_initial_safe_store_precombine_shadow_digest_seconds
```

`shadow_seconds` keeps its prior meaning: the host shadow build cost measured
before comparison. `compare_seconds`, `order_compare_seconds`, and
`digest_seconds` are shadow-only validation costs. The implementation does not
try to time each duplicate-summary candidate merge, because doing so requires a
timer call inside the tens-of-millions summary loop and materially perturbs the
measurement.

Commands run for the reported data:

```text
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRECOMBINE_SHADOW=1 make check-sample-cuda-sim-region-locate
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_PRECOMBINE_SHADOW=1 make check-matrix-cuda-sim-region
```

Both opt-in exactness runs passed.

## Results

| workload | legacy update | shadow build | build | group build | candidate merge | compare | digest | order compare | alloc | duplicate ratio | mismatches |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sample | 2.31483 | 2.10398 | 2.10398 | 2.10324 | not low-overhead | 2.17013 | 1.09933 | 0.0589236 | 0.00073645 | 80.28% | 0 |
| matrix | 0.0797872 | 0.0755803 | 0.0755802 | 0.0755552 | not low-overhead | 0.0730889 | 0.0381766 | 0.00173297 | 0.000024837 | 84.97% | 0 |

Shape counters:

| workload | input summaries | unique states | duplicate summaries | estimated saved upserts |
| --- | ---: | ---: | ---: | ---: |
| sample | 44,777,038 | 8,831,091 | 35,945,947 | 35,945,947 |
| matrix | 2,101,113 | 315,812 | 1,785,301 | 1,785,301 |

Exactness counters:

| workload | size | candidate | order | digest |
| --- | ---: | ---: | ---: | ---: |
| sample | 0 | 0 | 0 | 0 |
| matrix | 0 | 0 | 0 | 0 |

Derived ratios:

| workload | build / legacy update | compare / build | digest / compare | alloc / build |
| --- | ---: | ---: | ---: | ---: |
| sample | 90.89% | 103.14% | 50.66% | 0.04% |
| matrix | 94.73% | 96.70% | 52.23% | 0.03% |

## Interpretation

The cost is dominated by group/build, not by allocation. On both covered paths,
`group_build_seconds` is effectively the same as `build_seconds`; allocation is
below `0.05%` of build time. This rules out simple reserve/buffer reuse as the
main missing win for the current host structure.

The build itself is not meaningfully cheaper than the legacy update. It is about
`91-95%` of the authoritative update time on sample and matrix. Removing
shadow-only comparison/digest/order checks from a future real path would remove
additional diagnostic cost, but it would not make the current host grouping pass
cheap enough as an added pre-pass.

The comparison work is also substantial. Full set comparison and digesting cost
about another build-sized pass over the shadow/real safe-store contents, and the
digest subpart is about half of comparison time. That reinforces that the shadow
is an exactness oracle, not a production timing proxy.

## Answers

| question | answer |
| --- | --- |
| Is shadow cost dominated by group/build or by comparison/digest/order checks? | The production-relevant shadow build is dominated by group/build. Shadow-only comparison is also large, but it is separate validation work. |
| Is group/build itself meaningfully cheaper than legacy update? | No. Group/build is `90.89%` of sample update and `94.73%` of matrix update. |
| Would a real precombine path likely be faster if validation/compare were removed? | Not as an added host pre-pass. A real path would need to replace the legacy update loop or use a cheaper grouping layout. |
| Is allocation/reserve a visible cost? | No. Allocation/reserve is below `0.05%` of build time on covered paths. |
| Should the next PR be a real precombine path? | No. The next optimization PR should pivot to initial prune/index rebuild shadow or another initial safe-store subphase. |

## Recommendation

Do not implement a host-side real precombine path from the current structure.
The exactness and duplicate ratio remain strong, but the measured group/build
cost is too close to the existing authoritative update loop.

Recommended next step:

```text
initial prune/index rebuild shadow
```

If precombine is revisited later, it should start from a different data
structure or from replacing the authoritative update loop under a validation
gate, not by adding this host grouping pass ahead of the existing update.
