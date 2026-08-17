# GASAL2 integrated long-query result

## Decision

Phase 7 is an evidence-complete `no_go` for product runtime promotion.

```text
integrated candidate:
  segmented archive-first output
  bounded SQLite merge
  legacy-authority minScore
  GPU pruned scoreInfo exact-column path

explicitly disabled/absent:
  persistent multi-segment context
  segment ownership work drop
  traceback certificate shadow
  real traceback skip

max8 median speedup=1.089028x
max8 median wall reduction=8.175018%
full KCNQ1OT1 x chr22 gate=denied
```

The candidate is faster and correctness-clean in the bounded ladder, but the
max8 median is below both the 10% permission gate for the full run and the
Phase 7 `1.10x` runtime threshold. The 121-segment full candidate was therefore
not run. This is not a full-transcript KCNQ1OT1 result.

## Integrated configuration

Every run has a canonical `run-config.json`. The config payload enters
`config_digest_sha256`; a changed binary, input, segmentation parameter,
stream/batch setting or exact-column variant cannot resume an old run.

The max8 configuration was:

```text
binary_sha256=613b24d9190b8b931661fce231ded6662d2b2b3e5772262310e069c15f191cc8
query_sha256=f8883e1855017b7a28576770a8c8476a8eb1adbfcbef08d55c6dc74c49a86cc4
target_sha256=ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f
segment_len=2048
segment_overlap=512
grid_shifts=0,256
max_segments=8
archive_first=true
persistent_context=false
segment_batch_size=1
worker_count=1
gpu_ids=0
streams=3
gasal2_batch=20000
merge_dedup_backend=sqlite
traceback_certificate_mode=disabled
device_memory_budget_bytes=23622320128
```

The baseline uses `legacy_authority_scoreinfo`. The candidate changes only:

```text
exact_column_variant=gpu_pruned_scoreinfo_v1
exact_scoreinfo_gpu_max_per_task=512
```

The run was executed from parent commit `d50dd2c`; the Phase 7 commit contains
the runner, comparator, summarizer and tracked receipts. The executable digest,
input digests and complete runtime config are recorded independently of the
commit field.

## Resumability

Each completed segment atomically writes `segment-complete.json` containing:

```text
config digest
segment id and global query interval
query and target digests
archive path and digest
segment wall time
```

An incomplete segment directory is rerun; a valid receipt is reused. The
completed merged run atomically writes `run-complete.json`, tied to the config
and summary digest. Existing default behavior remains destructive only when
`RESUME=0`; Phase 7 explicitly used `RESUME=1`.

## Bounded ladder

The tracked aggregate receipt is
`docs/fasim_gasal2_long_query_integrated_benchmark.tsv`.

| Workload | Repeats | Baseline median | Candidate median | Reduction | Speedup | Contract |
|---|---:|---:|---:|---:|---:|---|
| KCNQ1OT1 small, max2 x chr22 2 Mb | 1 | 10.835249 s | 10.289051 s | 5.040936% | 1.053085x | clean |
| H19 short control x chr22 2 Mb | 1 | 6.364126 s | 5.921260 s | 6.958787% | 1.074793x | clean |
| KCNQ1OT1 max4 x chr22 full | 1 | 552.151763 s | 503.931416 s | 8.733169% | 1.095688x | clean |
| KCNQ1OT1 max8 x chr22 full | 2 | 1013.409552 s | 930.563144 s | 8.175018% | 1.089028x | clean |

### Max8 repeats

Runs were interleaved by reversing mode order in repeat 2.
Phase 7 permits two repeats when a max8 pair is expensive; each mode required
about 15.5--16.9 minutes of pipeline wall, so the bounded gate used two rather
than three repeats and reports the full observed min/max range.

| Repeat | Order | Baseline | Candidate | Reduction | Speedup |
|---:|---|---:|---:|---:|---:|
| 1 | baseline -> candidate | 1012.899019 s | 931.573672 s | 8.028969% | 1.087299x |
| 2 | candidate -> baseline | 1013.920085 s | 929.552615 s | 8.320919% | 1.090761x |

The performance direction is stable. It is not large enough for promotion.

### Stage interpretation

For max8 medians:

```text
exact stage:
  120.437260 s -> 86.010090 s
  reduction=28.585149%

host-observed traceback stage:
  373.807174 s -> 373.706758 s

GASAL2 requests:
  baseline=candidate=303560481 per paired run

traceback requests:
  baseline=candidate=128054052 per paired run

exact work:
  tasks=6157056
  cells=30785280000
```

The exact-scoreInfo path reduces exact-stage time without changing request or
DP-work counts. The end-to-end difference is not attributed solely to this
stage because merge, scheduling and ordinary run variance remain in the outer
wall measurement.

## Correctness

For every baseline/candidate pair and both shifted grids:

```text
full merged TFOsorted byte equal=1
missing rows=0
extra rows=0
score-ranked top5 equal=1
stability-ranked top5 equal=1
Nt-ranked top5 equal=1
offline clustered TFO1-TFO5 equal=1
archive restore clean=1
per-segment full TFOsorted text emitted=0
fallbacks=0
length-guard fallbacks=0
exact-scoreInfo overflow batches=0
exact-scoreInfo fallback batches=0
OOM=0
```

Within each mode, shifted-grid clustered TFO1-TFO5 is also 5/5. That is a grid
stability result, not unsegmented equivalence. Baseline/candidate byte equality
is scoped to the same bounded segmented configuration.

## Storage and memory

The historical max8 per-segment full-text inputs total `610786260` bytes. The
integrated archive-first inputs total `95766154` bytes:

```text
archive/text reduction=6.377893x
per-segment temporary full text bytes=0
bounded SQLite merge active=1
```

A separate 100-ms external sampling probe reran one representative 2048-bp
max8 candidate segment against chr22 full on an RTX 4090:

```text
GPU total memory=24564 MiB
peak compute-process device memory=14976 MiB
peak host RSS=931488 KiB
device budget=22 GiB
fallbacks=0
```

The memory result is a representative same-length segment probe, not a claim that every segment was independently sampled.
It supports one worker per GPU; it does not validate multi-worker density.

## Full-run gate

The required max8 conditions evaluate as:

```text
correctness clean=true
fallbacks=0
OOM=0
performance direction stable=true
median wall improvement >=10%=false
short-query regression <=3%=true
max8_full_run_allowed=0
```

Consequently:

```text
full segmented KCNQ1OT1 x chr22 candidate=not run
full KCNQ1OT1 x hg38=not run
unsegmented full-length equivalence=not claimed
runtime promotion=no_go
```

The older 121-segment authority artifact remains valid timing evidence for
Phases 0, 3, 5 and 6. It is not relabeled as a Phase 7 integrated candidate.

## Validation

```bash
python3 tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py
python3 tests/check_compare_fasim_gasal2_long_query_integrated.py
python3 tests/check_summarize_fasim_gasal2_long_query_integrated.py
make check-fasim-gasal2-long-query-integrated-phase7
```

Phase 8 should close the overall architecture as
`long_query_architecture_no_go_with_complete_evidence`, while preserving the
independently useful default-off archive-first and exact-scoreInfo components.
