# Fasim GASAL2 Long-Query Boundary

This checkpoint records the current long-query boundary for the GASAL2
scoreInfo/preAlign line. It prevents the short-query top5 milestone from being
overstated and avoids repeating the same max-query experiment.

## Current Boundary

The formal top5 GASAL2 preset remains bounded to:

```text
GASAL2_MAX_QUERY_LEN=2812
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812
```

The current example query lengths are:

```text
MEG3   query_len = 1582   supported by the formal short-query path
MALAT1 query_len = 8708   guarded out
NEAT1  query_len = 22767  guarded out
```

`make check-fasim-exact-scoreinfo-gpu-examples-gate` verifies this boundary:

```text
MEG3:
  query_preflight_supported = 1
  scoreinfo_gasal2_active = 1
  GASAL2 requests > 0
  exact scoreInfo GPU tasks > 0
  overflow/fallback = 0

MALAT1/NEAT1:
  query_preflight_supported = 0
  scoreinfo_gasal2_active = 0
  GASAL2 requests = 0
  exact scoreInfo GPU tasks = 0
  top5 clean via CPU fallback
```

## Max-Query Probe

A separate characterization build tried to make MALAT1 fit GASAL2 by rebuilding
GASAL2 with:

```text
GASAL2_MAX_QUERY_LEN=8708
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=8708
```

The result is not a viable runtime path:

```text
batch=20000, streams=3:
  fails in GASAL2 allocation with CUDA out-of-memory

batch=128, streams=1:
  runs without length fallback
  rows = 799 -> 570
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true
  wall = 23.11s -> 95.31s
  GASAL2 total = 83.43s
```

## Segmented GASAL2 Long-Query Probes

Segmented GASAL2 long-query probes tested the different-architecture path from
the plan. The bounded sample is MALAT1 first8 with `query_len = 8708`,
`tile_len = 2812`, `tile_overlap = 512`, and `max_segments = 4`.

The direct segmented traceback shadow is correctness-clean but performance
no-go:

```text
direct segmented traceback shadow:
  gasal2_requests = 500352
  traceback_requests = 500352
  fallbacks = 0
  top5 score/stability/nt_score = true/true/true
  CPU fallback wall ~= 23s
  segmented shadow total ~= 64s
```

Descriptor pruning was then wired into the traceback shadow with:

```text
pruned segmented traceback shadow:
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=37
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE=score_position_edges
  gasal2_requests = 467024
  traceback_requests = 467024
  fallbacks = 0
  top5 score/stability/nt_score = true/true/true
  CPU fallback wall ~= 23.11s
  segmented traceback shadow total ~= 63.52s
```

This proves the pruning selector is connected to full segmented traceback
shadow, but descriptor pruning alone does not make GASAL2 traceback viable.

The score-prepass batched shadow gives a positive stage-only signal:

```text
score-prepass batched shadow:
  gasal2_requests = 28032
  traceback_requests = 0
  fallbacks = 0
  top5 score/stability/nt_score = true/true/true
  segmented score-prepass shadow total ~= 2s
```

That result does not provide endpoint, CIGAR, traceback, candidate state,
output, or digest authority.

CPU replay with no-last can preserve the bounded top5 artifact through MALAT1
first128, but performance remains marginal:

```text
CPU replay with no-last:
  scoreinfo_max_per_task = 37
  prune_mode = score_position_edges
  top5 score/stability/nt_score = true/true/true
  malat1_first8 speedup=1.009996x
  malat1_first16 speedup=1.029101x
  malat1_first32 speedup=1.031832x
  malat1_first64 speedup=1.034623x
  malat1_first128 speedup=1.038017x
```

This is not enough to justify a long-query real path.
The recorded first8/first16/first32/first64/first128 scaling artifacts are
checked by:

```bash
make check-fasim-gasal2-long-query-segmented-no-last-scaling-result
```

## Decision

Increasing `GASAL2_MAX_QUERY_LEN` is not a valid continuation path for the
formal preset:

```text
MALAT1:
  either OOMs at useful batch shape
  or runs much slower and changes the top5 stability artifact

NEAT1:
  query_len = 22767 is beyond the tested MALAT1 expansion and remains guarded
```

Long-query workloads should remain on CPU fallback unless a different execution
design is introduced.

The current segmented no-last replay line is also stopped for real path:

```text
current segmented no-last replay line: stopped for real path
```

This stop checkpoint is checked by:

```bash
make check-fasim-gasal2-long-query-current-stop
```

## Allowed Next Designs

A future long-query GPU/GASAL2 line has to be a different architecture, for
example:

```text
query tiling with proven top5 artifact equivalence
segmented GASAL2 requests with deterministic merge
lower-memory GPU DP that preserves top5 score/stability/nt_score artifacts
CPU fallback authority with shadow validation before any opt-in
```

The executable follow-up plan is:

```text
docs/plans/2026-06-05-fasim-long-query-gasal2-segmented-shadow.md
```

Plan gate:

```bash
make check-fasim-gasal2-long-query-segmented-plan
make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow
make check-fasim-gasal2-long-query-segmented-replay-no-last
```

Any such design must prove:

```text
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
scoreinfo_gasal2_active = 1
GASAL2/exact-scoreInfo fallback = 0
GPU total < CPU fallback
```

Until then, long-query MALAT1/NEAT1 are not GASAL2-active successes.

## Verification

Focused boundary gate:

```bash
make check-fasim-gasal2-long-query-boundary
```

Runtime examples boundary:

```bash
make check-fasim-exact-scoreinfo-gpu-examples-gate
```
