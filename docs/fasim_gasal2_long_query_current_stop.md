# Fasim GASAL2 Current Long-Query Implementation Stop Checkpoint

This checkpoint records the decision for the current MALAT1/NEAT1 long-query
GASAL2 scoreInfo/preAlign implementation attempts.

## Decision

```text
current segmented no-last replay line: stopped for real path
correctness clean through MALAT1 first128
performance marginal through MALAT1 first128
```

The current implementation line should remain diagnostic only. It should not be
promoted to a real scoreInfo/preAlign path for long-query workloads.

## Evidence

The current best long-query candidate is segmented score-prepass plus CPU
no-last replay with:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY=1
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST=1
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK=37
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE=score_position_edges
```

Scaling evidence:

```text
malat1_first8 speedup=1.009996x
malat1_first16 speedup=1.029101x
malat1_first32 speedup=1.031832x
malat1_first64 speedup=1.034623x
malat1_first128 speedup=1.038017x
```

The same rows are top5 score/stability/nt_score clean and fallback-clean, but
the end-to-end speedup remains too small for a real long-query path.

Already-tested related lines:

```text
direct segmented traceback shadow: no-go
pruned segmented traceback shadow: no-go
score-prepass batched shadow: stage-only
single-pass topN: not top5-safe
max-query GASAL2 expansion: no-go
```

## Forbidden Promotions

do not promote segmented long-query no-last replay
do not promote GASAL2 traceback for long-query output
do not promote score-prepass stage-only output
do not continue current segmented/no-last implementation as a real path

These paths do not establish long-query production output, full scoreInfo
replacement, endpoint authority, CIGAR authority, traceback authority, or final
TFO equivalence.

## Allowed Continuation

Next universal-path work must be a different long-query architecture or
full-output equivalence proof.

The next-architecture implementation plan is:

```text
docs/plans/2026-06-06-fasim-long-query-gasal2-next-architecture.md
```

Plan gate:

```bash
make check-fasim-gasal2-long-query-next-architecture-plan
```

Examples of different architecture work:

```text
query tiling with exact candidate equivalence
lower-memory GPU DP with deterministic merge
different candidate generation that avoids CPU replay dominance
full-output equivalence proof for the accepted product scope
```

Any continuation must prove:

```text
scoreinfo_gasal2_active = 1
fallback = 0
top5 score/stability/nt_score clean
GPU/GASAL2 total < CPU fallback by a meaningful margin
output contract explicitly scoped and verified
```

## Gates

```bash
make check-fasim-gasal2-long-query-current-stop
make check-fasim-gasal2-long-query-segmented-no-last-scaling-result
```
