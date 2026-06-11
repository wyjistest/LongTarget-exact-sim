# GASAL2 Archive-First Output Redesign

## Goal

Reduce the remaining CPU-side output cost in the GASAL2 path by making a
typed, reference-backed archive the primary fast-path output, with full
`TFOsorted` text restored only when needed.

This replaces the previous direction of trying to make a direct text-row writer
or a direct lite/archive writer look like the legacy output path. The new design
keeps the legacy row contract as the validation authority, but avoids making
full row text the runtime data model.

## Problem

The current fast GASAL2 runs have two different results that should not be
confused:

```text
Good:
  compact/block-column archives can restore full TFOsorted rows
  archive-first lite runs avoid most full alignment-string materialization
  storage is already small enough for chr-scale outputs

Still bad:
  convertMyTriplex/text-row materialization remains the dominant CPU-side path
  direct-row attempts changed large-workload row sets
  further archive-size tuning gives diminishing returns
```

The row-format archive work proved that storing less text is possible. It did
not fully solve the runtime structure, because the runtime still thinks in terms
of legacy row emission and probes.

## Non-Goals

Do not:

```text
change default output behavior
change GASAL2 scoring or traceback selection
promote GASAL2 endpoint/CIGAR/score as independent output authority
change Fasim scoring/filter/top-N/unique semantics
claim aligner.Align replacement
optimize archive size before runtime equivalence is clean
reuse the failed direct-row path as a recommended runtime
```

## Core Redesign

### 1. Typed Emitted Row

Introduce one internal row type that represents a selected, post-alignment TFO
record before any text formatting:

```text
FasimTypedTfoRecord
  target_id / target_name
  query_start
  query_len
  target_start
  target_len
  direction
  strand_code
  rule
  score
  nt
  identity_text
  stability_text
  class_code
  midpoint
  center
  tfo_gap_mask
  tts_gap_mask
  optional legacy_order_key
```

The two text score fields are stored as text, not recomputed during restore, so
float formatting stays legacy-compatible.

The gap masks are the compact representation needed to reconstruct the aligned
`TFO sequence` and `TTS sequence` from the query and target FASTA references.
The archive does not store aligned sequence strings.

### 2. Legacy-Equivalent Builder

Add a builder that creates `FasimTypedTfoRecord` from the same selected
alignment and task context currently passed into `convertMyTriplex()`.

The builder must reuse the legacy calculations for:

```text
query coordinates
target coordinates
strand/reverse/rule
score
nt
identity
tri_score
filter eligibility
```

It may avoid:

```text
full aligned TFO/TTS string materialization
CIGAR string construction
CIGAR string parsing
```

It must not independently rederive top-N boundary semantics. That was the
failure mode of the old direct-row prototype.

### 3. Shared Sort / Unique / Filter

After typed records are built, run the same logical sequence as the legacy
triplex path:

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

The first implementation can use a legacy-triplex adapter for comparators if
that is the safest way to preserve behavior. A later cleanup may replace that
adapter only after chr22 and chr1 row-set gates pass.

### 4. Archive-First Writer

Add a new archive writer that consumes `FasimTypedTfoRecord` directly:

```text
FasimTypedTfoArchiveWriter
```

The archive format should be block-column and reference-backed:

```text
header:
  magic/version
  schema id
  query reference digest
  target reference digest
  target record table
  block row limit

per-block columns:
  target_id
  query_start delta-varint
  query_len varint
  target_start delta-varint
  target_len varint
  score delta-varint
  rule varint
  nt varint
  flags byte
  identity dictionary
  stability dictionary
  tfo_gap_mask bytes
  tts_gap_mask bytes
```

For single-record H19/chr workloads this is close to the current dictionary
column archive. The difference is architectural: this writer is the runtime
output, not a probe attached to row text.

### 5. Restore-On-Demand

Add a restore tool:

```text
restore_fasim_tfo_archive.py
```

It reconstructs full `TFOsorted` rows from:

```text
typed archive
query FASTA
target FASTA
target record table
```

Restore is a validation and interoperability path. It is not required on the
fast runtime path unless the user explicitly needs full `TFOsorted` text.

### 6. Optional Direct Consumers

Once archive restore is clean, TFO-level consumers should read the typed archive
directly where possible:

```text
top-K TFO summaries
TFO overlap/difference analysis
future clustering input
```

This avoids regenerating hundreds of MB of text only to parse it again.

## Runtime Activation

Use a new default-off mode or env, separate from the old diagnostic probes:

```text
FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1
```

Supported initial shape:

```text
GASAL2 path active
TFOsorted-compatible output requested
no legacy full text output in the fast path
query/target FASTA available for restore
single-query workloads first
```

Unsupported shapes must fail closed:

```text
requested = 1
active = 0
decision = unsupported_shape
legacy output path remains authority
```

## Validation Gates

### Small Smoke

```text
target = chr22 2 Mb fixture
compare = byte

legacy full TFOsorted
archive-first output + restore

required:
  restored byte-identical
  row count equal
  archive_first_active = 1
```

### Large Workloads

Large GASAL2 runs can have byte-order nondeterminism. Use sorted row-set gates:

```text
chr22 full:
  sorted legacy-only rows = 0
  sorted archive-only rows = 0
  row count equal

chr1 full:
  sorted legacy-only rows = 0
  sorted archive-only rows = 0
  row count equal
```

Only after row-set gates pass can speed be interpreted.

### TFO Contract

If the accepted product contract is TFO-level rather than full row-level, add a
separate gate:

```text
top5 TFO sequences equal
top5 score/stability/nt summaries equal
TFO set overlap and missing/extra counts reported
```

This is not a substitute for full row equivalence unless the product scope is
explicitly narrowed.

## Metrics

Collect:

```text
archive_first_requested
archive_first_active
archive_first_decision
typed_records_built
typed_records_emitted
archive_bytes
archive_gzip_bytes
restore_wall_seconds
legacy_run_wall_seconds
archive_run_wall_seconds
legacy_convert_wall_seconds
archive_build_seconds
archive_sort_seconds
archive_filter_seconds
archive_write_seconds
legacy_only_rows
archive_only_rows
```

The performance comparison should separate:

```text
compute/runtime wall:
  archive-first run without restore

interoperability wall:
  archive-first run + restore

legacy wall:
  full TFOsorted text run
```

## Expected Benefit

The likely win comes from removing these from the fast runtime path:

```text
full aligned string materialization
per-row TFO/TTS text output
TFOsorted text write volume
restore-time-only reconstruction work
```

The win does not come from more GPU kernel work. It is a CPU data-model and
output-path redesign.

## Risks

### Row-Set Drift

Direct-row code already drifted on chr22 and chr1. The new builder must be
legacy-equivalent before it is treated as a speed path.

### Float Formatting

`identity` and `tri_score` must be stored using the same text representation as
legacy output. Restore must not reformat floats from binary values.

### Multi-Record Targets

Grouped FASTA and sharded runs need a target record table. Archive rows must
store `target_id`, not just coordinates in a flattened sequence, or restored
row identity can become ambiguous.

### Text Order

Small fixtures can require byte equality. Large workloads should use sorted
row-set equality because repeated legacy GASAL2 runs are not always byte-order
deterministic.

## Implementation Plan Outline

1. Add a failing smoke check:

```text
make check-fasim-gasal2-archive-first-output
```

2. Add `FasimTypedTfoRecord` and a typed builder.

3. Add shared sort/unique/filter over typed records, initially using legacy
comparator adapters where needed.

4. Add `FasimTypedTfoArchiveWriter`.

5. Add `restore_fasim_tfo_archive.py`.

6. Wire `FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1` default-off.

7. Validate small byte equality.

8. Characterize chr22 and chr1 sorted row-set equality.

9. Interpret speed only after equivalence is clean.

## Decision Rule

```text
If small byte equality fails:
  stop and debug typed builder / restore.

If chr22 or chr1 sorted row sets differ:
  keep as diagnostic/no-go, regardless of speed.

If row sets match but archive-first + restore is not faster:
  use archive-first only when storage is the goal.

If row sets match and archive-first runtime is faster:
  document as default-off recommended output mode for GASAL2 TFOsorted-compatible workloads.
```

## Current Recommendation

Stop tuning the existing row-format archive for size. It has already proven the
storage idea. The next useful step is a clean archive-first runtime path whose
primary artifact is typed, reference-backed, and restorable.
