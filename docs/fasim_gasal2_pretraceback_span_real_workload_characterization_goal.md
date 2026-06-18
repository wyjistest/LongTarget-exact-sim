# Fasim GASAL2 Pre-Traceback Span Real-Workload Characterization Goal

This document is a copy-ready `/goal` prompt for the next narrow GASAL2
milestone after PR #171. It turns the pre-traceback pruning eligibility result
into a real-workload characterization question:

```text
Does the span-bound pre-traceback candidate bucket matter on real workloads,
and can it be proven safe enough to justify a later default-off runtime option?
```

This goal must not enable real pruning. It only characterizes the
`pretraceback_span_provable` opportunity on larger workloads, measures projected
time savings, and checks full-output/top5 contracts.

## Goal Prompt

```text
/goal

Create a docs/script/result PR that characterizes GASAL2 pre-traceback span
pruning eligibility on real workloads.

Base:
  gasal2-pretraceback-pruning-eligibility after PR #171, or its merge result.

Working branch suggestion:
  fasim-gasal2-pretraceback-span-real-workload-characterization

Objective:
  Determine whether the only currently supported pre-traceback candidate bucket,
  pretraceback_span_provable, is large and safe enough on real workloads to
  justify a future default-off runtime pruning option.

Do not:
  - enable real pruning
  - skip traceback at runtime
  - change default behavior
  - change output semantics
  - change scoring, thresholds, endpoint, CIGAR, traceback, merge, sort, or
    non-overlap policy
  - promote GASAL2 endpoint/CIGAR/traceback/score/digest as authority
  - claim full aligner.Align() replacement
  - claim generic pre-traceback dedup is supported
  - prune final_sort_dedup_removed as a whole
  - prune CIGAR-dependent duplicate or span buckets
  - add fixed score-threshold pruning such as a hard-coded 116 rule
  - infer aggregate eligibility rates from capped TSV samples
  - write huge uncapped per-attempt files by default
  - use historical inactive env names unless they still exist in current source

Context:
  PR #170 closed the traceback rejection taxonomy:
    traceback_requests          = 175,193
    retained_emitted           =   8,291
    filtered_nt                =   8,360
    invalid_span_bound         =  25,672
    final_sort_dedup_removed   = 132,870
    unknown                    =       0

  PR #171 split the residual buckets into eligibility classes:
    traceback_requests                       = 175,193
    retained_final_rows                       =   8,291
    pre_traceback_decidable_attempts          =  22,886
    post_traceback_only_attempts              = 144,016
    unknown_eligibility_attempts              =       0
    full_output_safe_candidate_attempts       =       0

  PR #171 bucket result:
    same_final_row_different_descriptor       =   1,910
    cigar_dependent_duplicate                 =  82,092
    sort_or_dominance_removed                 =   1,145
    pretraceback_span_provable                =  22,886
    cigar_dependent_span                      =  58,869

Important interpretation:
  Generic pre-traceback dedup is not supported by current evidence.

  The only concrete candidate is:
    pretraceback_span_provable

  Even that bucket is not yet a runtime pruning proof. It is a candidate for a
  real-workload shadow/characterization pass.

Primary question:
  On real workloads, what fraction of traceback requests and traceback wall time
  is represented by pretraceback_span_provable, and does the normal output path
  remain clean while this candidate set is measured?

Use current env/counter source:
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT=/path/to/examples.tsv
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT=N
  benchmark.fasim_gasal2_pretraceback_pruning_eligibility_*

Use existing timing where available:
  FASIM_TOP5_GASAL2_PHASE_TIMING=1
  benchmark.fasim_gasal2_*
  benchmark.fasim_top5_gasal2_phase_*

Do not add a runtime env such as:
  FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE=1

unless the PR is explicitly changed from characterization to implementation.
That is not the goal here.

Required workloads:
  1. chr22 full plain GASAL2 workload
     Purpose:
       primary real workload; compare with the known 32.44x full plain path.

  2. MALAT1 group32 two-contract workload
     Purpose:
       positive/scoped workload where full output has previously been close or
       equivalent under the two-contract path.

  3. NEAT1 attempt-consumer or equivalent fallback/no-go control
     Purpose:
       control workload where broad path behavior is known to be harder, so the
       report does not overgeneralize chr22/MALAT1 results.

Optional workloads:
  - chr21 full or chr21+chr22 if existing artifacts make this cheap enough.
  - chr22 slice 10m-12m smoke only as a parser/sanity fixture, not as the main
    decision row.

For each workload collect:
  workload_name
  target
  query
  mode
  workers
  group_target_records
  output_mode
  gasal2_runtime_env
  tracebacks_requested
  eligibility_attempts
  retained_final_rows
  removed_attempts
  pretraceback_span_provable
  pretraceback_span_fraction_of_traceback
  pretraceback_span_fraction_of_removed
  post_traceback_only_attempts
  unknown_eligibility_attempts
  mapped_removed_attempts
  unmapped_removed_attempts
  cigar_dependent_duplicate
  cigar_dependent_span
  same_final_row_different_descriptor
  sort_or_dominance_removed
  full_output_safe_candidate_attempts
  false_prune_shadow
  missing_rows_shadow
  extra_rows_shadow
  baseline_lite_rows
  candidate_lite_rows
  full_lite_missing_rows
  full_lite_extra_rows
  baseline_tfosorted_rows
  candidate_tfosorted_rows
  full_tfosorted_missing_rows
  full_tfosorted_extra_rows
  top5_score_equal
  top5_stability_equal
  top5_nt_score_equal
  gasal2_wall_seconds
  gasal2_extend_seconds
  gasal2_convert_seconds
  gasal2_traceback_seconds
  exact_column_seconds
  output_write_seconds
  projected_saved_traceback_requests
  projected_saved_traceback_fraction
  projected_saved_traceback_seconds
  projected_wall_speedup_if_span_pruned
  notes

Timing requirements:
  Request counts are not enough. Estimate projected savings with traceback wall
  weighting.

  If exact per-attempt traceback timing is not available, use the best current
  aggregate approximation and label it clearly:
    projected_saved_traceback_seconds =
      gasal2_traceback_seconds * pretraceback_span_fraction_of_traceback

  If GASAL2 extend time includes both score/end and traceback and cannot be
  split, report:
    timing_split_available=false
    projected_saved_traceback_seconds=unknown

  Do not present request fraction as wall-time saving unless the timing source
  supports that interpretation.

Required result table:
  workload
  tracebacks
  span_candidates
  span_fraction
  projected_saved_seconds
  projected_speedup
  full_lite_clean
  full_tfosorted_clean
  top5_clean
  false_prune_shadow
  unknown
  decision
  notes

Required scripts:
  - scripts/characterize_fasim_gasal2_pretraceback_span_real_workloads.sh
  - scripts/check_fasim_gasal2_pretraceback_span_real_workload_result.sh

Optional helper parser:
  - scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py

Required docs:
  - docs/fasim_gasal2_pretraceback_span_real_workload_characterization.md

Suggested Make targets:
  - characterize-fasim-gasal2-pretraceback-span-real-workloads
  - check-fasim-gasal2-pretraceback-span-real-workload-result

Minimum smoke/check behavior:
  The result check should be lightweight and deterministic. It may use committed
  result TSV/markdown instead of rerunning chr22 full.

  It must assert:
    - required workload rows exist
    - pretraceback_span_provable is present for each row
    - unknown_eligibility_attempts is present for each row
    - false_prune_shadow is present for each row
    - missing_rows_shadow is present for each row
    - extra_rows_shadow is present for each row
    - full_lite_missing_rows and full_lite_extra_rows are present
    - top5_score_equal/top5_stability_equal/top5_nt_score_equal are present
    - projected_saved_traceback_seconds is either numeric or explicitly unknown
      with timing_split_available=false
    - the docs decision does not recommend real pruning unless all gates are met

Run command shape:
  WORK=.tmp/characterize_fasim_gasal2_pretraceback_span_real_workloads \
  BIN=.tmp/fasim_longtarget_gasal2_direct \
  GASAL2_DIR=.tmp/GASAL2 \
  make characterize-fasim-gasal2-pretraceback-span-real-workloads

Use existing artifacts when available:
  - Do not rerun long full-chromosome jobs if local stderr/output artifacts
    already contain the required metrics.
  - If artifacts are reused, record their paths and command provenance.
  - If a required workload cannot be rerun or found, mark that row as missing
    and do not claim a decision for it.

Validation:
  - make check-fasim-gasal2-pretraceback-span-real-workload-result
  - python3 -m py_compile changed Python scripts, if any
  - bash -n changed shell scripts
  - git diff --check
  - changed-file bidi control scan

Decision gates:
  Strong go for next default-off implementation only if every real workload row
  that is meant to support the option satisfies:
    false_prune_shadow = 0
    missing_rows_shadow = 0
    extra_rows_shadow = 0
    full_lite_missing_rows = 0
    full_lite_extra_rows = 0
    full_tfosorted_missing_rows = 0
    full_tfosorted_extra_rows = 0
    top5_score_equal = true
    top5_stability_equal = true
    top5_nt_score_equal = true
    unknown_eligibility_attempts = 0
    projected_saved_traceback_seconds is material

  Weak go if:
    all correctness gates are clean, but projected saving is small or workload
    specific. The next PR may document guidance, but should not add runtime
    pruning yet.

  No-go if:
    any full output or top5 contract changes,
    false_prune_shadow is nonzero,
    unknown_eligibility_attempts is nonzero in the candidate bucket,
    timing cannot support a meaningful projected saving,
    or span candidates are too small to matter.

Expected conclusion format:
  - generic pre-traceback dedup:
      unsupported by #171 and not pursued here
  - span-bound prefilter:
      characterized on real workloads
  - CIGAR/representative/sort-dependent removals:
      keep traceback
  - next step:
      either default-off span prune implementation with validation, or stop as
      a research checkpoint
```

## Execution Contract

This is a goal document for implementation, not just a writing task. A Codex
run that accepts this goal should produce a narrow docs/script/result PR. The PR
is complete only when the repository contains the result doc, scripts, Make
targets, committed characterization table, and validation checks described
below.

The implementation must stay telemetry-only:

```text
allowed:
  parse existing benchmark counters
  run or reuse workload artifacts
  emit bounded result TSV/markdown
  compute projected span-prune opportunity
  validate output/top5 contracts
  document weak/no-go decisions honestly

forbidden:
  skip traceback
  add real pruning envs
  change C++ runtime behavior for normal runs
  change GASAL2 scoring/CIGAR/traceback authority
  hide missing workload rows behind a positive decision
```

## Required File Responsibilities

Create or modify these files only as needed:

```text
scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py
  Parse stderr benchmark lines and optional comparison summaries into one
  normalized TSV row per workload. Compute span fractions and projected savings
  only from aggregate counters, never from capped per-attempt exports.

scripts/characterize_fasim_gasal2_pretraceback_span_real_workloads.sh
  Build/reuse the GASAL2-enabled Fasim binary, run or reuse the required
  workload artifacts, call the summarizer, and write a stable result TSV under
  the configured WORK directory. It may skip long reruns if required artifacts
  are absent, but the row must be marked missing and non-decisive.

scripts/check_fasim_gasal2_pretraceback_span_real_workload_result.sh
  Validate the committed result TSV and markdown. It should be lightweight and
  deterministic; it must not rerun full chr22.

docs/fasim_gasal2_pretraceback_span_real_workload_characterization.md
  Record scope, artifact provenance, result table, decision gates, conclusion,
  and next-step recommendation. It must clearly state that no real pruning is
  enabled by this PR.

Makefile
  Add only focused targets for this milestone near the existing #170/#171
  GASAL2 traceback taxonomy targets.
```

Do not fold unrelated GASAL2 WIP, archive compression work, or previous main
checkout changes into this PR.

## Result TSV Contract

The committed or generated TSV must include one row for each required workload:

```text
chr22_full_plain
malat1_group32_two_contract
neat1_attempt_consumer_control
```

If a workload could not be run and no artifact has the required telemetry, keep
the row and set:

```text
status=missing
decision=no_decision
notes=<specific missing input/artifact/counter>
```

Do not omit a required workload row just because it is expensive.

The TSV header must include at least:

```text
workload_name
status
decision
target
query
mode
workers
group_target_records
output_mode
tracebacks_requested
eligibility_attempts
retained_final_rows
removed_attempts
pretraceback_span_provable
pretraceback_span_fraction_of_traceback
pretraceback_span_fraction_of_removed
post_traceback_only_attempts
unknown_eligibility_attempts
mapped_removed_attempts
unmapped_removed_attempts
cigar_dependent_duplicate
cigar_dependent_span
same_final_row_different_descriptor
sort_or_dominance_removed
full_output_safe_candidate_attempts
false_prune_shadow
missing_rows_shadow
extra_rows_shadow
baseline_lite_rows
candidate_lite_rows
full_lite_missing_rows
full_lite_extra_rows
baseline_tfosorted_rows
candidate_tfosorted_rows
full_tfosorted_missing_rows
full_tfosorted_extra_rows
top5_score_equal
top5_stability_equal
top5_nt_score_equal
timing_split_available
gasal2_wall_seconds
gasal2_extend_seconds
gasal2_convert_seconds
gasal2_traceback_seconds
exact_column_seconds
output_write_seconds
projected_saved_traceback_requests
projected_saved_traceback_fraction
projected_saved_traceback_seconds
projected_wall_speedup_if_span_pruned
artifact_provenance
notes
```

For numeric fields that are not available, use `unknown`, not an empty field.
For boolean fields, use `true`, `false`, or `unknown`.

## Summarizer Requirements

The summarizer should accept explicit file paths rather than hard-coding `.tmp`
locations. A practical CLI shape is:

```bash
python3 scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py \
  --workload-name chr22_full_plain \
  --status complete \
  --stderr "$WORK/chr22/stderr.log" \
  --top5-summary "$WORK/chr22/top5.summary" \
  --full-lite-summary "$WORK/chr22/full_lite.summary" \
  --tfosorted-summary "$WORK/chr22/tfosorted.summary" \
  --artifact-provenance "$WORK/chr22" \
  --output "$WORK/chr22.row.tsv"
```

It should parse existing benchmark names first:

```text
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_*
benchmark.fasim_gasal2_*
benchmark.fasim_top5_gasal2_phase_*
```

It must fail closed if required telemetry is partially present. For example, if
`pretraceback_span_provable` exists but `traceback_requests` is absent, the row
must be `status=incomplete` or the script must exit nonzero with a clear error.

Projection math:

```text
span_fraction_of_traceback =
  pretraceback_span_provable / tracebacks_requested

span_fraction_of_removed =
  pretraceback_span_provable / removed_attempts

projected_saved_traceback_requests =
  pretraceback_span_provable

projected_saved_traceback_fraction =
  span_fraction_of_traceback
```

Only compute `projected_saved_traceback_seconds` when traceback-specific timing
is available. If only inclusive GASAL2 extend timing is available, write:

```text
timing_split_available=false
projected_saved_traceback_seconds=unknown
projected_wall_speedup_if_span_pruned=unknown
notes=traceback timing not split from extend
```

## Characterization Script Requirements

The characterization script should be restartable and artifact-aware:

```bash
WORK=${WORK:-.tmp/characterize_fasim_gasal2_pretraceback_span_real_workloads}
BIN=${BIN:-.tmp/fasim_longtarget_gasal2_direct}
GASAL2_DIR=${GASAL2_DIR:-.tmp/GASAL2}
```

For each required workload it should:

```text
1. create a stable subdirectory under WORK
2. locate existing artifacts or run the workload if inputs are available
3. enable only diagnostic telemetry envs
4. keep per-attempt export capped
5. collect stderr and output comparison summaries
6. call the summarizer to generate one TSV row
7. concatenate rows into WORK/pretraceback_span_real_workloads.tsv
8. print the final TSV path
```

The script may reuse local artifacts only if they contain the #171 eligibility
benchmark counters. Older GASAL2 speed artifacts without those counters are
context only and must not be counted as complete rows.

## Result Check Requirements

The check script must validate the result, not the user's local machine. It
should pass in a clean checkout after the PR lands.

It must assert:

```text
required TSV columns exist
all three required workload rows exist
missing rows have decision=no_decision
complete rows have numeric tracebacks_requested
complete rows have numeric pretraceback_span_provable
complete rows have unknown_eligibility_attempts present
complete rows have false_prune_shadow/missing_rows_shadow/extra_rows_shadow
complete rows have full lite and TFOsorted missing/extra fields
complete rows have top5 score/stability/nt_score fields
numeric projected seconds are used only when timing_split_available=true
unknown projected seconds require timing_split_available=false
docs do not recommend real pruning unless all correctness gates are clean
docs mention generic dedup is unsupported
docs mention CIGAR/representative/sort-dependent buckets keep traceback
```

The check script should reject accidental overclaiming strings such as:

```text
real pruning enabled
safe to prune all final_sort_dedup_removed
generic pre-traceback dedup supported
GASAL2 replaces aligner.Align
```

unless they are explicitly negated in a non-goal sentence.

## Result Document Requirements

The result document must include:

```text
scope and non-goals
relationship to PR #170 and PR #171
artifact provenance for every row
required workload table
timing-source caveat
correctness gate table
decision table
next-step recommendation
```

The conclusion must use one of these decision labels:

```text
strong_go_for_default_off_span_prune_shadow
weak_go_more_characterization_needed
no_go_span_bucket_not_material
no_decision_missing_real_workload_data
```

If the decision is strong go, the document must still say the next PR is
default-off and validation-first. This PR must not implement that option.

## Suggested Implementation Steps

Use an isolated worktree based on PR #171:

```bash
git worktree add \
  .worktrees/fasim-gasal2-pretraceback-span-real-workload-characterization \
  fasim-gasal2-pretraceback-pruning-eligibility

cd .worktrees/fasim-gasal2-pretraceback-span-real-workload-characterization
git switch -c fasim-gasal2-pretraceback-span-real-workload-characterization
```

Then execute in small commits:

```text
1. add summarizer parser and parser-focused fixture/check
2. add characterization shell script
3. add result TSV and result markdown from available artifacts/runs
4. add Make targets and lightweight result check
5. run validation and commit
```

Keep the PR narrow. A good final diff should look like:

```text
Makefile
docs/fasim_gasal2_pretraceback_span_real_workload_characterization.md
docs/fasim_gasal2_pretraceback_span_real_workload_characterization_goal.md
scripts/characterize_fasim_gasal2_pretraceback_span_real_workloads.sh
scripts/check_fasim_gasal2_pretraceback_span_real_workload_result.sh
scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py
optional committed result TSV under docs/ or scripts/fixtures/
```

## Completion Audit

Before marking the goal complete, verify:

```text
deliverables exist:
  scripts/characterize_fasim_gasal2_pretraceback_span_real_workloads.sh
  scripts/check_fasim_gasal2_pretraceback_span_real_workload_result.sh
  docs/fasim_gasal2_pretraceback_span_real_workload_characterization.md

if the optional Python summarizer exists:
  python3 -m py_compile scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py

shell scripts parse:
  bash -n scripts/characterize_fasim_gasal2_pretraceback_span_real_workloads.sh
  bash -n scripts/check_fasim_gasal2_pretraceback_span_real_workload_result.sh

Make target passes:
  make check-fasim-gasal2-pretraceback-span-real-workload-result

repo hygiene passes:
  git diff --check
  changed-file bidi control scan

scope audit passes:
  no real pruning env was added
  no traceback skip path was added
  no output/scoring/CIGAR/sort semantics changed
  no uncapped per-attempt export is default
  required workload rows are present or explicitly missing with no_decision
```

Only mark the goal complete after the branch is committed and, if requested for
the milestone, pushed with a PR opened against the PR #171 branch or its merge
result.

## Review Notes For The Next Agent

This goal follows the #171 boundary:

```text
taxonomy complete
generic pre-traceback dedup not supported
only pretraceback_span_provable remains as a narrow candidate
```

The next PR should be a result checkpoint, not a runtime optimization PR. The
important output is a real-workload table that says whether span-bound pruning
is worth implementing later.

## Suggested PR Title

```text
fasim: characterize GASAL2 pre-traceback span pruning on real workloads
```

## Suggested Commit Message

```text
fasim: characterize GASAL2 pre-traceback span pruning
```
