# Fasim GASAL2 Traceback Rejection Taxonomy Goal

This document is a copy-ready `/goal` prompt for the next Codex run. It is
intended to create a telemetry-only milestone that explains where GASAL2
traceback work is rejected after execution.

## Goal Prompt

```text
/goal

Create a telemetry-only PR that characterizes GASAL2 traceback rejection
taxonomy for the current top5-focused GASAL2 path.

Base:
  current LongTarget-exact-sim workspace after the GASAL2 limited-traceback /
  dynamic traceback frontier characterization work.

Objective:
  Explain why millions of GASAL2 traceback attempts produce only hundreds of
  thousands of final .lite rows, without changing runtime behavior.

Working branch suggestion:
  fasim-gasal2-traceback-rejection-taxonomy

Do not:
  - change output semantics
  - change default behavior
  - add new pruning
  - skip any traceback at runtime
  - promote GASAL2 endpoint/CIGAR/traceback/score/digest as authority
  - claim full aligner.Align() replacement
  - claim full .lite/TFOsorted equivalence from top5-only evidence
  - reuse historical inactive env names unless they still exist in current source
  - write huge uncapped TSV files by default

Current evidence:
  chr22 full CPU vs GASAL2 full plain .lite:
    cpu_wall_seconds = 2275.937806
    gasal2_wall_seconds = 70.154883
    run_wall_speedup = 32.441616
    gasal2_requests = 21,802,059
    gasal2_traceback_requests = 6,910,419
    output lite rows = 388,821
    top5_score_equal = true
    top5_stability_equal = true
    top5_nt_score_equal = true
    full_rows_equal = false

  phase timing:
    flush_total_seconds = 64.488200
    gasal2_extend_wall_seconds = 40.421600
    exact_column_wall_seconds = 11.532200
    gasal2_convert_wall_seconds = 8.354580
    output_write_seconds = 0.568368

  current best simple top5-only threshold:
    FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116
    chr22 full wall_seconds = 48.483698
    traceback_requests = 2,441,113
    top5_score_equal = true
    top5_stability_equal = true
    top5_nt_score_equal = true

  known boundary:
    threshold 117 or score-band rescue can fail top5_stability.
    Simple score/proxy/overlap rules are not selective enough.

Primary question:
  For each traceback attempt, where does it die?

Use current naming style:
  env prefix:
    FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY=1
    FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT=/path/to/sample.tsv
    FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT_LIMIT=N

  benchmark prefix:
    benchmark.fasim_gasal2_traceback_rejection_taxonomy_*

  existing telemetry context:
    FASIM_TOP5_GASAL2_PHASE_TIMING=1
    benchmark.fasim_gasal2_*
    benchmark.fasim_top5_gasal2_phase_*

Track the funnel:
  1. GASAL2 request
  2. score/prealign candidate
  3. traceback attempt
  4. selected alignment / raw triplex
  5. converted triplex candidate
  6. emitted .lite row before final sort/dedup
  7. final sorted/dedup row

Classify rejection reasons:
  - below score/minScore threshold
  - not selected by scoreInfo/prealign policy
  - invalid or insufficient span bound
  - exact CIGAR/query span/ref span/nt below threshold
  - identity below threshold
  - stability below threshold
  - duplicate descriptor or duplicate row
  - dominated by final sort/dedup/non-overlap policy
  - rank/frontier dominated for top5-scoped contract
  - retained/emitted
  - unknown

For every bucket, also label whether the reason is:
  pre_traceback_decidable
  post_traceback_only
  contract_specific_top5_only
  full_output_required

Suggested bucket IDs:
  retained_emitted
  filtered_score
  filtered_identity
  filtered_stability
  filtered_nt
  invalid_span_bound
  duplicate_descriptor
  duplicate_row
  final_sort_dedup_removed
  final_nonoverlap_dominated
  top5_frontier_dominated
  post_cigar_only
  unknown

Required aggregate counters:
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_requested
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_active
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_attempts
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_retained_emitted
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_score
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_identity
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_stability
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_nt
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_invalid_span_bound
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_duplicate_descriptor
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_duplicate_row
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_final_sort_dedup_removed
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_final_nonoverlap_dominated
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_top5_frontier_dominated
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_post_cigar_only
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_unknown
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_path
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_rows
  benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_truncated

The exact bucket list may be refined while reading the current conversion code,
but the PR must document any mapping changes and keep parser output stable.

Suggested TSV export columns:
  attempt_id
  task_id
  scoreinfo_index
  prealign_score
  target_size
  decision_bucket
  pre_traceback_decidable
  post_traceback_only
  top5_only_safe_candidate
  full_output_safe_candidate
  emitted_row
  final_row
  output_global_start
  output_global_end
  score
  nt
  identity
  stability
  notes

The export is diagnostic only. It must be capped by default. A small smoke
fixture should set a low export limit and assert truncation behavior if the
fixture exceeds the cap.

Deliverables:
  1. Runtime telemetry counters, default-on only when existing GASAL2 phase
     timing/debug telemetry is requested, or guarded by a new explicit
     diagnostic env.
  2. Optional TSV sample/export for rejected traceback attempts, capped or
     bounded so chr22 does not create huge files by default.
  3. Parser/summarizer script that converts counters/TSV into a compact table.
  4. Smoke test using a small fixture.
  5. Docs checkpoint:
       docs/fasim_gasal2_traceback_rejection_taxonomy.md

Concrete file names:
  - scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py
  - scripts/check_fasim_gasal2_traceback_rejection_taxonomy_parser.sh
  - scripts/check_fasim_gasal2_traceback_rejection_taxonomy_smoke.sh
  - docs/fasim_gasal2_traceback_rejection_taxonomy.md

Suggested Make targets:
  - check-fasim-gasal2-traceback-rejection-taxonomy-parser
  - check-fasim-gasal2-traceback-rejection-taxonomy-smoke

Required report table:
  bucket
  attempts
  fraction_of_traceback_attempts
  fraction_of_gasal2_requests
  pre_traceback_decidable
  post_traceback_only
  top5_only_safe_candidate
  full_output_safe_candidate
  notes

Required summary output fields:
  taxonomy_attempts
  taxonomy_known_attempts
  taxonomy_unknown_attempts
  pre_traceback_decidable_attempts
  post_traceback_only_attempts
  top5_only_safe_candidate_attempts
  full_output_safe_candidate_attempts
  emitted_attempts
  rejected_attempts
  unknown_fraction

Required workload rows if feasible:
  - chr22 slice 10m-12m
  - chr22 full using existing result artifacts if available
  - optional chr21+chr22 only if runtime is acceptable

Minimum smoke behavior:
  - Build GASAL2 binary if needed.
  - Run a small chr22/H19 fixture with:
      FASIM_TOP5_GASAL2_PHASE_TIMING=1
      FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY=1
      FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT=$WORK/taxonomy.tsv
      FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT_LIMIT=100
  - Run the same fixture without taxonomy enabled.
  - Assert top5_score/top5_stability/top5_nt_score remain equal.
  - If full row equality is expected for the fixture, assert it; otherwise
    report full row diff as context only.
  - Assert taxonomy counters are present and active.
  - Assert export file exists, has the documented header, and does not exceed
    the configured limit plus header.

Characterization command shape:
  WORK=.tmp/characterize_fasim_gasal2_traceback_rejection_taxonomy_chr22 \
  TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
  BIN=.tmp/fasim_longtarget_gasal2_direct \
  make check-fasim-gasal2-traceback-rejection-taxonomy-smoke

Use existing result artifacts where possible. Do not rerun full chr22 unless the
current workspace lacks sufficient telemetry or the user explicitly asks for a
fresh long run.

Testing:
  - parser test for taxonomy summary
  - smoke test proving telemetry is emitted and behavior/output remains unchanged
  - make check-fasim-gasal2-traceback-rejection-taxonomy-parser
  - make check-fasim-gasal2-traceback-rejection-taxonomy-smoke
  - py_compile changed Python scripts
  - bash -n changed shell scripts
  - git diff --check
  - changed-file bidi scan

Decision:
  If most rejected traceback attempts fall into pre_traceback_decidable buckets:
    next PR = lazy traceback shadow with CPU/full-output authority.

  If most rejection depends on CIGAR/stability/final output state:
    do not attempt full-output lazy traceback; keep top5-only exploration separate.

  If top5-only frontier dominated buckets are large:
    next PR may design a top5 exact-certificate mode, still default-off.

  If taxonomy is ambiguous or unknown remains high:
    stop and add narrower instrumentation before pruning.

Completion audit before marking the goal complete:
  - docs/fasim_gasal2_traceback_rejection_taxonomy.md exists and states scope,
    non-goals, contract split, telemetry prefix, result table, and decision.
  - Parser test passes.
  - Smoke test passes and proves no behavior/output change for its fixture.
  - New counters are present in both GASAL2 build and stub/non-GASAL2 paths where
    existing telemetry conventions require stub output.
  - Export is bounded and cannot create chr22-scale huge files by default.
  - Unknown bucket is reported explicitly, not silently omitted.
  - Final response clearly says whether the PR is telemetry-only and whether it
    justifies lazy traceback as a next step.
```

## Scope Notes

This goal is deliberately not a performance optimization PR. It is a
measurement PR. The output of this milestone should be a defensible table that
answers whether traceback reduction can be made safe, and under which contract.

Two contracts must remain separate:

```text
full-output contract:
  full .lite / TFOsorted rows and digest must match CPU authority

top5-scoped contract:
  top5_score / top5_stability / top5_nt_score must match
  full rows may drift only when explicitly accepted by that scoped path
```

The current `116` threshold is a useful top5-scoped checkpoint, not a general
proof. This taxonomy goal exists because fixed score thresholds and simple
score-band rescue have already hit the stability boundary.

## Implementation Hints

The next Codex run should read the current conversion and emit path before
choosing exact hook points. Likely useful locations include the GASAL2 bridge
stats path, the direct GASAL2 conversion code, and the existing
`benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_*` counters. Existing
attempt-export analyzers are useful patterns:

```text
scripts/analyze_fasim_gasal2_limited_traceback_attempt_export.py
scripts/analyze_fasim_gasal2_stability_risk_attempts.py
scripts/analyze_fasim_gasal2_stability_proxy_rule_sweep.py
```

Do not count inclusive timers as exclusive time. If the taxonomy document uses
phase timing, it should state whether counters are inclusive, exclusive, or just
funnel counts.

## Suggested Parser Fixture

The parser test can be independent of the C++ runtime. A tiny TSV with five rows
is enough:

```text
attempt_id  decision_bucket        pre_traceback_decidable  post_traceback_only
1           retained_emitted       0                        0
2           filtered_nt            0                        1
3           filtered_score         1                        0
4           final_sort_dedup_removed 0                      1
5           unknown                0                        0
```

The expected parser output should include:

```text
taxonomy_attempts=5
taxonomy_unknown_attempts=1
pre_traceback_decidable_attempts=1
post_traceback_only_attempts=2
bucket filtered_nt attempts=1
bucket unknown attempts=1
```

## Expected Outcome

The best result is not necessarily a speedup. The best result is a clear
decision:

```text
lazy traceback is worth prototyping
```

or:

```text
traceback rejection is mostly post-CIGAR/post-output-state, so further pruning
requires a top5-specific certificate or should stop.
```
