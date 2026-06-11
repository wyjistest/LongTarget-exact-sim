# GASAL2 Equivalence-First Convert Design

## Goal

Reduce CPU-side conversion cost in the GASAL2 lite + column archive path without
changing Fasim output semantics.

The design target is not a new aligner path and not a new GASAL2 scoring path.
It is a replacement design for the failed direct lite/archive conversion
prototype:

```text
Keep:
  legacy row semantics
  legacy sort / unique / top-N / filter semantics
  CPU/GASAL2 traceback output authority

Change:
  avoid duplicate string materialization and CIGAR string parse where safe
```

## Context

The current GASAL2 lite + dictionary column archive path removed most full text
materialization cost, but CPU conversion is still significant:

```text
chr22 full:
  convert wall ~= 14.4s
  convertMyTriplex ~= 12.5s

chr1 full:
  convert wall ~= 79.6s
  convertMyTriplex ~= 69.5s
```

The previous direct conversion prototype was not acceptable. It was clean on a
small chr22 2 Mb fixture, but large workloads changed the restored row set:

```text
chr22 full direct-row prototype:
  speed signal
  row-set mismatch

chr1 full direct-row prototype:
  speed signal
  row-set mismatch

sidecar + legacy-field diagnostic variant:
  small fixture clean
  large workload still not clean
  no speed benefit
```

Repeated legacy chr22 runs also showed byte-order non-determinism with matching
sorted row sets. Therefore large-workload validation must distinguish row-order
differences from row-set differences.

## Non-Goals

Do not:

```text
change default behavior
change GASAL2 scoring, traceback, or selected-alignment logic
change candidate selection
change sort / unique / top-N / filter semantics
change final output semantics
promote GPU endpoint, CIGAR, score, or digest authority
reuse the direct-row prototype as a runtime path
claim performance before row-set equivalence
```

The existing `FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT` work should remain a
diagnostic/no-go checkpoint or be retired. A future implementation should use a
new, clearly named default-off env after it passes the equivalence gates.

## Recommended Architecture

### 1. Single Converted Row Record

Introduce one internal converted-row representation:

```text
FasimConvertedTriplexRecord
  triplex_fields:
    stari, endi, starj, endj
    strand, reverse, rule
    score, nt, identity, tri_score
    chr, genomestart, genomeend
    motif, middle, center, neartriplex

  optional payloads:
    alignment strings for full output
    typed CIGAR ops
    precomputed query/target gap masks
```

This record is the only source for lite row text and archive rows. Direct
archive code must not independently recompute row coordinates, strand labels,
identity, stability, or `nt`.

### 2. Legacy-Equivalent Builder

Refactor `convertMyTriplex()` into a builder plus wrapper:

```text
buildConvertedTriplexRecord(alignment, task context, materialization policy)
  -> zero or one FasimConvertedTriplexRecord

convertMyTriplex(...)
  calls buildConvertedTriplexRecord(...)
  adapts the record back to legacy triplex
```

The builder must reuse the exact existing logic for:

```text
identity
tri_score
nt
query coordinates
target coordinates
strand/reverse/rule
ntMin/ntMax behavior
```

This avoids the previous failure mode where direct-row code reimplemented
legacy row semantics and drifted at top-N boundaries.

### 3. Shared Sort / Unique / Filter

Extract one shared helper for converted rows:

```text
fasim_sort_unique_filter_converted_rows(rows, paraList)
```

It must be behaviorally equivalent to the current legacy sequence:

```text
sort compMyTriplexMultiple
unique sameMyTriplex
sort compMyTriplexMultiple2
unique sameMyTriplex
sort compMyTriplexSingle
keep first N
filter identity >= minIdentity
filter tri_score >= minStability
filter nt >= ntMin
```

The helper should compare converted rows using the same fields as legacy
`triplex`. Do not introduce a new comparator unless it is proven to produce the
same row set on chr22 and chr1.

### 4. Materialization Policy

Use an explicit policy instead of ad hoc booleans:

```text
FasimConvertMaterializationPolicy
  materialize_alignment_strings
  materialize_cigar_probe_string
  materialize_typed_cigar
  materialize_gap_masks
```

Initial policies:

```text
legacy full output:
  alignment strings = yes
  cigar_probe string = current behavior
  typed CIGAR = no
  gap masks = no

legacy lite + column archive:
  alignment strings = no
  cigar_probe string = yes
  typed CIGAR = no
  gap masks = no

new equivalence-first lite + column archive:
  alignment strings = no
  cigar_probe string = no
  typed CIGAR = yes
  gap masks = yes
```

The new path is only allowed after the converted-row builder and shared
sort/filter helper are used by both legacy and new modes or are proven
equivalent by the gates below.

### 5. Archive Writer

Add a column archive writer entry point that consumes
`FasimConvertedTriplexRecord`:

```text
write_converted_row(record)
```

It should write the same archive format as the current dictionary column
archive. It may use typed CIGAR ops or precomputed masks to avoid:

```text
triplex.cigar_probe string construction
fasim_parse_cigar_probe()
recomputing masks from strings
```

It must still restore to the same TFOsorted row text.

## Data Flow

```text
GASAL2/CPU traceback selected alignments
  -> buildConvertedTriplexRecord()
  -> shared sort / unique / top-N / filter
  -> lite writer from converted record
  -> column archive writer from converted record
  -> restore archive
  -> compare to legacy output
```

No GPU result becomes output authority in this design. The only changed area is
CPU conversion and archive payload construction.

## Validation Gates

### Required Smoke Gate

```text
small chr22 2 Mb:
  legacy restored TFOsorted byte-identical to new restored TFOsorted
  archive row count equal
  direct/equivalence path active = 1
```

### Required Large Gates

Because legacy chr22 is not byte-order deterministic, large gates compare sorted
row sets:

```text
chr22 full:
  sorted legacy-only rows = 0
  sorted new-only rows = 0
  row count equal

chr1 full:
  sorted legacy-only rows = 0
  sorted new-only rows = 0
  row count equal
```

Only after these pass may performance be interpreted.

### Performance Metrics

Collect:

```text
run_wall_seconds
convert_wall_seconds
selected_scan_seconds
triplex_builder_seconds
sort_seconds
filter_seconds
output_write_seconds
restore_wall_seconds
archive_bytes
archive_gzip_bytes
rows
legacy_only_rows
new_only_rows
```

Success is:

```text
equivalence first:
  all row-set gates pass

performance second:
  convert wall lower than legacy on chr22 and chr1
  run wall not worse than legacy
```

If equivalence fails, the path remains diagnostic/no-go regardless of speed.

## Test Strategy

Add a new default-off check target after implementation:

```text
make check-fasim-gasal2-equivalence-first-convert
```

It should run the small fixture in byte comparison mode.

Add characterization commands or scripts for large workloads:

```text
COMPARE_MODE=set
TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa

COMPARE_MODE=set
TARGET=.tmp/fasim_gasal2_chr1_full_input/chr1.fa
```

Large characterization can remain outside the default quick check because chr1
is long-running, but it is required before any recommendation.

## Failure Handling

When row-set comparison fails, the checker must emit:

```text
legacy_only_rows
new_only_rows
first legacy-only row
first new-only row
work directory containing full diff files
```

The runtime path must fail closed:

```text
unset env:
  legacy path only

env set but unsupported shape:
  active = 0
  decision = unsupported
  legacy path only

env set and supported:
  active = 1
  diagnostic output only until gates pass
```

## Implementation Boundaries

The first implementation PR should do only this:

```text
1. Add converted-row record and materialization policy.
2. Refactor convertMyTriplex through the converted-row builder.
3. Add shared sort / unique / filter helper.
4. Add converted-row column archive writer.
5. Add small fixture byte-equivalence check.
6. Document chr22/chr1 set-equivalence characterization.
```

Do not combine this with:

```text
GASAL2 score changes
GPU endpoint/CIGAR work
full aligner replacement
archive format redesign
automatic runtime policy
sharded runner policy changes
```

## Decision Rule

```text
If small fixture passes but chr22 or chr1 row-set differs:
  stop and debug converted-row equivalence

If row-set gates pass but speed does not improve:
  keep as refactor only; do not recommend runtime

If row-set gates pass and convert/run wall improve:
  next PR may document a default-off recommended runtime for lite + column archive only
```

This design is complete when the spec is reviewed. Implementation planning and
code changes remain separate steps.
