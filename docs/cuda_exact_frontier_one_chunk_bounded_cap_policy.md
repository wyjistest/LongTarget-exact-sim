# CUDA Exact Frontier One-Chunk Bounded Cap Policy

This PR makes bounded one-chunk shadow cap policy explicit. It does not change production authority, clean gate state, replay semantics, or route through `gpu_real` / `ordered_segmented_v3`.

Default policy keeps the conservative 65,536-summary cap. `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_ALLOW_LARGE_PREFIX=1` raises the cap to 1,048,576 only for selected `request` mode; all-request prefix and standalone subrange modes stay capped at 65,536.

| request | requested_max | effective_max | hard_cap | clamped | processed | input | coverage | mismatches | h2d | d2h |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 65,536 | 65,536 | 65,536 | 0 | 65,536 | 1,720,991 | 3.808% | 0 | 2,097,152 | 1,832 |
| 0 | 262,144 | 65,536 | 65,536 | 1 | 65,536 | 1,720,991 | 3.808% | 0 | 2,097,152 | 1,832 |
| 0 | 262,144 | 262,144 | 1,048,576 | 0 | 262,144 | 1,720,991 | 15.232% | 0 | 8,388,608 | 1,832 |
| 0 | 1,048,576 | 1,048,576 | 1,048,576 | 0 | 1,048,576 | 1,720,991 | 60.929% | 0 | 33,554,432 | 1,832 |

The 65,536 clamp is now visible through requested/effective/hard cap telemetry and `cap_clamped`. The 262K selected request-prefix run is genuinely processed only when the large-prefix opt-in is set.

1M selected request-prefix coverage was feasible for request 0 under the large-prefix opt-in and remained mismatch-free. Full all-request replay remains out of scope and guarded by the default cap; broader 1M coverage across selected requests should be a follow-up characterization PR.
