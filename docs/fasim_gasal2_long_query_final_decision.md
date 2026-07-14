# GASAL2 long-query architecture final decision

## Final decision

```text
long_query_architecture_no_go_with_complete_evidence
```

The segmented long-query architecture is not promoted as a product runtime.
The safe components work, but the integrated bounded candidate reached only
`1.089028x` median speedup on KCNQ1OT1 max8 x chr22. This is below the Phase 7
`1.10x` runtime threshold and the 10% permission gate for running the full
121-segment candidate.

This decision does not revoke the existing short-query GASAL2 product scope or
the independently useful default-off archive-first and exact-scoreInfo
components.

## Phase ledger

| Phase | Status | Result |
|---:|---|---|
| 0 | pass | baseline, contracts, inputs and artifact provenance frozen |
| 1 | pass | exact archive-first streaming merge with bounded SQLite dedup |
| 2 | no_go | segment ownership did not prove a safe work-drop authority |
| 3 | no_go | no valid persistent target/context boundary; setup ceiling is limited |
| 4 | no_go | dependency no-go because Phase 3 B=1 prerequisite is unavailable |
| 5 | pass | legacy-minScore plus GPU pruned scoreInfo is a safe default-off component |
| 6 | no_go | exact traceback certificates cover at most 0.0508% of requests |
| 7 | no_go | bounded integration clean but max8 median is below promotion gates |
| 8 | pass | scoped final decision, runtime notes and aggregate gates completed |

Phase 4 was not implemented and is not presented as tested microbatch code. It
is closed as dependency `no_go`, rather than left `blocked`, because the hard
prerequisite failed for an architectural reason rather than a missing external
resource.

## What passed

### Archive-first output

The Phase 1 path:

```text
restores the claimed TFOsorted rows exactly
uses FATFOC1 version 2 typed archives
does not emit per-segment full TFOsorted text
uses bounded SQLite exact dedup
atomically publishes merged output
keeps the existing default path unchanged
```

On the Phase 7 max8 scope, archived segment input was `95766154` bytes versus
`610786260` bytes of historical per-segment full text, a `6.377893x` storage
reduction. Storage reduction is not counted as compute speedup.

```text
archive/text reduction=6.377893x
per-segment full text bytes=0
```

### Exact-column scoreInfo

The safe Phase 5 candidate retains legacy-authority minScore and enables:

```bash
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=0
```

It reduced the integrated max8 exact-stage median from `120.437260 s` to
`86.010090 s` (`28.585149%`) without changing GASAL2 requests, traceback
requests, exact tasks or exact cells.

### Bounded integration contracts

For small, H19 short, max4 and two max8 pairs:

```text
full merged TFOsorted byte equal per shifted grid=1
missing rows=0
extra rows=0
score-ranked clustered top5 equal=1
stability-ranked clustered top5 equal=1
Nt-ranked clustered top5 equal=1
offline clustered TFO1-TFO5 equal=1
fallbacks=0
length-guard fallbacks=0
exact-scoreInfo overflow/fallback batches=0
OOM=0
```

The two max8 repeats had stable direction:

```text
baseline median=1013.409552 s
candidate median=930.563144 s
wall reduction=8.175018%
speedup=1.089028x
```

## What was no-go

### Ownership and persistent context

Shifted-grid ownership produced short-oracle extra rows and did not establish a
safe authority for dropping exact or traceback work. The current GASAL2 target
batches are query-dependent; they cannot be replaced by one resident target
upload without a new target-ID/offset execution contract.

### Multi-segment microbatch

Phase 4 requires the Phase 3 persistent B=1 context. Since that prerequisite
is unavailable, a host-only batching wrapper would not satisfy the specified
memory/reuse contract and was not built as misleading scaffold.

### Traceback request reduction

The exact pre-drop shadow had zero false rejects, but its best observed coverage
was only `64990 / 128054052 = 0.0508%` on max8. Rank-aware pruning has only a
score certificate; safe stability and Nt upper bounds remain unavailable.
Real traceback skip stays disabled.

### Integrated promotion

The max8 candidate was consistently faster but below the gate. Consequently:

```text
full segmented KCNQ1OT1 x chr22 integrated candidate=not run
full KCNQ1OT1 x hg38=not run
long-query product preset=not promoted
```

## Runtime status

All long-query additions remain default-off:

```text
segmented archive-first runner
GPU pruned scoreInfo exact-column variant
traceback certificate shadow
segment ownership shadow
two-grid KCNQ1OT1 characterization
```

There is no H19-, KCNQ1OT1- or chromosome-specific runtime branch in the safe
components. The fixed traceback threshold calibration is not part of this
architecture and is not a general long-query recommendation.

The existing supported product recommendation remains the checked short-query
normal-triplex lite scope documented in
`docs/fasim_gasal2_top5_recommended_runtime.md`. The current unsegmented GASAL2
query contract is implementation-bounded at 2812 bp; this is not a biological
definition of lncRNA length.

## Supported scope

Supported by existing product evidence:

```text
normal-triplex lite
validated short-query contract
one worker or one worker per GPU
existing authority/fallback path retained
```

Supported only as default-off components or characterization:

```text
archive-first output and exact restore
legacy-minScore plus GPU pruned scoreInfo
bounded KCNQ1OT1 max8 dual-grid workflow on chr22
resumable per-segment receipts and config digests
```

The bounded max8 workflow is not a production recommendation despite its clean
paired output contracts.

## Unsupported scope

```text
unsegmented full-length MALAT1, NEAT1 or KCNQ1OT1 acceleration
full-transcript KCNQ1OT1 integrated validation
full-hg38 segmented KCNQ1OT1 validation
single-grid substitution for the dual-grid contract
direct-lite or unrelated archive-first finalizer shapes
more than one worker per 24 GB GPU
multi-worker or multi-GPU segmented resource promotion
real traceback certificate pruning
full-output equivalence inferred only from top5 or shifted-grid stability
```

## Resource boundary

The checked machine used one NVIDIA GeForce RTX 4090 with `24564 MiB` total
memory visible to one worker. A 100-ms external probe of a representative
2048-bp candidate segment x chr22 recorded:

```text
peak compute-process device memory=14976 MiB
peak host RSS=931488 KiB
configured device budget=22 GiB
```

This is a same-length representative segment probe, not per-segment peak
sampling over full KCNQ1OT1. Keep one worker per GPU. No multi-worker memory
claim is made.

## Reproduction

There is no recommended production invocation for the integrated long-query
candidate. The bounded evidence can be reproduced after preparing the inputs
named in the Phase 7 config manifests:

```bash
make build-fasim-gasal2
CUDA_VISIBLE_DEVICES=0 \
MAX8_REPEATS=2 \
WORK="$PWD/.tmp/phase7_gasal2_long_query_integrated" \
make characterize-fasim-gasal2-long-query-integrated-phase7
```

The driver is fail-closed and resumable. Each run records binary/input/config
digests; each segment atomically records its archive digest; the completed run
records summary and merged-output digests. A config mismatch cannot reuse old
receipts.

For an individual grid, `segment_outputs.tsv` is the typed merge manifest.
`scripts/merge_fasim_segmented_tfosorted.py` restores archive rows, applies the
global query interval, performs exact bounded dedup and atomically writes
`merged-common-TFOsorted`. Do not concatenate segment text or keep only each
segment's local top5.

## Fallback behavior

The runtime authority remains the existing CPU/exact path. A GASAL2 allocation,
length or runtime failure must be reported and routed through the existing
fallback; it must not be labeled a clean GPU run. The Phase 7 evidence requires
all fallback counters to be zero.

Resume validation fails closed on config, input, archive, summary or merged
output digest drift. It never silently mixes segments from different configs.

## Correctness interpretation

The following statements remain distinct:

```text
byte-equal bounded baseline/candidate outputs != unsegmented full equivalence
shifted-grid clustered top5 stability != complete row-set equivalence
top5 equality != biological equivalence of every reported row
archive restore equality != aligner authority
exact-stage speedup != end-to-end speedup
```

## Known limitations

- Full-length long lncRNAs still require segmented execution; segmentation can
  change global semantics unless overlap, coordinates, dedup, ties and clustering
  are explicitly preserved.
- Dual shifted grids double work and remain required by the current contract.
- Traceback conversion is a large CPU stage, but no material safe pre-traceback
  rejection certificate was found.
- The current process-per-segment runner repeats target setup and cannot share a
  device-resident target context.
- The integrated max8 result has two repeats because each mode takes roughly
  15.5--16.9 minutes; the full observed range is reported.

## Next valid research question

The next defensible optimization line is bounded CPU traceback-result
materialization/conversion and GASAL2 memory-footprint reduction without
dropping requests. It should begin with profile-guided CIGAR/result-copy data
layout changes and exact byte/top5 gates. A persistent target engine is a
separate execution-contract redesign, not an incremental follow-up to the
current runner.

## Aggregate validation

```bash
make check-fasim-gasal2-long-query-final
```
