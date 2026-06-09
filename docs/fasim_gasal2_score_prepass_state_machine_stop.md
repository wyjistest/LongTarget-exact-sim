# Fasim GASAL2 Score-Prepass State-Machine Stop

This checkpoint stops the current segmented score-prepass state-machine
consumer line as a real-path candidate.

It does not stop the broader scoreInfo/preAlign GPU/GASAL2 objective. It only
records that the current implementation shape is exhausted.

## Decision

```text
score-prepass state-machine consumer:
  correctness scaffold: clean
  current real path: no-go

continue only with:
  different traceback replacement
  different replacement-consumer design
  external digest gate
  performance win over CPU fallback
```

## Evidence

The default-off characterization showed clean triplexes on bounded NEAT1 and
MALAT1 rows:

```text
NEAT1 first1:
  triplex mismatches = 0
  candidate_vs_baseline = 0.530629x

NEAT1 first4:
  triplex mismatches = 0
  candidate_vs_baseline = 0.568306x

NEAT1 first16:
  triplex mismatches = 0
  candidate_vs_baseline = 0.522888x

MALAT1 first8:
  triplex mismatches = 0
  candidate_vs_baseline = 0.702397x
```

The audited trust path also stayed correctness-clean, but it did not reduce the
dominant CPU traceback work:

```text
NEAT1 first16:
  realpath_extend_align_attempts = 0
  state_machine_cpu_align_attempts = 35,152
  align_cache_hits = 0
  align_cache_misses = 35,152
  candidate_vs_baseline = 0.5951x
```

The local align cache is not a solution for the checked shape:

```text
cache hits = 0
unique keys = misses
```

GASAL2 traceback is also not a direct replacement for the state-machine CPU
`Align()` path:

```text
full-query GASAL2 traceback:
  guarded out at query_len = 22,767
  current guard = 2,812
  raising guard to 30,000 hit CUDA illegal memory access

selected-segment traceback:
  NEAT1 first1 mismatches = 1,288 / 2,008
  NEAT1 first4 mismatches = 5,337 / 8,480
  NEAT1 first16 mismatches = 22,000 / 35,152

expanded-segment oracle:
  mismatches = 0
  required_max_len = 22,767
  required_over_gasal2_limit = 21,991 on first16
```

This means the repair is effectively full-query traceback for many attempts,
not a small selected-segment overlap fix.

## Stop Rule

Do not continue by tuning the current segmented score-prepass state-machine
implementation.

Do not promote:

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1
```

Do not claim:

```text
GPU endpoint authority
GPU CIGAR authority
GPU traceback authority
replacement-consumer output authority
broad scoreInfo/preAlign replacement
```

## Allowed Continuation

A future continuation must be a different architecture and must prove all of:

```text
triplex_mismatches = 0
full output or explicitly scoped output contract clean
candidate total < CPU fallback on the claimed workload
CPU traceback attempts materially reduced or replaced
no GPU endpoint/CIGAR/traceback authority unless separately proven
```

Valid directions are:

```text
legacy-compatible full-query traceback replacement
consumer design that preserves scoreInfo-level single-emission semantics
broader full-output/TFO equivalence proof over an already scoped path
accepted top5-only product scope
```

Invalid directions are:

```text
more selected-only replay
more segmented no-last replay
more selected-segment traceback without full-query equivalence
more local align-cache tuning for this shape
raising GASAL2 query guard as a fix
```

## Gate

```bash
make check-fasim-gasal2-score-prepass-state-machine-stop
```
