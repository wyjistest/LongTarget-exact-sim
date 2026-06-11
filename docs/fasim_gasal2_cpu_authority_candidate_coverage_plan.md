# Fasim GASAL2 CPU-Authority Candidate Coverage Plan

This is the next broad-path probe toward the active objective. It is not a
runtime path and not a completion claim.

The current emission-only selector is blocked by two independent failures:

```text
task49:
  score matches, endpoint/terminal differs

task117:
  segmented GASAL2 score crosses threshold while CPU aligner score does not
```

So the next viable GASAL2 path cannot use GASAL2 as output authority. CPU
`aligner.Align()` remains the only authority. GASAL2 may only propose candidate
attempts, and CPU must validate the selected candidate stream before any output
or digest claim.

## Probe

Add a default-off shadow that measures candidate coverage:

```text
CPU authority:
  build the legacy scoreInfo attempt stream
  run legacy CPU aligner.Align() state machine
  record the legacy selected attempt for each scoreInfo

GASAL2 candidate reducer:
  score the same attempts
  include threshold candidates
  include fallback candidates
  include last_nonzero candidates
  deduplicate attempts by scoreinfo/start/cutlength
  optionally apply score_margin sweep

coverage check:
  legacy selected attempt is present in the GASAL2 candidate set
```

Required telemetry:

```text
scoreinfos
attempts
gasal2_candidate_attempts
legacy_selected_attempts
covered_selected_attempts
false_negative_scoreinfos
cpu_align_attempts
realpath_reference_align_attempts
realpath_reference_seconds
score_seconds
select_seconds
cpu_align_seconds
convert_seconds
total_seconds
triplex_mismatches
missing_triplexes
extra_triplexes
first_false_negative_task
first_false_negative_scoreinfo
first_false_negative_reason
```

Hard gates:

```text
false_negative_scoreinfos = 0
triplex_mismatches = 0
missing_triplexes = 0
extra_triplexes = 0
cpu_align_attempts < realpath_reference_align_attempts
total_seconds < realpath_reference_seconds
```

## Sweep

The first characterization should run a score_margin sweep:

```text
score_margin = 0 / 16 / 32 / 64
```

Each row should record whether the candidate reducer includes:

```text
threshold candidates
fallback candidates
last_nonzero candidates
```

The initial workloads are:

```text
NEAT1 first1
NEAT1 first64
```

Focused debug rows must include the known divergence cases:

```text
task49
task117
```

## Constraints

```text
Do not use GASAL2 endpoint as terminal authority.
Do not use segmented score as accept/reject authority without CPU validation.
Do not use GASAL2 CIGAR or traceback.
Do not change production output.
Do not change default behavior.
Do not mark the full goal complete from this probe.
```

## Decision

```text
If false_negative_scoreinfos is nonzero, stop this candidate reducer.
If coverage is clean but CPU align attempts are not reduced, stop this candidate reducer.
If coverage is clean but total_seconds does not beat realpath_reference_seconds, keep it diagnostic only.
If coverage and speed are clean, next PR may implement a default-off shadow.
```

This probe is useful because it tests the only currently plausible broad GASAL2
shape: GPU/GASAL2 narrows the candidate set, while CPU `aligner.Align()` remains
the semantic authority.
