# Coordinate Mapping

## Canonical basis

Raw coordinate fields are retained before normalization. Query coordinates are
1-based inclusive and normalize to
`[raw_QueryStart-1, raw_QueryEnd)`. Target and genome coordinates normalize to
0-based half-open intervals on the forward target FASTA.

The normative eight-row matrix is `coordinate_mapping_table.tsv`. Its SHA-256
is bound by `paper/biological_topk/contract_spec.json`. Four `Direction=R`
combinations are reachable. The four `Direction=L` combinations are marked
`unreachable_by_current_runtime`; no formula is guessed for them.

## Target formulas

For `ParaPlus` and `AntiMinus`, raw target fields are 1-based inclusive:

```text
target = [raw_StartInSeq - 1, raw_EndInSeq)
```

For `ParaMinus` and `AntiPlus`, raw target fields are 0-based inclusive:

```text
target = [raw_StartInSeq, raw_EndInSeq + 1)
```

For every reachable row:

```text
genome_start0 = target_region_start0 + target_start0
genome_end0   = target_region_start0 + target_end0
```

The TTS reconstruction applies, respectively, forward, reverse-complement,
reverse, or complement orientation for `ParaPlus`, `ParaMinus`, `AntiPlus`, or
`AntiMinus`. Generic sequence normalization never changes orientation.

## Evidence and failure behavior

`paper/biological_topk/coordinate_golden_fixtures.tsv` covers every reachable
Strand/Direction combination, first and last target bases, single- and
multi-base intervals, reverse/complement reconstruction, genome offsets, and
frozen hq10/hq11 rows. Any unsupported label, unreachable direction, invalid
raw interval, out-of-bounds normalized interval, or TTS reconstruction mismatch
fails closed before matching.

Source authority is `fasim/fastsim.h:3701-3722` and
`fasim/Fasim-LongTarget.cpp:27757-27851,29323-29373`.
