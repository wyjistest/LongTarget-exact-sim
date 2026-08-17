# Fasim GASAL2 Segmented-Query H19 Control

This checkpoint is the first segmented-query round-trip control for extending
GASAL2-LongTarget beyond the current unsegmented short-query boundary.

It does not claim full-length long-lncRNA equivalence. It tests whether a query
that already fits the verified GASAL2 contract can be split into overlapping
segments, run through the same GASAL2 TFOsorted path, restored to global RNA
coordinates, merged, and reclustered without changing clustered TFO1-TFO5.

## Scope

```text
positive control: H19
target: chr22 10m-12m slice
segment length: 2048 by default
overlap: auto from unsegmented max query span plus guard
tail handling: final segment is tail-aligned to avoid a tiny terminal window
authority for this control: unsegmented GASAL2 TFOsorted
contract under test: clustered TFO1-TFO5 after global merge
```

This is a segmented-query workflow scaffold, not a runtime default and not an
unsegmented full-length KCNQ1OT1 claim.

## Pipeline

```text
unsegmented H19 GASAL2 TFOsorted
  -> derive max query span and safe overlap
  -> write overlapping query segments
  -> run each segment through GASAL2 TFOsorted
  -> restore segment-local QueryStart/QueryEnd to global RNA coordinates
  -> merge duplicate restored rows
  -> offline window-of-5 clustering
  -> compare clustered TFO1-TFO5 with unsegmented GASAL2
```

The merge step also restores `MidPoint` and `Center` when present. It does not
modify target coordinates, TFO/TTS strings, scores, stability, or Nt values.

## Run

```bash
make characterize-fasim-gasal2-segmented-query-h19-control
make check-fasim-gasal2-segmented-query-h19-control-result
```

Default artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_h19_control
```

## Decision Rule

```text
clean if:
  top5_offline_cluster_equal = true
  top5_offline_cluster_overlap = 5
  gasal2_fallbacks = 0
  length_guard_fallbacks = 0
```

Raw full-row equivalence is not required for this control. Segmentation can
produce extra lower-ranked rows or remove duplicate overlap rows. The contract
being tested here is the clustered experimental prioritization artifact.

## Current H19 Result

Artifact:

```text
.tmp/characterize_fasim_gasal2_segmented_query_h19_control
```

Result:

```text
query_len = 2812
segment_len = 2048
max_query_span = 141
overlap_guard = 32
segment_overlap = 172
segment_count = 2
actual_overlap = 1284

input_rows = 9498
output_rows = 9338
duplicate_rows = 160

gasal2_requests = 1548224
gasal2_traceback_requests = 490924
gasal2_fallbacks = 0
length_guard_fallbacks = 0

top5_offline_cluster_equal = true
top5_offline_cluster_overlap = 5

raw top5_tfo_score_equal = true
raw top5_tfo_stability_equal = true
raw top5_tfo_nt_score_equal = false
full_missing_rows = 35
full_extra_rows = 1115

decision = segmented_query_h19_control_clean
```

Interpretation:

```text
segmented-query clustered TFO1-TFO5 control:
  clean

raw TFOsorted/full-row equivalence:
  not claimed
```

The raw merged output contains additional lower-ranked rows from overlapping
segments, and the raw Nt top5 differs. The clustered TFO1-TFO5 detail rows are
byte-identical after global coordinate restoration and merge.

## Next Step

If this control is clean, the next meaningful milestone is a non-H19 segmented
pilot:

```text
KCNQ1OT1 segmented query
target = chr22 slice or chr22 full
segment_len <= 2812
global coordinate restore
overlap duplicate merge
clustered TFO1-TFO5 and shifted-grid stability checks
```

Do not write this as unsegmented KCNQ1OT1 equivalence. The correct scope is
segmented-query full-length lncRNA screening.
