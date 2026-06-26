# Fasim GASAL2 Segmented KCNQ1OT1 Coverage Ladder

This checkpoint documents the KCNQ1OT1 segmented-query coverage ladder on the
full chr22 target. It extends the bounded 4-segment pilot to 8 segments per
shifted grid while keeping the same target, segment length, overlap, and grid
shift policy.

## Scope

```text
query: KCNQ1OT1 full transcript FASTA
query_len: 91667
target: chr22 full, 50818468 bp
segment_len: 2048
segment_overlap: 512
grid shifts: 0 and 256
comparison: clustered TFO1-TFO5 equality across shifted grids
```

This is a coverage ladder, not a full-transcript validation. `max_segments=4`
and `max_segments=8` are completed. Full query coverage is extrapolated only.

## Results

```text
max_segments | total_segments | common_query_interval | gasal2_requests | traceback_requests | wall_sum_seconds | artifact_MB | grid_stable
4            | 8              | 41728-48128           | 151666259       | 62807605           | 676.332789       | 669         | yes
8            | 16             | 38656-51200           | 303560481       | 128054052          | 1249.592386      | 1004        | yes
full est.    | ~121           | 0-91667               | ~2.30B          | ~0.97B             | ~2.62h           | ~7.4GB      | not run
```

The full estimate uses the `max_segments=8` per-segment rate:

```text
estimated_full_total_segments = 121
wall_seconds_per_segment = 1249.592386 / 16 = 78.099524
estimated_full_wall_sum_seconds = 9450.04
estimated_full_wall_sum_hours = 2.625
estimated_full_gasal2_requests = 303560481 / 16 * 121 = 2.30B
estimated_full_traceback_requests = 128054052 / 16 * 121 = 0.97B
estimated_full_artifact_MB = 1004 / 16 * 121 = 7593 MB
```

## Completed Max8 Result

Artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full_max8
```

Result:

```text
grid_shift_0_segment_count = 8
grid_shift_0_range_start = 38400
grid_shift_0_range_end = 51200

grid_shift_256_segment_count = 8
grid_shift_256_range_start = 38656
grid_shift_256_range_end = 51456

common_query_start = 38656
common_query_end = 51200

shift 0:
  input_rows = 1371366
  output_rows = 952790
  duplicate_rows = 412298
  filtered_rows = 6278
  wall_sum_seconds = 620.756822

shift 256:
  input_rows = 1384197
  output_rows = 978114
  duplicate_rows = 404106
  filtered_rows = 1977
  wall_sum_seconds = 628.835564

both grids:
  wall_sum_seconds = 1249.592386
  gasal2_requests = 303560481
  gasal2_traceback_requests = 128054052
  gasal2_fallbacks = 0
  length_guard_fallbacks = 0
  artifact_size = 1004 MB

top5_offline_cluster_equal = true
top5_offline_cluster_overlap = 5
decision = segmented_query_kcnq1ot1_pilot_grid_stable
```

## Interpretation

```text
KCNQ1OT1 bounded segmented-query grid stability on chr22 full:
  strong positive through max_segments=8

full KCNQ1OT1 transcript coverage on chr22 full:
  not run

full KCNQ1OT1 x hg38:
  not claimed

unsegmented full-length KCNQ1OT1 equivalence:
  not claimed
```

The max8 run strengthens the segmented-query path, but it also makes the
resource curve explicit. Continuing directly to full query coverage would be
feasible but expensive and would produce multi-GB artifacts. The next useful
step is output reduction or offline per-segment topK sensitivity before running
larger coverage levels.
