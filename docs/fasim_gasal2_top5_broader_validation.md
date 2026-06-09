# Fasim GASAL2 Top5 Broader Validation

This is the top5 broader workload validation checkpoint for the current
scoreInfo/preAlign GASAL2 line.

It validates the evidence that exists today and keeps the remaining gap explicit.
It is not a broad production default decision.
It is part of the top5-only product-readiness boundary, not completion of the
full objective.

## Preset

The checked preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The contract remains top5-only.

## Short-Query Positive Set

The current short-query positive set is:

```text
small chr22 slice
chr21+chr22
MEG3 grouped
```

Each positive aggregate must report:

```text
top5_artifact_go
top5 score/stability/nt_score clean
active_path_runs = runs
positive_gasal2_request_runs = runs
positive_exact_scoreinfo_task_runs = runs
fallback/overflow = 0
```

Recorded evidence:

```text
small chr22 slice:
  decision = top5_artifact_go
  GASAL2/exact-scoreInfo active path clean

chr21+chr22:
  decision = top5_artifact_go
  speedup vs CPU worker wall sum = 40.119136x
  GASAL2/exact-scoreInfo active path clean

MEG3 grouped:
  decision = top5_artifact_go
  speedup vs CPU worker wall sum = 1.939275x
  complete-record grouping path clean
```

## Long-Query Guard Set

The current long-query guard set is:

```text
MALAT1 first8
NEAT1 first64
```

These rows are important because they prevent a false broad claim:

```text
query_len > GASAL2_MAX_QUERY_LEN
scoreinfo_gasal2_active = 0
CPU fallback top5 clean
not GASAL2-active evidence
```

They are correctness-safe CPU fallback examples, not evidence that the preset
has a MALAT1/NEAT1 GPU scoreInfo path.

## Broader Recommendation Status

The current broader recommendation status is:

```text
short-query/H19 top5:
  go as an opt-in product-readiness candidate

many-record tiny-region workload:
  go with complete-record grouping when the grouped top5 gate is clean

MALAT1/NEAT1 long-query workload:
  no real GASAL2 path

default production:
  not broad production default

full objective:
  full objective remains open
```

This checkpoint does not claim universal scoreInfo/preAlign replacement. It only
turns the current evidence into a broader-validation table for the scoped top5
artifact contract.

## Gate

Focused gate:

```bash
make check-fasim-gasal2-top5-broader-validation
```

Product-readiness gate:

```bash
make check-fasim-gasal2-top5-product-readiness
```

GASAL2 top5 recommended runtime gate:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

Top5 scoped completion candidate gate:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

The recommended-runtime gate documents the default-off short-query/H19 command
surface that follows from this validation table. The top5 scoped completion
candidate records the conditional top5-only product boundary. The full objective
remains open.

Composed gate:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```
