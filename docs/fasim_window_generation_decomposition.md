# Fasim Window-Generation Decomposition

Base branch:

```text
fasim-real-corpus-profile
```

This PR decomposes the existing Fasim profiling field
`fasim_window_generation_seconds`. It is profiling-only:

```text
no algorithm change
no output change
no CUDA kernel
no conservative filter
no threshold change
no non-overlap behavior change
no speedup claim
```

## Telemetry

The profile now emits:

```text
benchmark.fasim_window_generation_cut_sequence_seconds
benchmark.fasim_window_generation_transfer_seconds
benchmark.fasim_window_generation_reverse_seconds
benchmark.fasim_window_generation_source_transform_seconds
benchmark.fasim_window_generation_encode_seconds
benchmark.fasim_window_generation_flush_seconds
```

`fasim_window_generation_seconds` keeps its existing prep-time role. The new
`flush_seconds` value is different: it measures `flush_batch()` call wall time
as a diagnostic boundary and overlaps with DP scoring, column max, validation,
and output work. Do not add it to `fasim_window_generation_seconds` or to
stage totals.

## Local External Profiles

These runs use the same local humanLncAtlas input shapes documented in
`docs/fasim_real_corpus_profile.md`. The corpus files are not committed.

### human_lnc_atlas_17kb_target

```text
repeat = 2
canonical digest = sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
canonical output records = 0
windows = 4
dp_cells = 220,155,624
candidates = 57
final_hits = 0
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.000075 | 0.18% |
| window generation | 0.010645 | 25.51% |
| DP scoring | 0.019639 | 47.06% |
| column max | 0.011188 | 26.81% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000003 | 0.01% |
| output | 0.000000 | 0.00% |

| Window-generation detail | Seconds | Percent of total |
| --- | ---: | ---: |
| cutSequence | 0.000005 | 0.01% |
| transferString | 0.010230 | 24.51% |
| reverse/complement | 0.000009 | 0.02% |
| source transform | 0.000296 | 0.71% |
| encoded target build | 0.000102 | 0.24% |
| flush_batch call wall | 0.030836 | 73.89% |

```text
DP/scoring = 47.06%
DP + column = 73.87%
DP + column + transferString = 98.38%
```

### human_lnc_atlas_508kb_target

```text
repeat = 2
canonical digest = sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221
canonical output records = 34
windows = 104
dp_cells = 6,312,369,024
candidates = 1,367
final_hits = 34
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.002789 | 0.24% |
| window generation | 0.313515 | 26.66% |
| DP scoring | 0.551685 | 46.92% |
| column max | 0.304143 | 25.87% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000059 | 0.01% |
| output | 0.000181 | 0.02% |

| Window-generation detail | Seconds | Percent of total |
| --- | ---: | ---: |
| cutSequence | 0.000368 | 0.03% |
| transferString | 0.301226 | 25.62% |
| reverse/complement | 0.000244 | 0.02% |
| source transform | 0.008512 | 0.72% |
| encoded target build | 0.003086 | 0.26% |
| flush_batch call wall | 0.856204 | 72.82% |

```text
DP/scoring = 46.92%
DP + column = 72.79%
DP + column + transferString = 98.40%
```

## Decision

The decomposition identifies `transferString` as the dominant window-generation
cost on both real-shaped workloads:

```text
17kb target:
  transferString = 24.51% total
  transferString ~= 96% of window generation

508kb target:
  transferString = 25.62% total
  transferString ~= 96% of window generation
```

`cutSequence`, reverse/complement, source transform, and encoded target build
are not first-order targets in these runs. `flush_batch` is first-order wall
time, but it is an execution boundary around scoring/output and overlaps with
the existing DP/column/output telemetry.

The current data still does not support jumping directly to a narrow DP+column
CUDA prototype. DP+column is only about `73%` on the real-shaped workloads, so a
DP+column-only acceleration remains bounded near the #49 estimate. The more
promising target is the combined hot path:

```text
transferString window prep
DP scoring
column max
```

## Recommended Next Step

Create a narrow transferString-focused profiling/optimization PR before any
CUDA DP prototype:

```text
fasim transferString decomposition
```

It should answer:

```text
1. Which transferString mode/rule/strand cases dominate?
2. Is the cost from allocation, per-character conversion, branch structure, or
   repeated equivalent transforms?
3. Can transferString be made cheaper with table-driven CPU code, reuse, or
   batching without changing output?
4. After reducing transferString, does DP+column rise above the 80-90% range
   needed to justify a GPU DP+column prototype?
```

Any acceleration PR after this still needs the existing canonical digest checks
to remain byte-stable.
