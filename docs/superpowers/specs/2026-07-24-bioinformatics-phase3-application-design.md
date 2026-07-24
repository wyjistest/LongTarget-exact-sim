# Bioinformatics Phase 3 Application Design

## Purpose

Phase 3 must test the user-facing GASAL2-LongTarget workflow on a real,
preregistered lncRNA-promoter screening panel. It must measure the complete
verified-or-authority safe pipeline selected in Phase 2, rather than using the
GPU-only candidate as a substitute for user-safe performance.

This design separates Phase 3 into three committed checkpoints:

1. build and freeze the biological input panel;
2. build and freeze the execution runner and exact attempt plan;
3. run the excluded pilot, execute the immutable formal plan, and analyze the
   retained evidence.

No application backend, pilot, or benchmark may run before checkpoints 1 and 2
are committed in that order.

## Fixed Scope

- Assembly: GRCh38.
- Annotation: GENCODE v49.
- Query source: `gencode.v49.lncRNA_transcripts.fa.gz`.
- Annotation source: `gencode.v49.annotation.gtf.gz`.
- Target sequence source: UCSC GRCh38 `chr21.fa.gz` and `chr22.fa.gz`.
- Query count: exactly 50.
- Target policy: every chr21/chr22 protein-coding gene whose deterministic
  representative promoter produces a non-empty canonical A/C/G/T sequence.
- Minimum target count: 300.
- Expected annotation candidates: 668 (221 on chr21 and 447 on chr22); the
  exact frozen target count is determined only after sequence validation.
- Full pair count: `50 * frozen_target_count`, and at least 15,000.
- Positive control: none. Phase 3 is a computational-prioritization and
  performance application; no known-pair recall claim will be made.
- Selection seed:
  `gasal2-longtarget-phase3-application-v1-20260724`.

The panel may not be reduced after seeing runtime, correctness, fallback, or
candidate output. A scale-selection pilot is unnecessary because two RTX 4090
GPUs, 21 TB free storage, and Phase 2 timings support the recommended panel.

## Checkpoint 1: Input And Manifest Freeze

### Files

Checkpoint 1 creates:

- `reproduce/bioinformatics/fetch_application_inputs.sh`
- `reproduce/bioinformatics/build_application_panel.py`
- `reproduce/bioinformatics/application_inputs/queries/*.fa`
- `reproduce/bioinformatics/application_inputs/targets/*.fa`
- `paper/bioinformatics/application_selection.json`
- `paper/bioinformatics/application_sources.tsv`
- `paper/bioinformatics/application_manifest.tsv`
- `paper/bioinformatics/application_manifest.sha256`
- `paper/bioinformatics/application_protocol.md`
- `paper/bioinformatics/application_input_summary.tsv`
- `tests/check_build_bioinformatics_application_panel.py`
- `scripts/check_bioinformatics_phase3_freeze.sh`
- Make target `check-bioinformatics-phase3-freeze`

The existing Phase 2 builder, manifest, protocol, runner, raw artifacts, and
evidence files remain byte-for-byte unchanged.

### Query Selection

The builder parses GENCODE transcript metadata and lncRNA FASTA records with
strict UTF-8 and FASTA validation. A transcript is eligible when:

- its GENCODE gene type is `lncRNA`;
- it is on chr1-chr22 or chrX;
- its sequence is canonical A/C/G/T;
- its length is 500-2812 nt;
- its stable gene ID, gene name, and sequence digest are absent from
  `paper/bioinformatics/development_query_exclusions.tsv`;
- its stable gene ID and sequence digest are absent from the Phase 2 holdout
  manifest.

One transcript per stable gene is chosen by this exact ascending key:

1. annotation level;
2. `basic` tag preferred;
3. longer eligible sequence preferred;
4. full transcript ID.

The representative genes are ordered by SHA-256 of the ASCII string
`selection_seed|stable_gene_id|stable_transcript_id|sequence_sha256`. The first
50 are selected and assigned `aq001` through `aq050`. No biological label,
name, chromosome, candidate count, runtime, or result participates in
selection.

### Target Selection

The builder considers GENCODE `transcript` features with gene type
`protein_coding` on chr21 or chr22. One transcript TSS per stable gene is
chosen by this exact ascending key:

1. `MANE_Select` tag preferred;
2. `Ensembl_canonical` tag preferred;
3. `appris_principal_1` tag preferred;
4. any other `appris_principal` tag preferred;
5. `basic` tag preferred;
6. annotation level;
7. longer transcript span preferred;
8. full transcript ID.

For a plus-strand transcript, the TSS is its start; for a minus-strand
transcript, the TSS is its end. The promoter is -2000/+500 in transcriptional
orientation, clipped to chromosome bounds and stored as forward-genomic
sequence. A target is retained only when the materialized sequence is
non-empty and canonical A/C/G/T. Targets are sorted by chromosome number, TSS,
stable gene ID, and transcript ID, then assigned `at0001` onward. Excluded
noncanonical or empty windows are counted in the selection receipt; they are
not replaced from another chromosome.

### Manifest Schema

`application_manifest.tsv` contains one row per frozen input record, not one
row per query-target pair. Its exact columns are:

```text
record_id
record_role
source_release
assembly
original_gene_id
original_gene_name
original_transcript_id
selection_rule
sequence_length
chromosome
strand
tss
region_start
region_end
sequence_sha256
file_sha256
path
license_note
split
status
```

Query coordinate fields use `NA`. Every record has `split=application` and
`status=preregistered_not_run`. Paths are repository-relative. Gene IDs,
record IDs, sequence digests, and file paths are unique within their required
scope. Query rows state that GENCODE project data are open access. Target rows
state that UCSC data-use conditions and Genome Reference Consortium
attribution apply. Both state that final redistribution approval remains
owner-controlled.

`application_input_summary.tsv` contains one row with query count, target
count, pair count, total query bases, total target bases, per-chromosome target
counts, minimum/maximum query length, annotation candidate count, excluded
target count, and the manifest SHA-256. All values are derived from the
manifest and FASTA files.

`application_sources.tsv` records provider, release, assembly, exact URL,
upstream checksum, local cache path, compressed and decompressed sizes and
SHA-256 digests, terms, redistribution note, reconstruction command, and
verification status for all four upstream files.

`application_selection.json` records source hashes and sizes, exclusion source
hashes, candidate and exclusion counts, the exact selection rules, every
selected record, and the proposed freeze ID. The final freeze ID is
`bioinformatics-phase3-application-v1-` followed by the first eight characters
of the manifest SHA-256.

### Publication And Reconstruction

The builder stages the complete FASTA tree, selection receipt, manifest,
manifest checksum, source ledger, and input summary in a temporary sibling
directory. It validates the complete staged tree before publishing. Existing
destinations are accepted only when byte-identical; otherwise the build fails.
No partial overwrite or silent replacement is allowed.

The fetch script pins URL, compressed-source MD5, compressed-source SHA-256,
decompressed chromosome SHA-256, and byte size. It downloads only into
`.tmp/bioinformatics_application_sources`, reconstructs the staged panel, and
compares every generated artifact with the committed freeze.

The freeze checker performs reconstruction when sources are present and
otherwise performs all offline structural, schema, digest, overlap, count, and
immutability checks. It explicitly rejects any Phase 3 artifact root, runner
receipt, result table, or completed status before checkpoint 2.

## Checkpoint 2: Runner And Attempt-Plan Freeze

Checkpoint 2 is designed only after checkpoint 1 is committed. It creates an
immutable execution identity and exact cross-product plan from the frozen
record manifest.

### Modes

Every formal pair runs these user-visible arms:

- A: `cpu-authority --contract all-ranked-top5`
- B: `fast-experimental --contract auto`
- C: `safe --contract all-ranked-top5`

Under the Phase 2 decision, C must resolve to verified comparison for eligible
inputs and publish candidate output only after a clean comparison; mismatch or
comparator/candidate failure publishes authority. The primary B3 performance
claim uses C, never B.

### Execution Shape

- Worker density is exactly two.
- Worker 0 is pinned to GPU 0; worker 1 is pinned to GPU 1.
- At most one process uses each GPU.
- A shared, checksum-bound execution snapshot is stored once per batch rather
  than copied into every pair directory.
- The full panel is run once in arm blocks A, B, C so each arm has an observed
  batch makespan.
- A deterministic repeat subset contains 10 queries spanning the frozen query
  length distribution and 20 targets (10 per chromosome), selected only from
  input metadata and the Phase 3 seed.
- The repeat subset runs six paired repeats. Even repeats use A-B-C and odd
  repeats use C-B-A, providing three observations in each order.
- A fixed first-pair pilot runs A, B, and C once after the runner commit. It is
  excluded from formal source data.
- Backend timeout is 3600 seconds per mode.
- There are no retries, replacements, exclusions, or parameter changes after
  pilot or formal execution starts.

Phase 2 mean per-pair timings project approximately 1.5 h for A, 3.2 h for B,
and 3.8 h for C at two-worker density, before orchestration overhead. Three
complete repeats would exceed the preregistered 24-hour application execution
budget, so the full-panel descriptive run plus six balanced subset repeats is
fixed before execution.

The runner must preserve every report, output, stderr/stdout log, time sample,
GPU telemetry sample, return code, timeout, OOM, guard result, fallback reason,
and publication digest. Its plan-only mode performs no backend execution.

## Checkpoint 3: Analysis And B3 Decision

The analyzer validates the frozen manifest, execution identity, exact attempt
set, raw artifact ledger, reports, output trees, and source hashes without
following symlinks. It recomputes authority/candidate score, stability, Nt,
all-ranked, boundary-tie, and full-row comparisons for every formal pair. It
also checks that every safe publication is contract-safe and that fallback
outputs are byte-identical to authority output where applicable.

It generates:

- `paper/bioinformatics/source_data/application_runs.tsv`
- `paper/bioinformatics/source_data/application_summary.tsv`
- `paper/bioinformatics/source_data/application_correctness.tsv`
- `paper/bioinformatics/application_report.md`
- `paper/bioinformatics/figures/application_panel.svg`
- `paper/bioinformatics/figures/application_panel.pdf`
- an exact raw-artifact manifest and Phase 3 checker

Reported timing includes per-call wall seconds, observed full-arm makespan,
paired subset timing, peak RSS, peak GPU memory, and failure/fallback counts.
The 24-hour capacity estimate is computed from observed safe-pipeline formal
throughput. Candidate capability is reported separately.

B3 passes only when the real panel reaches all minimum counts, every safe final
output is clean or fail-closed to authority, every failure and fallback remains
visible, and safe C satisfies at least one declared widening criterion:

```text
safe full-batch or paired-median speedup >= 10x
or observed wall-time reduction >= 8 hours
or observed 24-hour pair-capacity gain >= 10x
```

Otherwise B3 is explicitly `no_go`; candidate-only speedup cannot rescue it.

## Failure Handling

All checkpoints fail closed on malformed source data, source checksum drift,
duplicate IDs, development/holdout overlap, noncanonical sequence, count below
the Phase 3 minimum, unsafe paths, symlinks, partial trees, receipt mismatch,
missing attempts, extra attempts, invalid reports, output-manifest drift, or
mutation of a prior freeze. Scientific mismatches are retained as results.
Technical failures are retained and never silently retried.

## Test Strategy

Checkpoint 1 tests use small synthetic GTF/FASTA fixtures to prove transcript
priority, strand-aware promoter coordinates, chromosome clipping, canonical
filtering, deterministic hash selection, development and holdout exclusion,
exact record schema, exact counts, transactional publication, reconstruction,
and rejection of drift or symlinks. The real committed panel is regenerated
byte-for-byte from pinned sources.

Checkpoint 2 tests use fake backends to prove plan-only non-execution, exact
cross-product cardinality, two-worker/GPU binding, arm order, pilot exclusion,
timeout and no-retry behavior, shared snapshot identity, atomic receipts, and
complete failure retention.

Checkpoint 3 tests mutate coherent sandbox copies of receipts and outputs to
prove that counters, publication sources, fallback reasons, hashes, paths,
attempt sets, timing aggregates, correctness counts, capacity calculations,
and narrative text are derived rather than trusted or hardcoded.
