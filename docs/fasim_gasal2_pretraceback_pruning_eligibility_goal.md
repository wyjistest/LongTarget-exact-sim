# Fasim GASAL2 Pre-Traceback Pruning Eligibility Goal

This document is a copy-ready `/goal` prompt for the next narrow GASAL2
milestone after PR #170. It turns the traceback rejection taxonomy into a more
specific eligibility question:

```text
Which rejected traceback attempts can be proven redundant before traceback, and
which still require CIGAR/final ordering to decide?
```

This goal must not enable pruning. It only adds telemetry, representative
mapping, parser checks, smoke validation, and a written checkpoint.

## Goal Prompt

```text
/goal

Create a telemetry-only PR that classifies GASAL2 pre-traceback pruning
eligibility for rejected traceback attempts.

Base:
  gasal2-traceback-rejection-taxonomy after PR #170, or its merge result.

Working branch suggestion:
  fasim-gasal2-pretraceback-pruning-eligibility

Objective:
  Split the #170 residual final_sort_dedup_removed and invalid_span_bound
  buckets into representative-linked eligibility sub-buckets.

  The PR must answer:
    - How many removed attempts can be mapped to a retained representative?
    - How many removed attempts are exact pre-traceback duplicates?
    - How many require CIGAR, converted alignment fields, final sort/dedup, or
      representative selection?
    - Is there any output-inert shadow evidence that a future lazy-traceback
      duplicate filter could be safe?

Do not:
  - enable real pruning
  - skip traceback at runtime
  - change default behavior
  - change output semantics
  - change scoring, thresholds, endpoint, CIGAR, traceback, merge, sort, or
    non-overlap policy
  - promote GASAL2 endpoint/CIGAR/traceback/score/digest as authority
  - claim full aligner.Align() replacement
  - infer aggregate eligibility rates from capped TSV samples
  - write huge uncapped per-attempt files by default

Context:
  PR #170 added traceback rejection taxonomy telemetry.

  Smoke checkpoint from #170:
    traceback_requests          = 175,193
    retained_emitted           =   8,291
    filtered_nt                =   8,360
    invalid_span_bound         =  25,672
    final_sort_dedup_removed   = 132,870
    unknown                    =       0

  Output contract stayed clean in that smoke:
    baseline_rows              = 8,291
    candidate_rows             = 8,291
    missing_rows               = 0
    extra_rows                 = 0
    top5_score_equal           = true
    top5_stability_equal       = true
    top5_nt_score_equal        = true

Important interpretation:
  unknown=0 in #170 means every attempt was assigned to one aggregate funnel
  bucket under the current priority accounting.

  It does not prove that every attempt's true causal rejection reason is known.

  final_sort_dedup_removed is still a residual aggregate bucket. It must be
  mapped to retained representatives before any pruning claim is made.

Core design:
  Add a new explicit diagnostic env:
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT=/path/to/examples.tsv
    FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT=N

  Emit counters with this prefix:
    benchmark.fasim_gasal2_pretraceback_pruning_eligibility_*

  Keep two data views separate:
    aggregate counters:
      full-run counts used for proportions and decisions

    capped TSV export:
      bounded representative examples, first mismatches, and debug rows only

  Do not derive full-run eligibility percentages from capped TSV rows.

Implementation location hints:
  Start from the #170 traceback rejection taxonomy implementation in:
    fasim/Fasim-LongTarget.cpp

  Add env helpers near the existing:
    fasim_gasal2_traceback_rejection_taxonomy_runtime()
    fasim_gasal2_traceback_rejection_taxonomy_export_path_runtime()

  Add telemetry structs near:
    FasimGasal2TracebackRejectionTaxonomyStats
    FasimGasal2TracebackRejectionTaxonomyExporter

  Wire active state near the current taxonomyEnabled / phaseTimingEnabled setup.

  Build attempt and representative observations in the GASAL2 conversion path
  where #170 already observes selected alignments, converted rows, local
  sort/dedup, and emitted rows.

Required aggregate counters:
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_requested
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_active
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_attempts
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_retained_final_rows
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_removed_attempts
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_mapped_removed_attempts
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unmapped_removed_attempts
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_exact_request_duplicate
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_exact_descriptor_duplicate
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_same_final_row_different_descriptor
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cross_flush_exact_duplicate
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_duplicate
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_representative_selection_dependent
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_sort_or_dominance_removed
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_pretraceback_span_provable
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_reverse_start_dependent_span
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_span
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unknown
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_false_prune_shadow
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_missing_rows_shadow
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_extra_rows_shadow
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_path
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_rows
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_truncated

Required final_sort_dedup_removed sub-buckets:
  exact_request_duplicate
  exact_descriptor_duplicate
  same_final_row_different_descriptor
  cross_flush_exact_duplicate
  cigar_dependent_duplicate
  representative_selection_dependent
  sort_or_dominance_removed
  unknown

Required invalid_span_bound sub-buckets:
  pretraceback_span_provable
  reverse_start_dependent_span
  cigar_dependent_span
  unknown

Bucket definitions:
  exact_request_duplicate:
    Same pre-traceback request key and same representative key. This can only be
    called future-pruning eligible if retaining the canonical representative
    would preserve final rows.

  exact_descriptor_duplicate:
    Same normalized pre-traceback descriptor after ignoring only fields proven
    not to affect final output. Document every ignored field.

  same_final_row_different_descriptor:
    Different pre-traceback descriptor but identical final row fingerprint. This
    is not automatically safe for pruning unless representative selection is
    separately proven stable.

  cross_flush_exact_duplicate:
    Duplicate across flush boundaries. Interesting for future pruning, but not
    immediately safe unless a future runtime can retain the same canonical
    representative across flushes without changing ordering or memory bounds.

  cigar_dependent_duplicate:
    Requires CIGAR, alignment strings, nt, identity, stability, or converted
    row fields to prove equality. Not safe for pre-traceback pruning.

  representative_selection_dependent:
    Requires final sort, tie policy, non-overlap policy, dominance, or global
    representative selection. Not safe for pre-traceback pruning in this PR.

  sort_or_dominance_removed:
    Removed only after final ordering/non-overlap/dominance. Not safe for
    pre-traceback pruning without a separate dominance certificate.

  pretraceback_span_provable:
    Invalid span can be proven using only pre-traceback descriptor metadata such
    as score/end/cutlength/query length/ref length. If the implementation cannot
    prove this without traceback-derived endpoints, it must not count the attempt
    here.

  reverse_start_dependent_span:
    Needs reverse-start recovery or endpoint convention details.

  cigar_dependent_span:
    Needs CIGAR or converted alignment fields.

Required per-attempt TSV columns:
  attempt_id
  flush_id
  task_id
  scoreinfo_index
  prealign_score
  query_len
  target_size
  target_start
  cutlength
  request_key_hash
  descriptor_key_hash
  final_row_hash
  representative_attempt_id
  representative_flush_id
  representative_request_key_hash
  representative_descriptor_key_hash
  same_flush
  cross_flush
  score
  query_begin
  query_end
  ref_begin
  ref_end
  output_global_start
  output_global_end
  nt
  identity
  stability
  cigar_hash
  final_rejection_bucket
  eligibility_bucket
  pre_traceback_decidable
  post_traceback_only
  top5_only_safe_candidate
  full_output_safe_candidate
  notes

Hashing requirements:
  Use stable deterministic hashes.
  Hash only normalized fields.
  Document every field included in:
    request_key_hash
    descriptor_key_hash
    final_row_hash
    cigar_hash

  Do not use:
    pointer addresses
    vector addresses
    unordered map iteration order
    process-order-dependent values unless explicitly part of the stable
    existing output order

Representative mapping requirements:
  For each final row fingerprint, identify the canonical retained representative
  under existing final sort/dedup behavior when possible.

  Removed attempts must be linked to a representative attempt when possible.

  If no representative can be linked:
    increment unmapped_removed_attempts
    classify as unknown or representative_selection_dependent
    mark full_output_safe_candidate=false

  If representative mapping is local-only and not global:
    document that limit in docs/fasim_gasal2_pretraceback_pruning_eligibility.md
    do not claim global pruning safety

Shadow simulation:
  This PR may include a side simulation that marks attempts that a hypothetical
  pre-traceback duplicate filter would skip.

  The real path must still execute every traceback.
  The shadow path must not feed output.

  Required shadow counters:
    false_prune_shadow
    missing_rows_shadow
    extra_rows_shadow

  Shadow must fail closed:
    if representative mapping is incomplete, classify as not safe
    if final row fingerprint differs, classify as not safe
    if tie/order/representative selection is ambiguous, classify as not safe

Required report table:
  eligibility_bucket
  attempts
  fraction_of_traceback_attempts
  fraction_of_removed_attempts
  representative_mapped
  pre_traceback_decidable
  post_traceback_only
  top5_only_safe_candidate
  full_output_safe_candidate
  false_prune_shadow
  missing_rows_shadow
  extra_rows_shadow
  notes

Required parser summary fields:
  eligibility_attempts
  removed_attempts
  mapped_removed_attempts
  unmapped_removed_attempts
  known_eligibility_attempts
  unknown_eligibility_attempts
  pre_traceback_decidable_attempts
  post_traceback_only_attempts
  top5_only_safe_candidate_attempts
  full_output_safe_candidate_attempts
  false_prune_shadow
  missing_rows_shadow
  extra_rows_shadow
  unknown_fraction

Deliverables:
  1. Runtime telemetry counters guarded by the new explicit diagnostic env.
  2. Capped representative TSV export for example attempts and first mismatches.
  3. Parser/summarizer script for stderr counters and capped TSV examples.
  4. Parser check with synthetic stderr/TSV coverage.
  5. Smoke test on the same chr22/H19 fixture used by #170.
  6. Docs checkpoint:
       docs/fasim_gasal2_pretraceback_pruning_eligibility.md

Concrete file names:
  - scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py
  - scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_parser.sh
  - scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_smoke.sh
  - docs/fasim_gasal2_pretraceback_pruning_eligibility.md

Suggested Make targets:
  - check-fasim-gasal2-pretraceback-pruning-eligibility-parser
  - check-fasim-gasal2-pretraceback-pruning-eligibility-smoke

Minimum smoke behavior:
  - Build or reuse the GASAL2-enabled binary.
  - Run the small chr22/H19 fixture with eligibility telemetry enabled.
  - Run the same fixture without eligibility telemetry enabled.
  - Assert baseline/candidate full lite rows are unchanged for the fixture.
  - Assert top5_score/top5_stability/top5_nt_score remain equal.
  - Assert traceback request count is unchanged.
  - Assert eligibility counters are present and active.
  - Assert aggregate bucket totals are bounded by traceback attempts.
  - Assert capped export exists.
  - Assert capped export has the documented header.
  - Assert capped export does not exceed EXPORT_LIMIT plus header.
  - Assert shadow false_prune/missing/extra are zero if shadow simulation is
    implemented.

Suggested smoke command shape:
  make check-fasim-gasal2-pretraceback-pruning-eligibility-smoke \
    GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2 \
    DNA=/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa

Testing:
  - make build-fasim-gasal2 \
      GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2
  - make check-fasim-gasal2-pretraceback-pruning-eligibility-parser
  - make check-fasim-gasal2-pretraceback-pruning-eligibility-smoke \
      GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2 \
      DNA=/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa
  - python3 -m py_compile scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py
  - bash -n scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_parser.sh \
      scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_smoke.sh
  - git diff --check
  - changed-file bidi control scan

Decision:
  If exact_request_duplicate or exact_descriptor_duplicate is large and shadow
  false_prune/missing/extra are all zero:
    next PR may design a default-off lazy-traceback shadow.

  If most removals are cigar_dependent_duplicate,
  representative_selection_dependent, or sort_or_dominance_removed:
    do not pursue pre-traceback pruning for those buckets.

  If unknown > 0:
    do not enable pruning; improve telemetry first.

  If output changes:
    stop and debug. Telemetry must be output-inert.

Completion checklist:
  - docs/fasim_gasal2_pretraceback_pruning_eligibility.md exists and states
    telemetry-only scope, bucket definitions, hash definitions, limitations,
    smoke result, and next decision.
  - Parser check passes.
  - Smoke check passes.
  - Runtime counters are full aggregate counters, not inferred from capped TSV.
  - TSV export is capped and bounded by default.
  - No traceback is skipped.
  - No default behavior changes.
  - No GASAL2 endpoint/CIGAR/traceback/score/digest authority promotion.
```

## Review Notes For The Next Agent

This goal intentionally follows the #170 warning:

```text
traceback rejection destination is closed,
but safe pre-traceback pruning is not proven.
```

The next PR must preserve that boundary. The desired output is an eligibility
taxonomy and representative map, not a faster runtime path.

The highest-value result would be showing that a large share of
`final_sort_dedup_removed` maps to exact pre-traceback duplicate descriptors with
zero shadow false-prune risk. If that is not true, the milestone should say so
clearly and stop there.

## Suggested PR Title

```text
fasim: classify GASAL2 pre-traceback pruning eligibility
```

## Suggested Commit Message

```text
fasim: classify GASAL2 pre-traceback pruning eligibility
```
