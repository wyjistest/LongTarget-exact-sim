# GASAL2-LongTarget paper scope and claims

## Fixed positioning

The paper package supports this working scope:

> A contract-aware GPU acceleration path for short-query top-K prediction in
> Fasim-LongTarget, with a systematic characterization of its operating
> envelope.

The supported runtime surface is default-off, normal-triplex, short-query
top-K. The current unsegmented query contract is implementation-bounded at
2812 bp. Supported density is one worker or one worker per GPU. This is not a
biological definition of short lncRNAs.

The long-query architecture remains closed as:

```text
long_query_architecture_no_go_with_complete_evidence
full 121-segment candidate = not run
full hg38 = not run
persistent target context = no-go under the current execution contract
segment ownership work drop = no-go under the current output contract
real traceback certificate skip = disabled
```

## C1 - Short-query fast top-K acceleration

Allowed: within the validated short-query, normal-triplex, fast top-K contract
and recorded hardware scope, the GASAL2 path can materially reduce wall time
while preserving score-, stability- and Nt-ranked clustered TFO1-TFO5.

Contract: `fast_topk_score_stability_nt`.

Required evidence: query length, target scope, GPU count, worker placement,
paired repeats, equal baseline/candidate contract, all three top5 gates and all
fallback counters. The historical 40.119136x row is a starting point, not the
paper estimate.

Prohibited: a general LongTarget speedup, full-output replacement, or a claim
covering all lncRNAs.

## C2 - Non-H19 generalization

Allowed: there is no H19-name or H19-sequence runtime special case, and
multiple preregistered non-H19 short-query workloads may be contract-clean and
faster under one preset.

Contract: `fast_topk_score_stability_nt` plus guarded long-query negative
controls.

Required evidence: immutable preregistration, at least three valid pairs for
core rows, all breadth rows retained, one preset, and all clean/mismatch/guard
outcomes in source data.

Prohibited: a guarantee that every short query is clean or accelerated.

## C3 - Contract-aware correctness and fail-closed behavior

Allowed: eligibility is established by separate score, stability and Nt
clustered top5 comparisons plus explicit ties, fallback, guard, overflow and
OOM accounting.

Contract: workload-specific `fast_topk_score_stability_nt`,
`full_tfosorted_rowset`, or `preflight_guard_only`.

Prohibited: treating top5 equality as full row-set equality, or counting a
fallback-heavy run as a clean GPU replicate.

## C4 - Two-slot overlap

Allowed: at one worker per GPU, checked two-slot CPU/GPU overlap can reduce wall
time relative to the same synchronous preset.

Contract: paired `fast_topk_score_stability_nt` runs with identical preset and
output work.

Required evidence: at least five valid pairs each for chr21 and chr22, balanced
order, stage timing, peak memory, all three top5 gates and zero fallback.

Prohibited: extrapolation to multiple workers sharing one 24 GB GPU or
attribution of every saved second to device-kernel overlap.

## C5 - Archive-first storage and bounded merge

Allowed: archive-first can restore the declared TFOsorted rows exactly, reduce
storage and support bounded-memory exact merge.

Contract: `archive_restore_only` or `shifted_grid_bounded_full_rows`, declared
per workload.

Required evidence: archive and text bytes, storage ratio, restore and merge
wall, complete run-plus-merge wall, peak merge RSS and exact dedup metadata.

Prohibited: counting storage reduction as compute speedup or inferring
segmentation completeness from archive equality.

## C6 - Exact-column component optimization

Allowed: legacy-minScore plus GPU pruned scoreInfo can reduce exact-column
stage time in its checked scope. Stage improvement and end-to-end improvement
must be reported separately.

Contract: same complete archive/TFOsorted output for baseline and candidate,
plus all three top5 checks.

Required evidence: stage share, stage and end-to-end wall, tasks, cells,
requests, traceback requests, overflow and fallback counters for at least three
compatible pairs.

Prohibited: presenting component-stage reduction as the same end-to-end
speedup or promoting the rejected column-derived-minScore variant.

## C7 - Operating envelope and long-query limits

Allowed: the strongest benefit is scoped to short-query top-K; complete-output
rows are near parity in existing evidence, and the bounded max8 long-query
candidate reached only 1.089028x and missed promotion.

Contract: `full_tfosorted_rowset` for complete-output rows,
`shifted_grid_bounded_full_rows` for max8, and `preflight_guard_only` for
unsupported full-length queries.

Required evidence: at least three valid max8 pairs, exact bounded row/top5
contracts, zero fallback/OOM, descriptive full-output rows and explicit
negative architecture results.

Prohibited: unsegmented full-length MALAT1, NEAT1 or KCNQ1OT1 acceleration;
full-transcript or full-genome equivalence; or a promoted persistent target,
ownership-drop or traceback-skip path.

## Interpretation boundary

The following remain different claims:

```text
top5 equality != complete row-set equality
shifted-grid stability != unsegmented equivalence
archive restore equality != aligner authority
kernel or stage speedup != end-to-end speedup
historical single-run value != paper repeated estimate
```
