# Fasim GASAL2 Segmented-Query KCNQ1OT1 Pilot

This checkpoint is a bounded KCNQ1OT1 segmented-query pilot. It is deliberately
not a full-genome or full-length equivalence claim.

## Scope

```text
query: KCNQ1OT1 full transcript FASTA
target: chr22 10m-12m slice by default
segment_len: 2048
segment_overlap: 512
grid shifts: 0 and 256
max_segments: 4 per grid by default
comparison: clustered TFO1-TFO5 stability between shifted segment grids
```

Because full-length unsegmented KCNQ1OT1 exceeds the verified GASAL2 query
contract, this pilot has no unsegmented KCNQ1OT1 authority. It tests a narrower
property:

```text
Given bounded overlapping KCNQ1OT1 query segments,
after restoring global RNA coordinates and filtering to common grid coverage,
do shifted grids produce the same clustered TFO1-TFO5?
```

## Run

```bash
make characterize-fasim-gasal2-segmented-query-kcnq1ot1-pilot
make check-fasim-gasal2-segmented-query-kcnq1ot1-pilot-result
```

Default artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot
```

`KCNQ1OT1_FASTA` is external to the repository and defaults to:

```text
.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa
```

## Decision Rule

```text
clean if:
  top5_offline_cluster_equal = true
  top5_offline_cluster_overlap = 5
  gasal2_fallbacks = 0
  length_guard_fallbacks = 0
```

This is a grid-stability pilot. It does not establish full KCNQ1OT1
segmented-query genome-wide validity by itself.

## Current Bounded Result

Artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot
```

Result:

```text
query_len = 91667
segment_len = 2048
segment_overlap = 512
grid_shifts = 0 256
max_segments = 4
common_query_start = 41728
common_query_end = 48128

shift 0:
  segments = 4
  input_rows = 20513
  output_rows = 13135
  duplicate_rows = 6957
  filtered_rows = 421

shift 256:
  segments = 4
  input_rows = 20845
  output_rows = 13761
  duplicate_rows = 7064
  filtered_rows = 20

gasal2_requests = 3959478
gasal2_traceback_requests = 1639917
gasal2_fallbacks = 0
length_guard_fallbacks = 0

top5_offline_cluster_equal = true
top5_offline_cluster_overlap = 5

decision = segmented_query_kcnq1ot1_pilot_grid_stable
```

Interpretation:

```text
bounded shifted-grid stability:
  clean

full KCNQ1OT1 genome-wide segmented workflow:
  not yet claimed
```

This result is the first positive signal that full-length KCNQ1OT1 can be
handled as a segmented-query screening workflow while keeping each individual
GASAL2 query segment inside the verified short-query contract.
