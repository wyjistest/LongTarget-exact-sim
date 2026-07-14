# GASAL2 long-query exact-column optimization

## Decision

Phase 5 is a `pass` with a default-off `strong_go` candidate:

```text
candidate = legacy-authority minScore + GPU pruned scoreInfo
scope = one validated short-query segment per process
runtime default = unchanged
```

The result does not validate full-transcript KCNQ1OT1 output equivalence. It
validates the exact-stage replacement on a 2048-bp KCNQ1OT1 segment against a
full chr22 target, plus a full-length 2812-bp H19 short-query control.

## Entry profile

The entry profile aggregates all 121 segment logs from the existing two-grid
full KCNQ1OT1 x chr22 artifact. Wall values are sums across segment processes,
not a single-process elapsed time.

```text
runs=121
end_to_end_seconds=8687.413318
exact_stage_seconds=911.212000
exact_stage_percent=10.49
exact_kernel_seconds=545.095930
exact_kernel_percent_of_stage=59.82
exact_h2d_seconds=23.447899
exact_d2h_seconds=92.505883
exact_launches=11374
exact_tasks=46562736
exact_cells=232813680000
fallbacks=0
entry_gate=material
```

The tracked per-segment receipt is
`docs/fasim_gasal2_exact_column_long_query_entry_profile.tsv`.

## Task compaction shadow

The shadow considers only byte-identical `seq2` inputs within the same exact
batch. Hashes are used only to form candidate buckets; string equality is the
authority, so hash collisions cannot drop work. The mode is observational and
always reports `runtime_work_dropped=0`.

On one KCNQ1OT1 2048-bp segment x chr22 2-Mb target:

```text
exact_tasks_before=10368
shadow_candidate_tasks_after=10368
shadow_candidate_tasks_dropped_identical=0
exact_cells_before=51840000
shadow_candidate_cells_after=51840000
runtime_work_dropped=0
```

Therefore exact task compaction is `no_go` for the measured workload. Phase 2
segment ownership is not used to remove exact tasks because it did not prove a
runtime-work authority.

## Rejected fused candidate

The first candidate fused column maxima, minScore derivation, scoreInfo grouping
and pruning. It was faster but failed the full-row gate on chr22 full:

```text
baseline median wall=49.79 s
column-minScore candidate median wall=40.52 s
baseline scoreInfo input groups=5483009
candidate scoreInfo input groups=5483030
restored baseline rows=47636
restored candidate rows=47637
missing rows=0
extra rows=1
```

The root cause is the minScore authority. The production baseline derives
minScore from the legacy `calc_score_once`-equivalent score. The rejected kernel
derived minScore from the exact-column row maximum. Those values differ on a
small number of chr22 tasks, producing 21 extra scoreInfo groups and one extra
final row. This candidate is not promoted despite its larger wall reduction.

## Promoted candidate

The promoted candidate retains the legacy-authority minScore pass and replaces
the full column-maxima D2H plus host scoreInfo construction with the existing
GPU pruned-scoreInfo path:

```bash
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
```

`FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT` is deliberately absent.

### KCNQ1OT1 segment x chr22 full

Configuration:

```text
query source=KCNQ1OT1 ENST00000597346.1
query segment=0..2048
target=chr22 full, 50818468 bp
rule=0
repeats=3, interleaved
output=archive-first TFOsorted
```

Results:

```text
baseline median wall=50.400000 s
candidate median wall=44.950000 s
wall reduction=10.81%
speedup=1.121246x

baseline median exact stage=7.714830 s
candidate median exact stage=4.712460 s
exact-stage reduction=38.92%

exact tasks=384816 per run, equal
exact cells=1924080000 per run, equal
exact launches=94 per run, equal
full archive SHA-256 equal=3/3
fallbacks=0
overflow batches=0
promotion_gate=strong_go
```

The paired receipt is
`docs/fasim_gasal2_exact_column_long_query_benchmark.tsv`.

### H19 short-query control

The full 2812-bp H19 fixture was run against the chr22 2-Mb target for five
interleaved repeats:

```text
baseline median wall=2.510000 s
candidate median wall=2.360000 s
wall reduction=5.98%
speedup=1.063559x
baseline median exact stage=0.314802 s
candidate median exact stage=0.235049 s
exact-stage reduction=25.33%
full archive SHA-256 equal=5/5
fallbacks=0
overflow batches=0
```

The short-query control improves rather than regresses, satisfying the <=3%
regression gate. The paired receipt is
`docs/fasim_gasal2_exact_column_short_query_control.tsv`.

## Correctness and boundary gates

The automated gates cover:

```text
per-task scoreInfo validation against CPU authority
full TFOsorted byte equality
score / stability / Nt-score top5 equality
offline clustered TFO1-TFO5 equality
rule=0 exact-column overflow digest
max-per-task 512 and 2048 fixtures
partial and 5000-bp target tiles
single-visible-device guard
fallbacks=0
```

The chr22 full and H19 performance receipts additionally require identical
archive bytes for every paired run. This is stronger than top5-only equality for
those bounded workloads, but it is not a claim of full segmented-transcript or
full-hg38 equivalence.

## Scope

The candidate remains default-off. It applies to the current normal-triplex
lite/archive-first short-query segment path. It does not extend the 2812-bp
unsegmented query limit, does not cover direct-lite or archive-first finalizer
shapes beyond the tested path, and does not promote the rejected
column-derived-minScore fusion.

Phase 6 can proceed independently to traceback timing and safe candidate
certificates.
