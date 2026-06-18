# Fasim GASAL2 Tie-Complete Top5 Traceback Certificate Goal

This document is a copy-ready `/goal` prompt for the next narrow GASAL2
milestone after the pre-traceback span-prune stop checkpoint.

The previous span-prune shadow proved a strict span certificate can be
correctness-clean, but only skipped 22 of 175,193 selected tracebacks on the
smoke workload. That is not material enough for a real span-prune path. The next
useful direction is a top5-scoped traceback certificate, not broader full-output
pruning.

## Goal Prompt

```text
/goal

Create a telemetry/shadow PR that characterizes a tie-complete final-top5
traceback certificate for the GASAL2 top5 artifact path.

Suggested PR title:
  fasim: characterize tie-complete top5 traceback certificate

Base:
  fasim-gasal2-pretraceback-span-prune-shadow after PR #173, or its merge
  result.

Working branch suggestion:
  fasim-gasal2-tie-complete-top5-traceback-certificate

Objective:
  Determine whether GASAL2 traceback work can be physically reduced for the
  top5 artifact contract by processing candidates until all remaining
  candidates are provably unable to change the final retained unique top5 rows.

  This is a top5-only certificate. It is not a full lite-output or full
  TFOsorted-output pruning mechanism.

New default-off shadow env:
  FASIM_GASAL2_TOP5_TRACEBACK_CERTIFICATE_SHADOW=1

Do:
  - keep the authority path unchanged
  - run forward score/end for all candidates
  - build global candidate ordering by admissible upper bound
  - physically run filtered traceback batch in shadow
  - convert/filter/dedup the shadow rows with the same top5 row semantics
  - compare against authority top5 rows for score, stability, and nt_score
  - keep complete boundary ties
  - measure actual traceback count and wall-time reduction
  - report unsupported certificate modes explicitly

Do not:
  - change default behavior
  - change scoring, endpoint, CIGAR, traceback, sort, dedup, non-overlap, or
    output semantics
  - promote GASAL2 endpoint/CIGAR/traceback/score/digest as authority
  - claim aligner.Align replacement
  - expand this to full-output pruning
  - implement a real pruning option
  - add fixed score-threshold pruning as the algorithm
  - promote fixed threshold 116 into an algorithm
  - use local per-flush top5 as a global stopping condition
  - drop boundary ties
  - infer stability or nt_score safety from score alone
  - continue span-prune work
  - make span predicate changes
  - prune CIGAR-dependent duplicate/span buckets

Context:
  PR #173 closed the span-prune line:
    authority selected tracebacks = 175,193
    strict span skipped selected  =      22
    skipped fraction              = 0.0126%
    false_prune                   = 0
    full lite / TFOsorted / top5  = clean

    broader cutlength < cLength:
      skipped selected = 51,701
      false_prune      = 11
      missing_rows     = 11

  Decision from #173:
    strict span certificate correctness-clean
    strict span performance immaterial
    broader span predicate rejected
    real span-prune option no-go

  Historical top5 threshold reference:
    FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116
      traceback_requests = 2,441,113
      wall_seconds       = 48.483698
      top5 score/stability/nt_score clean

  fixed threshold 116 is historical oracle reference only. It is not a
  portable algorithm and must not define the certificate.

Certificate model:
  The shadow first computes GASAL2 forward score/end for all selected
  candidates. It then processes candidates by global upper-bound group, from
  highest upper bound to lowest.

  After each processed group:
    - run traceback for that group
    - run existing convert/filter/dedup/top5 row construction
    - update the current final retained unique rows
    - update each supported rank5 boundary

  Stop condition:
    unprocessed_upper_bound < rank5_boundary

  Boundary-tie rule:
    unprocessed_upper_bound == rank5_boundary
      means the boundary tie group is not complete yet.
      Continue processing all candidates tied at the boundary.

  The certificate is valid only for final retained unique rows, not raw
  pre-traceback candidates. High-score candidates may be removed by invalid
  span, filtered_nt, CIGAR-dependent filters, representative selection, or
  final dedup before they contribute to top5.

Ranking contracts:
  The top5 artifact has three checked ranking contracts:
    score
    stability
    nt_score

  Each contract must be certified independently:
    score_certificate_supported
    stability_certificate_supported
    nt_score_certificate_supported

  For score:
    GASAL2 forward score may be used only if it is an admissible upper bound for
    the final score row ordering after convert/filter/dedup.

  For stability:
    Use pruning only if there is an admissible pre-traceback upper bound for
    stability. Otherwise set stability_certificate_supported=false and keep all
    candidates required by that contract.

  For nt_score:
    Use pruning only if there is an admissible pre-traceback upper bound for
    nt_score. Otherwise set nt_score_certificate_supported=false and keep all
    candidates required by that contract.

  The physical traceback set is conservative:
    traceback_set = score_candidates union stability_candidates union nt_score_candidates

  If any mode is unsupported, the conservative candidate set for that mode is
  all authority selected candidates. The shadow may still report a clean result,
  but the decision must say the certificate is not yet material for that mode.

Global ordering requirement:
  Top5 is a global artifact. Do not stop inside a single flush based on a local
  top5 frontier.

  First shadow version should prefer:
    Pass 1:
      collect all selected candidate score/end and lightweight descriptors

    Pass 2:
      build a global upper-bound frontier
      execute filtered traceback batches selected by the certificate

  A streaming frontier can be a later optimization only after the global
  certificate is correct.

Required telemetry:
  baseline_traceback_requests
  certificate_traceback_requests
  tracebacks_skipped
  tracebacks_skipped_fraction

  score_certificate_supported
  stability_certificate_supported
  nt_score_certificate_supported

  score_rank5_boundary
  stability_rank5_boundary
  nt_score_rank5_boundary

  score_boundary_ties
  stability_boundary_ties
  nt_score_boundary_ties

  score_groups_processed
  stability_groups_processed
  nt_score_groups_processed
  boundary_updates

  invalid_after_traceback
  filtered_nt_after_traceback
  dedup_removed_after_traceback

  certificate_pack_seconds
  certificate_traceback_seconds
  certificate_convert_seconds
  certificate_total_seconds
  measured_net_saved_seconds

  false_prune
  missing_top5_rows
  extra_top5_rows

Required result table:
  workload_name
  target
  query
  mode
  workers
  group_target_records
  output_contract
  baseline_traceback_requests
  certificate_traceback_requests
  tracebacks_skipped
  tracebacks_skipped_fraction
  score_certificate_supported
  stability_certificate_supported
  nt_score_certificate_supported
  score_rank5_boundary
  stability_rank5_boundary
  nt_score_rank5_boundary
  score_boundary_ties
  stability_boundary_ties
  nt_score_boundary_ties
  top5_score_equal
  top5_stability_equal
  top5_nt_score_equal
  top5_score_rows_order_equal
  top5_stability_rows_order_equal
  top5_nt_score_rows_order_equal
  false_prune
  missing_top5_rows
  extra_top5_rows
  measured_net_saved_seconds
  wall_speedup_vs_authority
  full_lite_claim
  full_tfosorted_claim
  decision
  notes

Hard gates:
  top5 score rows/order equal
  top5 stability rows/order equal
  top5 nt_score rows/order equal

  all boundary ties retained
  false_prune = 0
  missing_top5_rows = 0
  extra_top5_rows = 0

  score_certificate_supported=true if score pruning is claimed
  stability_certificate_supported=true if stability pruning is claimed
  nt_score_certificate_supported=true if nt_score pruning is claimed

  If a mode is unsupported:
    do not prune that mode
    include all authority selected candidates for that mode
    report certificate_supported=false

  full lite equivalence: not claimed
  full TFOsorted equivalence: not claimed

Expected workloads:
  1. chr22 full plain top5 artifact workload
     Purpose:
       primary comparison against historical 70.15s full plain and 48.48s
       fixed-threshold reference.

  2. chr21 full plain top5 artifact workload if available
     Purpose:
       second material chromosome so the certificate is not chr22-only.

  3. chr22 slice smoke
     Purpose:
       deterministic parser/smoke fixture only; not the main decision row.

Decision criteria:
  strong_go_top5_shadow:
    top5 three-contract rows/order clean
    all supported-mode certificates valid
    boundary ties retained
    false_prune=0
    measured wall saving >= 10%
    certificate_traceback_requests materially lower than baseline

  weak_go_more_characterization_needed:
    top5 clean
    measured saving positive but < 10%, or only one material workload available

  no_go:
    any top5 contract differs
    any false prune
    boundary ties incomplete
    supported-mode upper bound not proven admissible
    measured saving immaterial

Deliverables:
  - docs/fasim_gasal2_tie_complete_top5_traceback_certificate.md
  - docs/fasim_gasal2_tie_complete_top5_traceback_certificate.tsv
  - scripts/summarize_fasim_gasal2_tie_complete_top5_traceback_certificate.py
  - scripts/check_fasim_gasal2_tie_complete_top5_traceback_certificate_parser.sh
  - scripts/check_fasim_gasal2_tie_complete_top5_traceback_certificate_result.sh
  - optional smoke script if the runtime fixture is cheap enough

Suggested Make targets:
  - check-fasim-gasal2-tie-complete-top5-traceback-certificate-parser
  - check-fasim-gasal2-tie-complete-top5-traceback-certificate-result
  - optional:
      check-fasim-gasal2-tie-complete-top5-traceback-certificate-smoke

Minimum documentation requirements:
  The result document must explicitly say:
    no real pruning
    no span predicate changes
    fixed threshold 116 is historical oracle reference only
    full lite equivalence: not claimed
    full TFOsorted equivalence: not claimed

  It must also explain why a raw candidate rank5 threshold is unsound:
    high-score raw candidates can be invalid or deduped after traceback
    lower-score valid retained rows may still enter the final top5
    boundary ties must be processed completely
```

## Implementation Notes For The Next Agent

The main risk is accidentally turning a historical threshold result into an
algorithm. The certificate must be frontier-based:

```text
process candidates until remaining upper bounds cannot affect final top5
```

not threshold-based:

```text
pick a constant score and skip everything below it
```

The first useful implementation can be inefficient internally if it keeps the
authority path unchanged and measures the filtered path in shadow. Correctness
of the certificate is the milestone; runtime polish can follow only after the
top5 contracts are clean.

The shadow must be global across flushes. If memory pressure makes a two-pass
global shadow too expensive, stop and document that as an architecture blocker
instead of falling back to local per-flush top5.
