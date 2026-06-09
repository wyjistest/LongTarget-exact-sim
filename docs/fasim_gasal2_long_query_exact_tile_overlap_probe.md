# Fasim GASAL2 Long-Query Exact-Tile Overlap Probe

This checkpoint records whether overlap rescues the long-query exact-tile
candidate-equivalence shape after the non-overlap probe failed.

## Decision

```text
decision = exact_tile_overlap_candidate_equivalence_no_go
```

The checked path is diagnostic only:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_CANDIDATE_EQUIVALENCE=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_OVERLAP=<N>
```

CPU fallback remains authority. The overlap probe does not use tile candidates
for output, digest, endpoint, CIGAR, traceback, or candidate state. The output
digest remains unchanged in the checked runs.

## Results

MALAT1 first8, half-tile overlap:

```text
overlap = 1406
query_len = 8708
tile_len = 2812
tiles = 6
tile_descriptor_digest = 8144326404929707858
cpu_oracle_candidates = 31272
tile_candidates = 33862
candidate_missing = 1
candidate_extra = 2591
position_missing = 1
position_extra = 2397
position_score_mismatches = 0
fallback = 0
output digest unchanged
```

MALAT1 first8, larger overlap:

```text
overlap = 2048
query_len = 8708
tile_len = 2812
tiles = 9
tile_descriptor_digest = 11322515831205853531
cpu_oracle_candidates = 31272
tile_candidates = 34232
candidate_missing = 1
candidate_extra = 2961
position_missing = 1
position_extra = 2644
position_score_mismatches = 0
fallback = 0
output digest unchanged
```

## Boundary

Overlap substantially reduces missing candidates relative to non-overlap exact
tiling, but it does not produce exact candidate equivalence. Larger overlap
reduces missing candidates but increases extra candidates.

larger overlap reduces missing candidates but increases extra candidates.

position_score_mismatches = 0 means this is not a score remapping problem.
The overlap no-go is position-level: tile-local DP creates positions absent from
full-query CPU oracle.

do not promote overlap exact tiling to a real path.

Any future long-query path needs a stronger boundary/stitching design. A simple
union of tile-local scoreInfo candidates is not enough.

## Gates

The expensive diagnostic probe is:

```bash
make check-fasim-gasal2-long-query-exact-tile-overlap-probe
```

The lightweight result checkpoint is:

```bash
make check-fasim-gasal2-long-query-exact-tile-overlap-result
```
