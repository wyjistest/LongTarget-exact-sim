# Fasim GASAL2 Pre-Traceback Span-Prune Shadow

This checkpoint adds a default-off shadow for a narrow question:

```text
Can a pre-traceback span certificate physically skip GASAL2 traceback work
without changing the current full lite / TFOsorted / top5 contracts?
```

It does not enable real pruning. The current full GASAL2 traceback path remains
the output authority, and the shadow output is not used for emission,
scoring, CIGAR, sorting, or TFO decisions.

## Scope

New opt-in telemetry:

```bash
FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE_SHADOW=1
```

The shadow:

```text
1. Runs the normal GASAL2 score prepass.
2. Selects the same authority traceback candidates.
3. Applies a strict score-end span certificate:
     query_end + 1 + (ref_end - target_start + 1) < cLength
4. Runs a physical filtered traceback batch for the kept candidates.
5. Leaves the authority path unchanged.
6. Reports measured filtered-batch timing and false-prune counters.
```

It does not prune:

```text
generic dedup
cigar_dependent_duplicate
cigar_dependent_span
sort_or_dominance_removed
representative selection
fixed score thresholds
```

## Key Result

Committed result:

```text
docs/fasim_gasal2_pretraceback_span_prune_shadow.tsv
```

Smoke workload:

```text
chr22 slice 10M-12M, H19 query, lite output
```

Measured shadow result:

```text
authority selected tracebacks = 175,193
shadow skipped selected       =      22
shadow kept selected          = 175,171
skipped fraction              = 0.0126%

false_prune = 0
missing_rows = 0
extra_rows = 0
full lite missing/extra = 0/0
full TFOsorted missing/extra = 0/0
top5 score/stability/nt_score clean
```

## Important Negative Finding

The broader `cutlength < cLength` predicate is not safe enough. During
implementation, that predicate produced:

```text
skipped selected = 51,701
false_prune      = 11
missing_rows     = 11
```

That result explains why #172's request-count opportunity cannot be promoted
directly into real pruning. The safe score-end certificate is correctness-clean
on the smoke workload, but it is not material there.

## Decision

Decision: research shadow only.

```text
safe strict score-end span certificate:
  correctness-clean on chr22 slice
  currently too small to justify real pruning

cutlength-only candidate:
  not safe
  do not implement as real pruning

next step:
  no default-off real span-prune option yet
  only revisit if a material workload shows a larger strict certificate bucket
```

This closes the immediate #172 follow-up as a measured weak/no-go checkpoint:
actual filtered-batch shadow works, but the safe candidate count is too small
on the tested material slice.

## Validation

```bash
make build-fasim-gasal2 FASIM_GASAL2_TARGET=$PWD/.tmp/fasim_longtarget_gasal2_direct GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2
make check-fasim-gasal2-pretraceback-span-prune-shadow-parser
make check-fasim-gasal2-pretraceback-span-prune-shadow-api
make check-fasim-gasal2-pretraceback-span-prune-shadow-smoke
python3 -m py_compile scripts/summarize_fasim_gasal2_pretraceback_span_prune_shadow.py
git diff --check
```
