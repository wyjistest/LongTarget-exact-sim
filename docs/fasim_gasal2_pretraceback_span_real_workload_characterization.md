# Fasim GASAL2 Pre-Traceback Span Real-Workload Characterization

This checkpoint characterizes the only #171 pre-traceback candidate bucket that
has a concrete signal:

```text
pretraceback_span_provable
```

It is telemetry-only. No real pruning is enabled, no traceback is skipped, no
output/scoring/threshold/CIGAR/traceback/sort behavior is changed, and GASAL2 is
not promoted as `aligner.Align()` authority.

## Scope

This result follows two previous milestones:

```text
#170:
  closed the traceback rejection taxonomy for the smoke workload

#171:
  split removed traceback attempts into pre-traceback and post-traceback
  eligibility classes
```

The #171 result showed that generic pre-traceback dedup is unsupported. The only
remaining narrow candidate is `pretraceback_span_provable`. CIGAR/representative/sort-dependent
removals keep traceback.

## Artifact Provenance

The characterization script checks local artifacts for #171 counters:

```text
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_*
```

Older GASAL2 speed artifacts without these counters are not used as complete
evidence. For this checkpoint the required rows were refreshed with a locally
built GASAL2-enabled Fasim binary from this branch.

Committed result table:

```text
docs/fasim_gasal2_pretraceback_span_real_workload_characterization.tsv
```

## Result Table

| workload | status | tracebacks | span candidates | span fraction | projected saved seconds | top5 clean | decision | notes |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| chr22_full_plain | complete | 6,910,419 | 896,062 | 12.97% | unknown | true | weak_go_more_characterization_needed | full lite/top5 clean; traceback timing is not split from extend |
| malat1_group32_two_contract | complete | 0 | 0 | unknown | unknown | true | no_go_span_bucket_not_material | eligibility active, but this two-contract path has no GASAL2 traceback attempts |
| neat1_attempt_consumer_control | complete | 0 | 0 | unknown | unknown | true | no_go_span_bucket_not_material | eligibility active, but this control path has no GASAL2 traceback attempts |

## Timing Caveat

Request counts alone are not wall-time savings. The result schema therefore
separates:

```text
pretraceback_span_fraction_of_traceback
projected_saved_traceback_seconds
timing_split_available
```

If traceback-specific timing is unavailable, projected saved seconds stay
`unknown` and `timing_split_available=false`.

## Correctness Gates

A row can support a future default-off span-prune shadow only if it is complete
and all gates are clean:

```text
false_prune_shadow = 0
missing_rows_shadow = 0
extra_rows_shadow = 0
full lite missing/extra = 0
full TFOsorted missing/extra = 0
top5 score/stability/nt_score = true
unknown_eligibility_attempts = 0
projected saved traceback seconds are material
```

The chr22 row satisfies the correctness gates that can be checked here:

```text
false_prune_shadow = 0
missing_rows_shadow = 0
extra_rows_shadow = 0
full lite missing/extra = 0
full TFOsorted missing/extra = 0
top5 score/stability/nt_score = true
unknown_eligibility_attempts = 0
```

It does not satisfy the timing gate because traceback-specific wall time is not
split from GASAL2 extend. Therefore request fraction must not be presented as a
wall-time saving.

The MALAT1 and NEAT1 control rows are correctness-clean but have
`tracebacks_requested=0`, so they do not provide a material span-pruning
opportunity.

## Decision

Decision: weak_go_more_characterization_needed

```text
generic pre-traceback dedup:
  unsupported by #171 and not pursued here

span-bound prefilter:
  chr22 full plain shows a real candidate bucket:
    896,062 / 6,910,419 traceback attempts = 12.97%

  MALAT1 group32 and NEAT1 attempt-consumer controls do not exercise GASAL2
  traceback attempts in these paths, so span pruning is not material there.

CIGAR/representative/sort-dependent buckets:
  keep traceback

next step:
  do not implement real pruning yet
  add traceback-specific timing or a validation shadow before any default-off
  span-prune option
```

This checkpoint does not justify adding a real span pruning option. It shows a
meaningful chr22 request-count opportunity, but the wall-time projection is
unknown until traceback timing is separated from the broader GASAL2 extend path.

## Commands

Generate or refresh the table:

```bash
WORK=.tmp/characterize_fasim_gasal2_pretraceback_span_real_workloads \
BIN=.tmp/fasim_longtarget_gasal2_direct \
GASAL2_DIR=.tmp/GASAL2 \
make characterize-fasim-gasal2-pretraceback-span-real-workloads
```

Validate the committed result:

```bash
make check-fasim-gasal2-pretraceback-span-real-workload-result
```
