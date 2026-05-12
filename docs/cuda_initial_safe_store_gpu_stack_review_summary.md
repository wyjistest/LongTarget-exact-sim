# Initial Safe-Store GPU Stack Review Summary

This is the integration summary for the safe-store GPU stack from PR #21
through PR #30. The stack should be reviewed as a completed optimization line,
not as a base for more feature work before review feedback.

## Stack

| PR | Title | Purpose |
| --- | --- | --- |
| #21 | cuda: add initial safe-store GPU precombine shadow | Default-off diagnostic GPU unique-start precombine, compared against CPU authoritative post-update safe store. |
| #22 | cuda: add opt-in initial safe-store GPU precombine | Default-off real opt-in that feeds GPU-precombined unique states into host safe-store update, with validation/fallback. |
| #23 | cuda: add GPU-resident initial safe-store precombine source | Reuses GPU-resident initial summaries and avoids the redundant summary H2D upload when available. |
| #24 | cuda: add GPU-pruned safe-store precombine shadow | Default-off diagnostic device prune after GPU precombine, compared against CPU authoritative post-prune safe store. |
| #25 | cuda: add opt-in GPU-pruned safe-store precombine | Default-off real opt-in that downloads only GPU-pruned kept states and skips CPU prune in that opt-in path. |
| #26 | cuda: add packed kept-state D2H measurement | Measurement-only packed kept-state D2H path for post-prune kept states. |
| #27 | cuda: add packed kept-state materialization opt-in | Default-off packed kept-state materialization opt-in, with validation/fallback. |
| #28 | cuda: characterize packed safe-store materialization | 3-run A/B showing packed real is exact-clean and saves bytes, but does not win median wall-clock. |
| #29 | cuda: add fast safe-store materialization opt-in | Default-off host-only fast materialize/index build opt-in, exact-clean but not the median wall-clock winner. |
| #30 | cuda: document initial safe-store GPU best path | Consolidates the current best path and documents the recommended opt-in. |

## Recommended Opt-In

The current recommended safe-store GPU opt-in is:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

This should remain default-off. The best-path target is:

```bash
make check-sim-initial-safe-store-gpu-best-path
```

It asserts the recommended path is active and that packed D2H and fast
materialize are off.

## Best-Path A/B

The current 3-run sample median from PR #30:

| Mode | total s | sim s | initial scan s | rebuild s | D2H bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| legacy | 15.8349 | 13.7844 | 9.02808 | 3.19147 | 0 |
| resident GPU precombine | 14.7726 | 12.7549 | 7.95158 | 2.30742 | 317919276 |
| resident GPU precombine + GPU prune | 12.6598 | 10.6354 | 6.27427 | 0.699733 | 119203236 |
| resident GPU precombine + GPU prune + packed real | 13.1878 | 11.1486 | 6.85908 | 1.02084 | 66224020 |
| resident GPU precombine + GPU prune + fast materialize | 12.9951 | 10.869 | 6.56624 | 0.692826 | 119203236 |

Best-path median delta versus legacy:

```text
total_seconds:              -3.1751s
sim_seconds:                -3.1490s
sim_initial_scan_seconds:   -2.75381s
initial_store_rebuild:      -2.491737s
```

## Negative Branches

Packed real and fast materialize are useful evidence, but they should not be
recommended or defaulted from this stack.

Packed real:

- Exact-clean and fallback-clean.
- Reduces kept-state D2H bytes.
- Does not beat resident GPU precombine + GPU prune in the 3-run median.

Fast materialize:

- Exact-clean and fallback-clean.
- Reduces a host materialize/index slice.
- Does not beat resident GPU precombine + GPU prune in the 3-run median.

These branches should remain diagnostic or specialized opt-ins until a separate
A/B shows a stable wall-clock win.

## Correctness And Boundary

Across the relevant sample A/B and opt-in checks:

```text
size/candidate/order/digest mismatches = 0
fallbacks = 0
```

Authority and routing boundaries:

- CPU remains the default authority.
- CPU upload, locate, region, and output handoff remain unchanged.
- Candidate/frontier replay is unchanged.
- The exact-frontier clean gate remains inactive and unsupported.
- There is no route through `gpu_real`, `ordered_segmented_v3`, or
  `EXACT_FRONTIER_REPLAY`.
- No runtime default changes are part of the stack.

## Tests Run In The Stack

Representative checks from the stack include:

```bash
make build-cuda
make check-benchmark-telemetry
make check-sim-locate-update
make check-sample-cuda-sim-region-locate
make check-matrix-cuda-sim-region
make check-sim-initial-safe-store-gpu-precombine-shadow
make check-sim-initial-safe-store-gpu-precombine
make check-sim-initial-safe-store-gpu-precombine-validate
make check-sim-initial-safe-store-gpu-precombine-resident
make check-sim-initial-safe-store-gpu-precombine-prune-shadow
make check-sim-initial-safe-store-gpu-precombine-prune
make check-sim-initial-safe-store-gpu-best-path
make check-sim-initial-safe-store-gpu-precombine-prune-validate
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h-real
make check-sim-initial-safe-store-gpu-precombine-prune-packed-d2h-real-validate
make check-sim-initial-safe-store-gpu-precombine-prune-fast-materialize
make check-sim-initial-safe-store-gpu-precombine-prune-fast-materialize-validate
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_SHADOW_GATE=1 make check-sample-cuda-sim-region-locate
git diff --check
changed-file bidi scan
```

## Suggested Reviewer Focus

Reviewers should focus on:

- Whether the recommended opt-in remains clearly default-off.
- Whether validation/fallback behavior is sufficient for the real opt-in paths.
- Whether resident-source fallback semantics are clear when device summaries are
  unavailable.
- Whether CPU upload/locate/region authority boundaries are preserved.
- Whether packed real and fast materialize are correctly documented as
  non-recommended branches despite local metric wins.
- Whether the stack should be merged as-is before any wider workload/default
  discussion.

## Stop Point

No further feature work should be added to this safe-store GPU stack before
review feedback. The next useful follow-up after review is a separate
telemetry-only characterization of remaining CUDA SIM bottlenecks under the
recommended best path.
