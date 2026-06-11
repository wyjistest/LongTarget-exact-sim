# Fasim GASAL2 Emission-Only Consumer Debug

This checkpoint narrows the current
`FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1` no-go result. It is not a real
runtime path and it does not change output authority.

## NEAT1 first64 Result

The current broad emission-only consumer shadow remains a correctness and
performance no-go:

```text
decision = emission_only_consumer_shadow_correctness_no_go
candidate_vs_baseline = 0.157653x
cpu_align_attempts = 52,994
realpath_reference_align_attempts = 140,087
align_attempt_reduction = 87,093
triplex_mismatches = 4,404
missing_triplexes = 2,096
extra_triplexes = 1,460
```

It reduces CPU align attempts, but it changes the emitted triplex stream and is
much slower than the CPU-authority baseline.

## Focused Mismatch Evidence

A focused NEAT1 debug run around `task_key=49` shows the first local divergence
is not a score mismatch. GASAL2 and CPU agree on score for the relevant
attempt, but disagree on the endpoint/terminal condition:

```text
task_key=49 scoreinfo_index=6 attempt_index=26
  prealign_score = 162
  cpu_score = 137
  cpu_ref_end = 1574
  cpu_terminal = 0
  shadow_score = 137
  shadow_ref_end = 1575
  shadow_terminal = 1
```

That makes the shadow selector choose attempt `26`, while legacy chooses attempt
`27`:

```text
legacy_emit_reason = terminal
legacy_attempt_index = 27
legacy_align_score = 99
legacy_ref_end = 1575

shadow_emit_reason = terminal
shadow_attempt_index = 26
shadow_score = 137
shadow_ref_end = 1575
```

So GASAL2 score can match while GASAL2 endpoint/terminal is still not
Fasim-compatible.

## Variant Checks

`FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_NO_GPU_TERMINAL=1` is not a fix.
For the same task it removes the bad terminal pick at `scoreinfo_index=6`, but
creates other mismatches by falling back to `last_nonzero` where legacy selects
terminal:

```text
task_key=49 no_gpu_terminal summary mismatches = 3
```

`FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_VERIFY_TERMINAL=1` fixes the
focused `task_key=49` selection:

```text
task_key=49 verify_terminal summary mismatches = 0
```

That is a semantic probe only. It uses CPU `aligner.Align()` to verify terminal
candidates and is too expensive to promote as a performance path.

## Mismatch Taxonomy

An earlier unfiltered debug sample captured 471 summary mismatches:

```text
terminal -> terminal:      240
last_nonzero -> terminal:  184
last_nonzero -> threshold:  21
terminal -> threshold:      14
terminal -> last_nonzero:   12
```

The main mismatch class is endpoint/terminal/tie-policy authority, not just raw
score disagreement.

The threshold-divergence rows are more restrictive for future work. There are
35 cases where shadow emits by threshold but legacy does not. A focused debug
run for `task_key=117`, `scoreinfo_index=26` shows this is a score authority
problem, not only a selected-attempt summary artifact:

```text
task_key=117 scoreinfo_index=26 attempt_index=104
  prealign_score = 110
  cpu_score = 68
  cpu_ref_end = 2203
  cpu_query_end = 3003
  shadow_score = 138
  shadow_ref_end = 2172
  shadow_query_end = 2814

legacy_emit_reason = last_nonzero
legacy_attempt_index = 107
legacy_align_score = 58

shadow_emit_reason = threshold
shadow_attempt_index = 104
shadow_score = 138
```

The shadow score crosses `prealign_score=110`, while the CPU score for the same
attempt is only `68`. The shadow query endpoint is near a long-query tile
boundary (`2814`). This means the current long-query segmented max-score shape
is not a full-query legacy score/endpoint/tie-policy equivalent selector, and
it cannot be used as a simple safe threshold authority.

The score overestimate has a concrete parameter component. CPU
`StripedSmithWaterman::Aligner` defaults to gap open `16`, gap extend `4`, while
the current GASAL2 bridge default remains gap open `12`, gap extend `4`.
For the focused task117 row, forcing `FASIM_ALIGN_GASAL2_GAP_OPEN=16` changes
the same attempt from a false threshold hit to a below-threshold score:

```text
task_key=117 scoreinfo_index=26 attempt_index=104
  gap_open = 12: shadow_score = 138
  gap_open = 16: shadow_score = 104
  cpu_score = 68
  prealign_score = 110
```

However, this is not a safe default fix. Rebuilding with gap open `16` as the
GASAL2 default makes the existing NEAT1 first1 emission-only clean gate fail:

```text
triplex_mismatches = 12
missing_triplexes = 1
extra_triplexes = 15
decision = emission_only_consumer_shadow_mismatch_no_go
```

With `FASIM_ALIGN_GASAL2_GAP_OPEN=12`, the same first1 gate is clean:

```text
triplex_mismatches = 0
missing_triplexes = 0
extra_triplexes = 0
cpu_align_attempts = 718
realpath_reference_align_attempts = 2008
```

So gap-open alignment explains part of the score false-positive problem, but
changing it alone trades one correctness failure for another. The bridge keeps
its historical default and exposes `FASIM_ALIGN_GASAL2_GAP_OPEN` only as a
diagnostic A/B knob.

## Decision

Current emission-only consumer selector:

```text
score-only signal:
  useful for diagnostics only

endpoint / terminal authority:
  no-go

threshold authority from segmented max-score:
  no-go; task117 shows segmented GASAL2 score can overestimate CPU score

gap-open 16 parameter probe:
  useful diagnostic
  not a default fix

real replacement path:
  no
```

Allowed continuation:

```text
different long-query execution design with Fasim-compatible score/end/tie policy
or CPU-authority validation that still reduces total work enough to beat baseline
```

Forbidden:

```text
do not use GASAL2 endpoint as terminal authority
do not use current segmented max-score threshold as output authority
do not use current segmented GASAL2 score as a safe reject/accept authority
do not promote VERIFY_TERMINAL as a performance path
do not claim emission-only consumer equivalence from digest fallback
```
