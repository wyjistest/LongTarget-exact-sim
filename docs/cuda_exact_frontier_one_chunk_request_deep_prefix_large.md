# CUDA Exact Frontier One-Chunk Large Request Prefix Coverage

This docs-only checkpoint characterizes selected request/window prefixes using the allow-large bounded one-chunk policy. It adds no replay behavior, cap change, CPU intermediate-state snapshot, CUDA kernel, gate change, or authority path.

| request | input | requested | effective | processed | coverage | clamped | h2d | d2h | mismatches |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1,720,991 | 262,144 | 262,144 | 262,144 | 15.232% | 0 | 8,388,608 | 1,832 | 0 |
| 0 | 1,720,991 | 1,048,576 | 1,048,576 | 1,048,576 | 60.929% | 0 | 33,554,432 | 1,832 | 0 |
| 24 | 1,200,010 | 262,144 | 262,144 | 262,144 | 21.845% | 0 | 8,388,608 | 1,832 | 0 |
| 24 | 1,200,010 | 1,048,576 | 1,048,576 | 1,048,576 | 87.381% | 0 | 33,554,432 | 1,832 | 0 |
| 47 | 1,091,537 | 262,144 | 262,144 | 262,144 | 24.016% | 0 | 8,388,608 | 1,832 | 0 |
| 47 | 1,091,537 | 1,048,576 | 1,048,576 | 1,048,576 | 96.064% | 0 | 33,554,432 | 1,832 | 0 |

All runs used `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_ALLOW_LARGE_PREFIX=1`, `RANGE_MODE=request`, and `hard_cap=1,048,576`. Clean gate telemetry remained `active=0`, `supported=0`, and `authority=cpu`; global one-chunk replay backend support remained `0`, and production `one_chunk_compare_calls` remained `0`.

The 1,048,576 request-prefix runs are still prefix replay, not full request replay, because all three requests remain `truncated=1`. Request 47 is near-full at 96.064% coverage, but it still does not prove full request exactness.

Tail, middle, and offset modes remain standalone subrange diagnostics, not true production intermediate-state replay. The next step should be selected full-request cap policy if full request-prefix evidence is desired; CPU intermediate-state snapshots should wait until full selected requests are characterized.
