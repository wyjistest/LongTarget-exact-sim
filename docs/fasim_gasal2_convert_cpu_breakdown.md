# Fasim GASAL2 Convert CPU Breakdown

This checkpoint decomposes the remaining CPU-side conversion cost after the
GASAL2 lite + column archive path.

## Scope

```text
Added telemetry only:
  gasal2_convert_wall_seconds
  gasal2_convert_selected_scan_seconds
  gasal2_convert_span_check_seconds
  gasal2_convert_triplex_seconds
  gasal2_convert_raw_triplexes_per_second

Not changed:
  output behavior
  archive format
  GASAL2 scoring or traceback
  candidate selection
  threshold/filter semantics
```

The smoke gate is:

```bash
make check-fasim-gasal2-convert-cpu-breakdown
```

It validates that the new metrics are emitted on the small chr22 2Mb fixture.

## Results

### chr22 Full Lite + Column Archive

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa

convert input alignments = 6,910,419
raw triplexes = 6,416,623
convert wall = 14.3875s
selected scan = 13.0668s
convertMyTriplex = 12.5232s
span check = 0.175621s
sort = 0.893676s
filter = 0.282227s
raw triplexes / second = 445,987
```

Share of convert wall:

```text
selected scan = 90.8%
convertMyTriplex = 87.0%
span check = 1.2%
sort = 6.2%
filter = 2.0%
```

### chr1 Full Lite + Column Archive

```text
target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa

convert input alignments = 37,949,280
raw triplexes = 35,178,647
convert wall = 79.5787s
selected scan = 72.4609s
convertMyTriplex = 69.4502s
span check = 0.967489s
sort = 4.87436s
filter = 1.44676s
raw triplexes / second = 442,061
```

Share of convert wall:

```text
selected scan = 91.1%
convertMyTriplex = 87.3%
span check = 1.2%
sort = 6.1%
filter = 1.8%
```

## Decision

The remaining CPU conversion bottleneck is not sorting, filtering, or archive
writing. It is the per-alignment `convertMyTriplex()` path, which still builds
full `triplex` rows from GASAL2 alignments before the lite/archive writer emits
a smaller representation.

The next optimization should not keep tuning the archive format. It also should
not hand-write an independent direct row path. A first direct-row prototype had
speed signal, but large workload row sets diverged from the legacy path. The
right next design is equivalence-first:

```text
1. keep legacy row semantics as authority
2. share sort / unique / top-N / filter behavior
3. introduce a converted-row record that can feed lite output and archive output
4. avoid duplicate string materialization and CIGAR string parse only after row
   equivalence is proven
```

Required gate for such a path:

```text
small fixture:
  restored TFOsorted byte-identical

chr22 / chr1 lite:
  sorted row-set equal
  legacy-only rows = 0
  new-only rows = 0
  convert wall lower than current path
```

The detailed design is:

```text
docs/superpowers/specs/2026-06-11-gasal2-equivalence-first-convert-design.md
```
