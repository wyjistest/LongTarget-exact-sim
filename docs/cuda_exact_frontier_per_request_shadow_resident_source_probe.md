# CUDA Exact Frontier Per-Request Shadow Resident-Source Probe

This is a diagnostic performance probe only. CPU remains authoritative, runtime
defaults are unchanged, the clean gate remains inactive, and this path does not
feed GPU output into production output, safe-store authority, locate, region, or
planner decisions.

## Runtime Controls

```bash
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW=1
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_RESIDENT_SOURCE=1
```

Selection still uses the existing controls:

```bash
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_REQUEST_INDEX=47
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_PER_REQUEST_SHADOW_REQUEST_LIST=0,24,47
```

When resident summaries are unavailable, the diagnostic records a fallback and
uses the existing host-H2D shadow path.

## Fresh Sample Runs

All runs used the CUDA sample region/locate exactness command with oracle diff.
The full 48-request resident-source shadow was not run in this PR because the
3-request probe already spends about `5.5s` in the diagnostic shadow path; prior
full per-request audits are intentionally expensive and are better left as
manual correctness checks.

| Mode | Requests | Input source | H2D bytes | Summary H2D saved | D2H bytes | Shadow seconds | Kernel seconds | Compare seconds | Mismatches | Fallbacks |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Host-H2D shadow | 47 | host_h2d | 69,860,168 | 0 | 308,444 | 1.42948 | 1.32985 | 0.0996309 | 0 | 0 |
| Resident shadow | 47 | device_resident | 1,800 | 69,858,368 | 308,444 | 1.41532 | 1.32085 | 0.094464 | 0 | 0 |
| Host-H2D shadow | 0,24,47 | host_h2d | 256,807,832 | 0 | 9,044,844 | 5.40708 | 4.99617 | 0.410905 | 0 | 0 |
| Resident shadow | 0,24,47 | device_resident | 5,400 | 256,802,432 | 9,044,844 | 5.51423 | 5.08428 | 0.429949 | 0 | 0 |

## Interpretation

Resident-source replay is exact-clean for both sampled modes and eliminates the
redundant summary H2D upload. In the single-request smoke it is slightly faster,
but in the 3-request sample it is slightly slower on this run. The remaining
cost is dominated by the GPU shadow replay/safe-store diagnostic work rather
than summary upload.

This result is useful as a probe, but it is not enough to justify a real
production exact frontier replay path. The next decision point should compare
more repeats if this line stays active; otherwise, pivot to safe-workset
decomposition under the safe-store GPU best path.

## Validation

```bash
make build-cuda
make check-sim-initial-exact-frontier-per-request-shadow-smoke
make check-sim-initial-exact-frontier-per-request-shadow-resident-smoke
make check-sim-initial-exact-frontier-per-request-shadow-sampled
make check-sim-initial-exact-frontier-per-request-shadow-resident-sampled
make check-sim-initial-exact-frontier-per-request-shadow-invalid
make check-benchmark-telemetry
make check-sim-locate-update
make check-sample-cuda-sim-region-locate
make check-matrix-cuda-sim-region
make check-sim-initial-safe-store-gpu-best-path
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_SHADOW_GATE=1 make check-sample-cuda-sim-region-locate
make check-sim-cuda-region-docs
```

An additional combined opt-in sample enabled per-request resident shadow together
with the safe-store GPU best path. It confirmed both paths used
`device_resident` input and reported `fallbacks=0`.

All listed shadow runs completed with:

```text
sim_initial_exact_frontier_per_request_shadow_total_mismatches=0
sim_initial_exact_frontier_per_request_shadow_fallbacks=0
sim_initial_exact_frontier_per_request_shadow_authority=cpu
```
