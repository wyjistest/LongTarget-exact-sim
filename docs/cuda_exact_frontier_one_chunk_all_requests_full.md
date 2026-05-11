# CUDA Exact Frontier One-Chunk All Requests Full Characterization

This docs-only checkpoint characterizes all 48 request/window indexes with the selected full-request bounded one-chunk shadow policy. Each run is an independent `RANGE_MODE=request` diagnostic shadow replay with an explicit `REQUEST_INDEX`; this is not full 44.8M all-request replay, clean gate support, or production authority.

All runs used:

- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_INPUT_ADAPTER=1`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_SHADOW=1`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_RANGE_MODE=request`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_ALLOW_FULL_REQUEST=1`
- `LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_ONE_CHUNK_BOUNDED_MAX_SUMMARIES=2097152`

Every request reported `requested_max=2097152`, `effective_max=2097152`, `hard_cap=2097152`, and `cap_clamped=0`.

| request | input | processed | fully_processed | truncated | clamped | h2d | d2h | mismatches | note |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 1720991 | 1720991 | 1 | 0 | 0 | 55071712 | 1832 | 0 | 2.203s |
| 1 | 694262 | 694262 | 1 | 0 | 0 | 22216384 | 1832 | 0 | 0.827s |
| 2 | 625316 | 625316 | 1 | 0 | 0 | 20010112 | 1832 | 0 | 0.771s |
| 3 | 957830 | 957830 | 1 | 0 | 0 | 30650560 | 1832 | 0 | 1.077s |
| 4 | 116515 | 116515 | 1 | 0 | 0 | 3728480 | 1832 | 0 | 0.106s |
| 5 | 622555 | 622555 | 1 | 0 | 0 | 19921760 | 1832 | 0 | 0.732s |
| 6 | 1664170 | 1664170 | 1 | 0 | 0 | 53253440 | 1832 | 0 | 2.096s |
| 7 | 788570 | 788570 | 1 | 0 | 0 | 25234240 | 1832 | 0 | 0.941s |
| 8 | 633440 | 633440 | 1 | 0 | 0 | 20270080 | 1832 | 0 | 0.776s |
| 9 | 813569 | 813569 | 1 | 0 | 0 | 26034208 | 1832 | 0 | 0.866s |
| 10 | 116146 | 116146 | 1 | 0 | 0 | 3716672 | 1832 | 0 | 0.105s |
| 11 | 834299 | 834299 | 1 | 0 | 0 | 26697568 | 1832 | 0 | 0.999s |
| 12 | 1662486 | 1662486 | 1 | 0 | 0 | 53199552 | 1832 | 0 | 2.101s |
| 13 | 761704 | 761704 | 1 | 0 | 0 | 24374528 | 1832 | 0 | 0.933s |
| 14 | 1229254 | 1229254 | 1 | 0 | 0 | 39336128 | 1832 | 0 | 1.570s |
| 15 | 813625 | 813625 | 1 | 0 | 0 | 26036000 | 1832 | 0 | 0.890s |
| 16 | 104216 | 104216 | 1 | 0 | 0 | 3334912 | 1832 | 0 | 0.094s |
| 17 | 1612015 | 1612015 | 1 | 0 | 0 | 51584480 | 1832 | 0 | 1.987s |
| 18 | 1258011 | 1258011 | 1 | 0 | 0 | 40256352 | 1832 | 0 | 1.544s |
| 19 | 1445537 | 1445537 | 1 | 0 | 0 | 46257184 | 1832 | 0 | 1.784s |
| 20 | 1281477 | 1281477 | 1 | 0 | 0 | 41007264 | 1832 | 0 | 1.631s |
| 21 | 449749 | 449749 | 1 | 0 | 0 | 14391968 | 1832 | 0 | 0.393s |
| 22 | 436483 | 436483 | 1 | 0 | 0 | 13967456 | 1832 | 0 | 0.459s |
| 23 | 1608997 | 1608997 | 1 | 0 | 0 | 51487904 | 1832 | 0 | 1.991s |
| 24 | 1200010 | 1200010 | 1 | 0 | 0 | 38400320 | 1832 | 0 | 1.447s |
| 25 | 613420 | 613420 | 1 | 0 | 0 | 19629440 | 1832 | 0 | 0.703s |
| 26 | 1539755 | 1539755 | 1 | 0 | 0 | 49272160 | 1832 | 0 | 1.939s |
| 27 | 645694 | 645694 | 1 | 0 | 0 | 20662208 | 1832 | 0 | 0.650s |
| 28 | 287868 | 287868 | 1 | 0 | 0 | 9211776 | 1832 | 0 | 0.305s |
| 29 | 1009576 | 1009576 | 1 | 0 | 0 | 32306432 | 1832 | 0 | 1.187s |
| 30 | 1719103 | 1719103 | 1 | 0 | 0 | 55011296 | 1832 | 0 | 2.168s |
| 31 | 680202 | 680202 | 1 | 0 | 0 | 21766464 | 1832 | 0 | 0.801s |
| 32 | 1155967 | 1155967 | 1 | 0 | 0 | 36990944 | 1832 | 0 | 1.469s |
| 33 | 954732 | 954732 | 1 | 0 | 0 | 30551424 | 1832 | 0 | 1.058s |
| 34 | 114660 | 114660 | 1 | 0 | 0 | 3669120 | 1832 | 0 | 0.105s |
| 35 | 1608782 | 1608782 | 1 | 0 | 0 | 51481024 | 1832 | 0 | 1.995s |
| 36 | 957719 | 957719 | 1 | 0 | 0 | 30647008 | 1832 | 0 | 1.147s |
| 37 | 1406317 | 1406317 | 1 | 0 | 0 | 45002144 | 1832 | 0 | 1.730s |
| 38 | 1015622 | 1015622 | 1 | 0 | 0 | 32499904 | 1832 | 0 | 1.286s |
| 39 | 395397 | 395397 | 1 | 0 | 0 | 12652704 | 1832 | 0 | 0.328s |
| 40 | 554630 | 554630 | 1 | 0 | 0 | 17748160 | 1832 | 0 | 0.615s |
| 41 | 1491446 | 1491446 | 1 | 0 | 0 | 47726272 | 1832 | 0 | 1.860s |
| 42 | 1126706 | 1126706 | 1 | 0 | 0 | 36054592 | 1832 | 0 | 1.332s |
| 43 | 350915 | 350915 | 1 | 0 | 0 | 11229280 | 1832 | 0 | 0.370s |
| 44 | 1542875 | 1542875 | 1 | 0 | 0 | 49372000 | 1832 | 0 | 1.946s |
| 45 | 645552 | 645552 | 1 | 0 | 0 | 20657664 | 1832 | 0 | 0.653s |
| 46 | 417336 | 417336 | 1 | 0 | 0 | 13354752 | 1832 | 0 | 0.468s |
| 47 | 1091537 | 1091537 | 1 | 0 | 0 | 34929184 | 1832 | 0 | 1.307s |

Summary:

- 48 / 48 requests replayed fully with `request_fully_processed=1` and `truncated=0`.
- No request exceeded the 2,097,152-summary absolute hard cap; `cap_clamped=0` for all 48.
- Bounded mismatch counters were zero for all 48 requests.
- The largest request was request 0 with 1,720,991 summaries.
- The largest H2D footprint was also request 0 with 55,071,712 bytes.
- Runtime followed request size; request 0 was the largest observed run at 2.203s. No mismatch, cap, or D2H outlier appeared.

Clean gate telemetry remained `active=0`, `supported=0`, and `authority=cpu` for the characterization runs. Global one-chunk replay backend support remained `0`, and production `one_chunk_compare_calls` remained `0`.

Interpretation:

This is strong evidence that production-shaped bounded request-mode shadow replay can consume and compare each individual request/window completely under the selected full-request policy. It still does not prove full all-request one-chunk replay, true tail/middle production intermediate-state replay, safe-store digest/epoch shadow, chunk-boundary equivalence, clean gate support, or production authority.

The next PR should be a production one-chunk backend design milestone. It should decide whether a future backend replays per request/window or as a true all-request stream, define memory and batching policy, specify result aggregation, add safe-store digest/epoch coverage, and state the exact conditions required before the clean gate may become active.
