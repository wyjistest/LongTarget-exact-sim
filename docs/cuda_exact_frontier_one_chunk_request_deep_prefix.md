# CUDA Exact Frontier One-Chunk Request Deep Prefix

This docs-only checkpoint characterizes selected request/window deep-prefix coverage using existing bounded one-chunk shadow telemetry. It adds no replay behavior, CPU intermediate-state snapshot, CUDA kernel, gate change, or authority path.

## Deep-Prefix Table

| request_index | request_input_summaries | max_summaries | processed | coverage | truncated | mismatches | h2d | d2h | runtime note |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 1,720,991 | 65,536 | 65,536 | 3.808% | 1 | 0 | 2,097,152 | 1,832 | completed sample smoke |
| 24 | 1,200,010 | 65,536 | 65,536 | 5.461% | 1 | 0 | 2,097,152 | 1,832 | completed sample smoke |
| 47 | 1,091,537 | 65,536 | 65,536 | 6.004% | 1 | 0 | 2,097,152 | 1,832 | completed sample smoke |

The current bounded-shadow runtime hard-caps `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_MAX_SUMMARIES` at 65,536. A `MAX_SUMMARIES=262144` request-index-0 smoke reported `max_summaries=65536` and `processed_summaries=65536`, so 262K, 1M, and full selected-request prefixes were not honestly exercised in this checkpoint.

## Interpretation

Selected request deep prefixes remained mismatch-free for first, middle, and last sampled request/window indexes at the current 65,536 cap. This extends the earlier 4,096 request-prefix coverage, but does not prove full request replay because each request is still truncated.

Increasing `MAX_SUMMARIES` beyond 65,536 requires a bounded-shadow cap policy change before it can produce deeper telemetry. That change should stay default-off and should not flip clean gate state or global replay backend support.

Tail, middle, and offset modes remain standalone subrange diagnostics, not true production intermediate-state replay. True middle/tail validation still needs CPU intermediate-state snapshot support for candidate state, running floor, first-max/tie, safe-store digest, and safe-store epoch.

Recommended next PR: raise or parameterize the bounded-shadow max cap for selected request-prefix coverage if deeper prefix evidence is desired; otherwise move to CPU intermediate-state snapshot support design.
