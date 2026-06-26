# Fasim GASAL2 Segmented KCNQ1OT1 Target-Scope Expansion

This checkpoint expands the bounded KCNQ1OT1 segmented-query pilot from the
2 Mb chr22 slice to the full chr22 target. It keeps the query-region scope fixed
so that only the target scope changes.

## Scope

```text
query: KCNQ1OT1 full transcript FASTA
query_len: 91667
target: chr22 full, 50818468 bp
segment_len: 2048
segment_overlap: 512
grid shifts: 0 and 256
max_segments: 4 per grid
common query interval: 41728-48128
claim: shifted-grid clustered TFO1-TFO5 stability on chr22 full
```

This is still not full-length KCNQ1OT1 genome-wide validation. It keeps a
bounded query region and expands only the DNA target from a 2 Mb slice to chr22.

## Run

```bash
WORK=.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full \
TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
KCNQ1OT1_FASTA=.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa \
SEGMENT_LEN=2048 \
SEGMENT_OVERLAP=512 \
GRID_SHIFTS='0 256' \
MAX_SEGMENTS=4 \
bash scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh
```

Check:

```bash
make check-fasim-gasal2-segmented-query-kcnq1ot1-target-scope-result
```

Artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full
```

## Result

```text
grid_shift_0_segment_count = 4
grid_shift_0_range_start = 41472
grid_shift_0_range_end = 48128

grid_shift_256_segment_count = 4
grid_shift_256_range_start = 41728
grid_shift_256_range_end = 48384

common_query_start = 41728
common_query_end = 48128

shift 0:
  input_rows = 932168
  output_rows = 615631
  duplicate_rows = 300834
  filtered_rows = 15703

shift 256:
  input_rows = 949097
  output_rows = 640993
  duplicate_rows = 306477
  filtered_rows = 1627

gasal2_requests = 151666259
gasal2_traceback_requests = 62807605
gasal2_fallbacks = 0
length_guard_fallbacks = 0

top5_offline_cluster_equal = true
top5_offline_cluster_overlap = 5

decision = segmented_query_kcnq1ot1_pilot_grid_stable
```

The clustered TFO1-TFO5 detail rows are identical between the two shifted grids.

## Interpretation

```text
KCNQ1OT1 bounded segmented query x chr22 full:
  grid-stable clustered TFO1-TFO5

full KCNQ1OT1 x hg38:
  not yet claimed

unsegmented full-length KCNQ1OT1 equivalence:
  not claimed
```

This strengthens the segmented-query line by showing that the shifted-grid
stability observed on the 2 Mb slice is not limited to that target slice.
