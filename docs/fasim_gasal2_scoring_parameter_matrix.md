# Fasim GASAL2 Scoring Parameter Matrix

This is a diagnostic checkpoint, not a runtime path. It records why the current
GASAL2 emission-only consumer cannot be promoted by changing one scoring
parameter or by trusting GASAL2 endpoint/terminal fields.

## Focused Matrix

```text
task_key=49 scoreinfo_index=6 attempt_index=26
  CPU score = 137
  GASAL2 score = 137
  CPU ref_end = 1574, terminal = 0
  GASAL2 ref_end = 1575, terminal = 1
  legacy selects attempt 27
  shadow selects attempt 26
```

This is an endpoint/terminal mismatch. The score agrees, but the selector does
not.

```text
NO_GPU_TERMINAL:
  task_key=49 summary mismatches = 3

VERIFY_TERMINAL:
  task_key=49 summary mismatches = 0
```

`NO_GPU_TERMINAL` is not equivalent because legacy still needs terminal-best
selection. `VERIFY_TERMINAL` is only a semantic probe because it uses CPU
`aligner.Align()` to verify terminal candidates.

```text
task_key=117 scoreinfo_index=26 attempt_index=104
  prealign_score = 110
  CPU score = 68
  gap_open=12:
    GASAL2 score = 138
    shadow emits threshold
    legacy emits last_nonzero
  gap_open=16:
    GASAL2 score = 104
    below the prealign threshold
```

This is a segmented score/threshold mismatch. Aligning GASAL2 gap open with CPU
SSW removes this specific false threshold hit, but it does not make the current
selector equivalent.

```text
NEAT1 first1
  gap_open=12:
    triplex_mismatches = 0
    missing_triplexes = 0
    extra_triplexes = 0
    cpu_align_attempts = 718
    realpath_reference_align_attempts = 2008

  gap_open=16:
    triplex_mismatches = 12
    missing_triplexes = 1
    extra_triplexes = 15
```

Gap-open alignment is a diagnostic variable, not a default fix. The parameter
change trades one failure mode for another.

## Decision

Do not promote GASAL2 endpoint, terminal, segmented max-score, or gap-open 16
as authority.

```text
current emission-only consumer:
  endpoint/terminal authority: no-go
  segmented threshold authority: no-go
  gap_open=16 default: no-go
```

Allowed continuation:

```text
full-query-compatible score/end/tie-policy design
CPU-authority validation that still reduces enough total work
```

Forbidden:

```text
do not use GASAL2 endpoint as terminal authority
do not use segmented max-score as safe accept/reject authority
do not change GASAL2 default gap_open to 16 without a new equivalence proof
do not treat VERIFY_TERMINAL as a performance path
```
