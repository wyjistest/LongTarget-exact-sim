# Fasim GASAL2 Long-Query Segmented Shadow

This document defines the first default-off diagnostic surface for a future
long-query GASAL2 scoreInfo/preAlign prototype. It is not production output.

## Scope

```text
default-off diagnostic only
CPU fallback remains authority
no production output use
no formal short-query preset change
no GASAL2_MAX_QUERY_LEN increase
```

The design keeps the current GASAL2 build boundary:

```text
GASAL2_MAX_QUERY_LEN=2812
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812
```

Long queries must be split into bounded segments instead of rebuilding GASAL2
with a larger max query length.

## Diagnostic Env

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512
FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=0
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE=score
```

`FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0` means unlimited. Test scripts may
set a positive cap for bounded probes.
`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1` switches the
segmented diagnostic from traceback to GASAL2 score-prepass selection only. It
must leave `traceback_requests = 0` and must not feed production output.
`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK` optionally
applies the same diagnostic scoreInfo pruning cap to segmented score-prepass or
traceback shadow runs. The default `0` preserves unpruned behavior.
`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE` selects the
diagnostic scoreInfo pruning strategy. The default `score` mode preserves the
previous highest-score-first behavior. Experimental `score_position_spread` and
`score_position_edges` modes retain some lower-score entries by position to
probe whether stability top5 rows can be preserved with fewer CPU replay calls.

The descriptor-collection runtime records request state and deterministic query
segments:

```text
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_query_len
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_len
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_overlap
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_segments
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_gasal2_requests
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_traceback_requests
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_fallbacks
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_max_per_task
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_prune_mode
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_total_seconds
```

Segments use zero-based half-open query offsets internally. Each segment is at
most `tile_len` bases. Before a real segmented GASAL2 execution implementation
exists, `active` must remain `0`; `gasal2_requests` and `traceback_requests`
must also remain `0`.
For the bounded MALAT1 first8 probe with `MAX_SEGMENTS=4`, expected telemetry is:

```text
query_len = 8708
tile_len = 2812
tile_overlap = 512
segments = 4
```

## Required Gate

The segmented shadow is only a continuation candidate if it proves:

```text
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
scoreinfo_gasal2_active = 1
GASAL2/exact-scoreInfo fallback = 0
GPU total < CPU fallback
```

The top5 comparison target is the CPU fallback authority. GPU segment results
must not enter candidate state, merged output, digest, endpoint, CIGAR, or
traceback authority.

## Stop Conditions

```text
top5 score/stability/nt_score changes
segment coordinate translation is ambiguous
GASAL2 fallback or overflow appears
GPU total is slower than CPU fallback
production output use is required before top5 equivalence is proven
```

Until the gate passes, MALAT1/NEAT1 remain guarded CPU fallback workloads, not
GASAL2-active successes.

## MALAT1 First8 Probe

The bounded Task 5 probe establishes that segmented GASAL2 execution can run as
a shadow, but the current direct traceback shape is not a performance candidate:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512
FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=4

decision = top5_artifact_no_go
query_len = 8708
segments = 4
active = 1
gasal2_requests = 500352
traceback_requests = 500352
fallbacks = 0
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
CPU fallback authority wall ~= 23s
segmented shadow total ~= 64s
```

This means the segment coordinate and top5 artifact smoke is clean for the
bounded MALAT1 sample, but one traceback batch per segment over all descriptors
is too slow. It remains diagnostic-only and must not feed production output.

## Pruned Traceback Shadow Probe

The same scoreInfo pruning selector can also be applied to direct segmented
GASAL2 traceback shadow. This tests whether descriptor reduction alone can make
the traceback-heavy path viable without CPU replay:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=0
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=37
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE=score_position_edges
```

MALAT1 first8 bounded result:

```text
decision = top5_artifact_no_go
query_len = 8708
segments = 4
gasal2_requests = 467024
traceback_requests = 467024
fallbacks = 0
scoreinfo_input_groups = 31272
scoreinfo_kept_groups = 29189
scoreinfo_pruned_groups = 2083
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
CPU fallback authority wall ~= 23.11s
segmented traceback shadow total ~= 63.52s
candidate wall ~= 98.30s
speedup_vs_baseline ~= 0.24x
```

This proves the pruning cap is wired into the full traceback shadow, but it does
not change the decision. Direct segmented GASAL2 traceback remains
correctness-clean and performance no-go for this bounded long-query sample.
It is not a real output path and does not make GASAL2 traceback authoritative.

## Score-Prepass Probe

The follow-up diagnostic mode avoids the traceback-heavy shape:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS=64

required:
  active = 1
  gasal2_requests > 0
  traceback_requests = 0
  fallbacks = 0
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
```

This is still shadow-only. A score-prepass win does not make GASAL2 endpoint,
CIGAR, traceback, candidate state, output, or digest authoritative.

Current MALAT1 first8 result:

```text
decision = top5_artifact_no_go
query_len = 8708
segments = 4
active = 1
gasal2_requests = 500352
traceback_requests = 0
fallbacks = 0
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
CPU fallback authority wall ~= 23s
segmented score-prepass shadow total ~= 44s
```

This removes the traceback cost, but score-prepass still processes too many
segment/request pairs and remains slower than CPU fallback on the bounded
MALAT1 sample.

Descriptor reduction alone is not enough:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=1

gasal2_requests = 28032
traceback_requests = 0
gasal2_score_batches = 7008
score_wait_seconds ~= 43s
segmented score-prepass shadow total ~= 43s
```

The request count drops, but the path still launches thousands of tiny score
batches.

Adding descriptor reduction plus batched flushes changes the signal:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS=64

decision = top5_artifact_go
query_len = 8708
segments = 4
active = 1
gasal2_requests = 28032
traceback_requests = 0
fallbacks = 0
scoreinfo_input_groups = 31272
scoreinfo_kept_groups = 1752
scoreinfo_pruned_groups = 29520
gasal2_score_batches = 116
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
CPU fallback authority wall ~= 23s
segmented score-prepass shadow total ~= 2s
```

This is a score-prepass-stage positive signal only. The candidate run still
executes CPU fallback for production output, so this is not a real output path.
The next gate would need to prove how a reduced GASAL2 score-prepass result can
feed CPU traceback or candidate selection without changing top5 artifacts.

## CPU Replay Probe

`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY=1` feeds selected
GASAL2 score-prepass descriptors into CPU traceback replay. GASAL2 still does
not provide endpoint, CIGAR, traceback, candidate state, output, or digest
authority.

MALAT1 first8 replay results:

```text
scoreinfo_max_per_task = 1:
  decision = top5_artifact_no_go
  candidate wall ~= 15s
  candidate rows = 65
  top5 score/stability/nt_score = false/false/false

scoreinfo_max_per_task = 8:
  decision = top5_artifact_no_go
  candidate wall ~= 21s
  candidate rows = 369
  top5 score/stability/nt_score = false/false/true

scoreinfo_max_per_task = 16:
  decision = top5_artifact_no_go
  candidate wall ~= 24s
  candidate rows = 568
  top5 score/stability/nt_score = true/false/true

scoreinfo_max_per_task = 32:
  decision = top5_artifact_no_go
  candidate wall ~= 27s
  candidate rows = 730
  top5 score/stability/nt_score = true/false/true

scoreinfo_max_per_task = 64:
  decision = top5_artifact_go
  gasal2_requests = 498480
  gasal2_score_batches = 128
  cpu_replay_attempts = 217730
  cpu_replay_selected = 31155
  cpu_replay_align_calls = 105763
  candidate rows = 793
  top5 score/stability/nt_score = true/true/true
  CPU fallback authority wall ~= 23s
  candidate wall ~= 28s
```

The replay architecture can preserve top5 when pruning is loose enough, but then
CPU replay work dominates and the candidate remains slower than CPU fallback.
Aggressive pruning is faster but drops top5 rows. This is not a real-path go.

## Replay-Preserving Prune Mode Probe

The default scoreInfo pruning mode keeps highest-score entries first. That mode
preserves score and nt-score top5 at `scoreinfo_max_per_task = 32`, but misses a
stability top5 row with lower score. The diagnostic prune mode env is:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE=score_position_edges
```

MALAT1 first8 bounded replay results:

```text
score_position_edges, scoreinfo_max_per_task = 36:
  decision = top5_artifact_no_go
  top5 score/stability/nt_score = true/false/true
  cpu_replay_align_calls = 100032
  candidate wall ~= 27.95s

score_position_edges, scoreinfo_max_per_task = 37:
  decision = top5_artifact_go
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 467024
  scoreinfo_kept_groups = 29189
  cpu_replay_align_calls = 100523
  candidate rows = 757
  CPU fallback authority wall ~= 23.22s
  candidate wall ~= 27.46s

score_position_edges, scoreinfo_max_per_task = 40:
  decision = top5_artifact_go
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 101903
  candidate wall ~= 28.57s

score mode, scoreinfo_max_per_task = 64:
  decision = top5_artifact_go
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 105763
  candidate wall ~= 27.74s
```

This is a correctness-shaping positive signal only. Position-aware pruning can
preserve the bounded MALAT1 top5 artifact with a smaller cap than score-only
`64`, but CPU replay still dominates and the candidate remains slower than CPU
fallback. This is not a real-path go.

## CPU Replay Candidate Reduction Probe

The CPU replay bottleneck is the number of GASAL2-selected descriptors that
still require CPU `Align()` to recover Fasim-compatible traceback semantics.
The existing candidate selector supports removing last-attempt candidates while
keeping threshold and fallback candidates:

```text
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST=1
```

MALAT1 first8 bounded replay with position-aware pruning:

```text
score_position_edges, scoreinfo_max_per_task = 37:
  no-last = 0
  top5 score/stability/nt_score = true/true/true
  cpu_replay_attempts = 203594
  cpu_replay_selected = 29189
  cpu_replay_align_calls = 100523
  CPU replay seconds ~= 12.55s
  candidate wall ~= 27.44s

score_position_edges, scoreinfo_max_per_task = 37:
  no-last = 1
  top5 score/stability/nt_score = true/true/true
  cpu_replay_attempts = 119453
  cpu_replay_selected = 26515
  cpu_replay_align_calls = 58341
  CPU replay seconds ~= 8.19s
  candidate wall ~= 23.88s
```

Bounded scaling with the same settings:

```text
MALAT1 first8:
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 467024
  cpu_replay_align_calls = 58341
  CPU fallback wall ~= 23.22s
  candidate wall ~= 22.79s
  speedup ~= 1.02x

MALAT1 first16:
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 1166784
  cpu_replay_align_calls = 146198
  CPU fallback wall ~= 57.87s
  candidate wall ~= 56.23s
  speedup ~= 1.03x

MALAT1 first32:
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 2166592
  cpu_replay_align_calls = 270570
  CPU fallback wall ~= 106.72s
  candidate wall ~= 103.43s
  speedup ~= 1.03x

MALAT1 first64:
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 4776704
  cpu_replay_align_calls = 597523
  CPU fallback wall ~= 236.14s
  candidate wall ~= 228.24s
  malat1_first64 speedup=1.034623x

MALAT1 first128:
  top5 score/stability/nt_score = true/true/true
  gasal2_requests = 10684256
  cpu_replay_align_calls = 1329852
  CPU fallback wall ~= 527.93s
  candidate wall ~= 508.59s
  malat1_first128 speedup=1.038017x
```

Disabling fallback candidates is not safe for this bounded probe:

```text
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST=1:
  top5 score/stability/nt_score = false/false/false
```

Replay ordering was also probed. The selected descriptors carry diagnostic
GASAL2 score-prepass fields, and the replay order can be set to:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_ORDER=threshold_score
```

MALAT1 first8 with `score_position_edges`, `scoreinfo_max_per_task = 37`, and
`no-last = 1`:

```text
legacy order:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 58341
  candidate wall ~= 22.79s

threshold_score order:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 58345
  candidate wall ~= 22.81s
```

Threshold-first ordering is therefore not a useful replay-reduction path for
this bounded sample.

This is a stronger replay-reduction signal than scoreInfo pruning alone, and it
stays top5-clean through MALAT1 first128. Performance remains marginal at about
1.01-1.04x, so this is still a bounded diagnostic rather than a real-path go.
It does not make GASAL2 endpoint, CIGAR, traceback, candidate state, output, or
digest authoritative.

## Verification

Static env/contract gate:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-env
make check-fasim-gasal2-long-query-segmented-shadow-default-off
make check-fasim-gasal2-long-query-segmented-scoreinfo-prune-mode
make check-fasim-gasal2-long-query-segmented-replay-no-last
make check-fasim-gasal2-long-query-segmented-no-last-scaling-result
make check-fasim-gasal2-long-query-segmented-record-limit
make check-fasim-gasal2-long-query-segmented-replay-score-order
make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow
```

Follow-up implementation plan:

```text
docs/plans/2026-06-05-fasim-long-query-gasal2-segmented-shadow.md
```
