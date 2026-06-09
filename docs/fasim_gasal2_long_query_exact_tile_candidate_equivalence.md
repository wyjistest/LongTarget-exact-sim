# Fasim GASAL2 Long-Query Exact-Tile Candidate Equivalence

This checkpoint records the first candidate-equivalence run for the long-query
exact-tile shadow architecture.

## Decision

```text
decision = exact_tile_candidate_equivalence_no_go
```

The checked shape is diagnostic only:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_CANDIDATE_EQUIVALENCE=1
```

CPU fallback remains authority. The candidate-equivalence shadow does not use
tile candidates for output, digest, endpoint, CIGAR, traceback, or candidate
state.

## Result

MALAT1 first8:

```text
active = 1
query_len = 8708
tile_len = 2812
tiles = 4
tile_descriptors = 4
tile_max_query_len = 2812
tile_descriptor_digest = 16919590609729549896
cpu_oracle_candidates = 31272
tile_candidates = 31591
candidate_missing = 1720
candidate_extra = 2039
fallback = 0
output digest unchanged
```

The clean candidate-equivalence gate intentionally fails for this shape:

```bash
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence
```

Observed failure:

```text
candidate equivalence mismatch: missing=1720 extra=2039
```

## Boundary

This proves that non-overlap exact tiling is not candidate-equivalent for the
MALAT1 first8 long-query sample. The mismatch appears before any output use, so
the CPU fallback output remains unchanged and correctness-safe.

do not promote this exact-tile shape to a real path.

Do not claim that the current exact-tile descriptor architecture is a
long-query scoreInfo/preAlign replacement.

Any future long-query architecture needs a different candidate-equivalence
strategy, such as overlap with a proven boundary policy or another exact DP
stitching design, before performance characterization is meaningful.

## Gate

The no-go result checkpoint is:

```bash
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result
```
