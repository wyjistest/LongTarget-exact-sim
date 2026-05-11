# CUDA Exact Frontier One-Chunk Selected Full Request Coverage

This PR adds a default-off selected full-request cap policy for the bounded one-chunk shadow. It is still request-mode diagnostic shadow coverage only: it does not validate full 44.8M all-request replay, true tail/middle production intermediate-state replay, safe-store digest/epoch shadow, or chunk-boundary equivalence.

The full-request policy is active only when all of the following are set:

- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_SHADOW=1`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_RANGE_MODE=request`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_REQUEST_INDEX=<idx>`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_ALLOW_FULL_REQUEST=1`

The absolute hard cap is 2,097,152 summaries. Prefix, tail, middle, offset, and all-request coverage keep the existing conservative caps.

| request | input | processed | fully_processed | truncated | h2d | d2h | mismatches | runtime note |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 47 | 1,091,537 | 1,091,537 | 1 | 0 | 34,929,184 | 1,832 | 0 | full selected request |
| 24 | 1,200,010 | 1,200,010 | 1 | 0 | 38,400,320 | 1,832 | 0 | full selected request |
| 0 | 1,720,991 | 1,720,991 | 1 | 0 | 55,071,712 | 1,832 | 0 | full selected request |

All three selected full-request runs reported `hard_cap=2,097,152`, `cap_clamped=0`, `full_request_active=1`, `full_request_supported=1`, and `full_request_disabled_reason=none`. Candidate digest, min-candidate/runningMin, first-max/tie, safe-store digest, and total bounded mismatch counters were all zero.

Guard checks:

| mode | request_index | allow_full_request | requested | effective | hard_cap | clamped | calls | processed | disabled_reason |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| prefix | all | 1 | 2,097,152 | 65,536 | 65,536 | 1 | 48 | 3,145,728 | request_mode_required |
| request | all | 1 | 2,097,152 | 65,536 | 65,536 | 1 | 0 | 0 | request_index_not_set |

The guard checks confirm `ALLOW_FULL_REQUEST=1` does not affect prefix/all-request coverage and does not activate without an explicit request index.

Clean gate telemetry remained `active=0`, `supported=0`, and `authority=cpu`; global one-chunk replay backend support remained `0`, and production `one_chunk_compare_calls` remained `0`.

The next bounded characterization step should be all 48 requests individually full-request coverage. CPU intermediate-state snapshots should wait until individual full requests are characterized, because snapshots are only needed for true production tail/middle state comparisons.
