# Fasim Long-Query Streaming ScoreInfo Fused MinScore Design

This started as a design checkpoint and now has a default-off prototype
boundary. It targets the current NEAT1/MALAT1 long-query streaming scoreInfo
bottleneck without changing default runtime behavior.

## Context

The current trust path is correctness-clean for MALAT1-like samples and NEAT1
non-shared samples, but NEAT1 remains performance no-go. The main GPU-side
reason is that the hot path runs two long-query DP passes:

```text
1. GPU max-score/minScore pass:
   prealign_cuda_find_max_scores_global_state_batch()

2. GPU scoreInfo pass:
   prealign_cuda_find_streaming_scoreinfo_batch_pruned()
```

For NEAT1 first64:

```text
tasks = 3,072
gpu_minscore_wall_seconds ~= 16.30s
gpu_call_seconds ~= 33.77s
gpu_total_seconds ~= 50.07s
baseline Running time = 87.1285s
candidate Running time = 123.041s
candidate/baseline speedup = 0.708143x
```

For NEAT1 first128 audited replay, correctness is clean but the wall time is
diagnostic-heavy:

```text
tasks = 6,144
gpu_minscore_wall_seconds = 34.414s
gpu_call_seconds = 67.0715s
gpu_total_seconds = 101.486s
segmented/full/oracle replay mismatches = 0
```

Do not use audited replay wall time as real runtime speedup evidence. The
audited run includes segmented/full/oracle replay probes.

## Prototype Boundary

The first prototype is wired behind:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1
```

It is diagnostic only. It must not be used with trust mode or real output
authority.

MALAT1 first8 boundary result:

```text
tasks = 1824
fused_minscore_requested = 1
fused_minscore_active = 1
fused_minscore_used = 1727
fused_minscore_fallbacks = 0
fused_minscore_score_mismatches = 97
fused_minscore_min_score_mismatches = 97
scoreinfo_mismatches = 92
candidate_missing = 0
candidate_extra = 0
output digest unchanged because GPU remains shadow-only
decision = streaming_scoreinfo_shadow_mismatch
```

This is a hard no-go for promoting the current fused prototype. The root cause
is semantic, not launch/resource failure: CPU `task.fullScore`/minScore follows
the legacy calc-score profile/target encoding, while streaming scoreInfo
compatibility follows the SSW byte-profile/Lazy-F scoreInfo path. A naive single
column-max pass does not simultaneously satisfy both contracts.

## Design

The next plausible implementation is a fused minScore + scoreInfo CUDA
prototype:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1
```

The fused path should:

```text
1. Run one column-max DP pass per batch.
2. Store column maxima as today.
3. Reduce column maxima to a per-task full score.
4. Derive minScore from that full score on device.
5. Compact scoreInfo candidates using the derived minScore.
6. Copy back scores, compacted scoreInfo, counts, and overflow state.
```

If the two contracts can be unified, this would remove the separate
`prealign_cuda_find_max_scores_global_state_batch()` DP pass from the hot path.
The current prototype does not prove that unification. It does not remove CPU
`extend`, traceback, CIGAR, or output authority.

## Required Telemetry

The prototype must expose separate telemetry:

```text
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_active
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_used
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_fallbacks
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_min_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_kernel_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_total_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_error
```

It should also continue reporting existing scoreInfo counters:

```text
scoreinfo_mismatches
candidate_missing
candidate_extra
gpu_scoreinfo_groups
cpu_scoreinfo_groups
realpath_used
realpath_fallbacks
output digest
```

## Correctness Gate

For any future shadow mode:

```text
fused_minscore_active = 1
fused_minscore_used = tasks
fused_minscore_fallbacks = 0
fused_minscore_score_mismatches = 0
fused_minscore_min_score_mismatches = 0
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
output digest unchanged
```

For trust mode:

```text
realpath_used = tasks
realpath_fallbacks = 0
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
compare_seconds = 0
output digest unchanged by external gate
```

## Performance Gate

The first useful target is NEAT1 because it currently exposes the two-pass cost
most clearly.

Hard gate:

```text
NEAT1 first64 fused trust:
  candidate/baseline speedup > 1.0x
  GPU total < current non-fused GPU total
```

Better gate:

```text
NEAT1 first64:
  fused GPU total <= current scoreInfo gpu_call_seconds + small overhead
```

The expected first-order improvement is bounded by removing the separate
minScore DP pass:

```text
current NEAT1 first64:
  gpu_minscore_wall_seconds ~= 16.30s
  gpu_call_seconds ~= 33.77s
  gpu_total_seconds ~= 50.07s
```

If the fused prototype remains slower than CPU or still loses whole-run
runtime, do not promote it as a real path.

The current prototype fails before the performance gate because score/minScore
and scoreInfo are not simultaneously clean.

## Non-Goals

Do not:

```text
change default behavior
use GPU endpoint
use GPU CIGAR
use GPU traceback
change output semantics
change scheduler policy
claim broad scoreInfo/preAlign replacement from MALAT1 alone
use audited replay wall time as real runtime speedup evidence
enable `FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1` with fused
  minScore
claim current fused prototype correctness
```

## Decision

```text
decision = fused_minscore_current_prototype_no_go
```

The next allowed direction is not promoting this prototype. It is either:

```text
1. prove a column-max representation that satisfies both legacy calc-score
   minScore and byte-profile scoreInfo contracts, or
2. implement a two-contract bridge that keeps legacy calc-score minScore and
   byte-profile scoreInfo separate inside one bounded bridge, or
3. keep the existing two-pass GPU path as the correctness-clean diagnostic path.
```

The follow-up design gate is:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
```

## Gate

```bash
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary
```
