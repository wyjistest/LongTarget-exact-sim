# Fasim GASAL2 segmented archive-first merge

## Status

Phase 1 is `pass` for the explicit segmented-query runner.

The new path is default-off. It does not change Fasim scoring, traceback,
candidate selection, sorting, clustering, or the normal unsegmented output
path.

## Scope

The segmented KCNQ1OT1 characterization runner now emits one archive per RNA
segment instead of a complete per-segment `TFOsorted` text file:

```text
FASIM_OUTPUT_MODE=tfosorted
FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1
```

Each segment must produce exactly one non-empty
`*.archive-first.tfoa`. Zero or multiple archives fail closed, as does any
complete `*-TFOsorted` text output from the archive-first run. Archives are
retained by default. `CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE=1` removes them only
after all grid merges have succeeded.

The typed manifest is:

```text
segment_id
global_start
global_end
artifact_kind
artifact_path
query_fasta
query_fasta_sha256
target_fasta
target_fasta_sha256
```

`artifact_kind` is `archive_first_tfoa` for this runner. The merge CLI still
accepts the legacy `tfosorted` manifest field and defaults to the in-memory
dedup backend, preserving existing text callers for one compatibility cycle.

## Decoder contract

`scripts/fasim_tfo_archive.py` is the single implementation of the
`FATFOC1` version 2 schema. Both the standalone restore CLI and segmented
merge import it. The decoder:

- validates magic, version, the 13-column payload shape, terminator, masks,
  flags, and coordinate bounds;
- verifies raw SHA-256 digests for both query and target FASTA references;
- decodes one archive block at a time;
- rejects declared blocks above 1,000,000 rows or 256 MiB before decoding;
- requires one query and one target FASTA record because the archive itself
  does not identify a record in a multi-record reference;
- restores `Chr`, `StartInGenome`, and `EndInGenome` from target headers using
  the same `species|chromosome|start-end` convention as Fasim.

The last item fixes the Phase 0 compound-header failure. The
`testDNA.fa` fixture now restores all 144 rows byte-for-byte, including
`chr11` and the absolute target offset.

## Bounded exact merge

The merge writes a `.partial` output as rows arrive and atomically publishes
the final output only after successful completion. It no longer stores a
complete output-row list.

The production segmented runner selects:

```text
--dedup-backend sqlite
--dedup-db <grid-workdir>/merge-dedup.sqlite
```

The SQLite primary key is the complete canonical TSV row as a BLOB. No short
or probabilistic hash is used. `INSERT OR IGNORE` therefore preserves the
existing exact first-seen-row-wins order. Transactions commit every 10,000
attempted rows by default. A failed merge retains its partial output and
database for diagnosis; a successful merge removes the database unless
`--keep-dedup-db` is explicit.

## Gate evidence

Command:

```bash
make check-fasim-gasal2-segmented-archive-first
```

Artifact:

```text
.tmp/check_fasim_gasal2_segmented_archive_first/summary.txt
```

Latest hard-gate result:

```text
legacy_text_vs_archive_merged_equal=1
missing_rows=0
extra_rows=0
small_fixture_byte_identical=1
compound_header_byte_identical=1
per_segment_full_text_emitted=0
bounded_memory_backend_active=1
bounded_backend_exact=1
fallbacks=0
length_guard_fallbacks=0
existing_default_path_unchanged=1
peak_rss_materially_below_legacy=1
phase1_decision=pass
```

The text/archive comparison applies the same coordinate restore, filter, and
exact-dedup merge semantics to both inputs. Both consume 8,291 input rows,
remove the same 33 exact duplicates, and emit the same 8,258 rows in the same
byte order. Separately, the raw archive restore remains byte-identical to the
raw 8,291-row legacy text, so dedup is not being misreported as archive loss.

## Storage and memory

The real H19 by chr22 2 Mb fixture produced:

```text
legacy_text_bytes=1836889
archive_bytes=321411
archive/text ratio=0.174976
storage reduction=82.50%
```

The 150,000-row synthetic control produced byte-identical memory and SQLite
outputs:

```text
memory_peak_rss_kb=44012
sqlite_peak_rss_kb=29212
peak_rss_reduction_kb=14800
peak_rss_reduction_fraction=0.336272
memory_process_wall_seconds=1.227274
sqlite_process_wall_seconds=1.723749
```

The RSS comparison is against the merge's exact in-memory set backend. It is
a conservative control relative to the old implementation, which also held
the complete output-row list. SQLite costs about 0.50 seconds in this
synthetic run but lowers peak RSS by 33.6%; Phase 1 is a storage/memory phase
and does not require compute speedup.

Measured wall components for the real 2 Mb fixture were:

```text
legacy text run=3.383438 s
archive-first run=2.524499 s
standalone full restore=0.280155 s
archive run plus restore=2.804654 s
typed SQLite merge=0.281531 s
  archive decode/restore portion=0.220705 s
```

Restore time is included rather than omitted.

## Segmented runtime smoke

The runtime smoke uses four actual GASAL2 archive-first segment runs across
two shifted grids over H19 and the 4,366-bp compound-header DNA fixture. It is
small enough for an automated gate while exercising the real binary:

```text
artifact_kind_counts=archive_first_tfoa:4
archive_input_bytes=3447
text_input_bytes=0
input_rows=64
output_rows=58
dedup_backend=sqlite
pipeline_wall_seconds=2.223548
per_segment_full_text_emitted=0
segment_archives_retained=4
gasal2_fallbacks=0
length_guard_fallbacks=0
```

This smoke is not a shifted-grid biological equivalence gate; its tiny target
does not produce equal offline clustered top five candidates. Phase 1 only
uses it to validate artifact and merge lifecycle behavior.

## Limits

This phase does not claim:

- segmentation completeness or core/halo ownership;
- clustered TFO1-TFO5 equivalence for a new workload;
- full KCNQ1OT1 transcript coverage;
- full hg38 execution;
- multi-record archive reference recovery;
- a default-on runtime change.

Those claims remain gated by later phases in `goal.md`. No multi-hour
KCNQ1OT1 run was performed for Phase 1.

## Regression

The complete Phase 0 gate remains clean after this change:

```bash
make check-fasim-gasal2-long-query-phase0
```

It finishes with:

```text
Fasim GASAL2 long-query Phase 0 baseline OK
```
