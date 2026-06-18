# Fasim GASAL2 Pre-Traceback Pruning Eligibility

This checkpoint adds telemetry for GASAL2 traceback attempts after the traceback
rejection taxonomy milestone. It asks which removed attempts can be linked to a
retained representative, and which removals still require CIGAR or final
ordering to decide.

## Scope

Diagnostic env:

```bash
FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1
FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT=/path/to/eligibility.tsv
FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT=100
```

Counters use:

```text
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_*
```

This is telemetry-only. It does not skip traceback, add pruning, change default
behavior, change output semantics, change scoring/thresholds/CIGAR/traceback,
or promote GASAL2 output as authority.

## Data Model

The runtime emits two distinct views:

```text
aggregate counters:
  full-run eligibility counts used for proportions and decisions

capped TSV export:
  bounded examples only; not a source for full-run percentages
```

The implementation maps representatives in the existing GASAL2 conversion path
at task-local sort/filter time. The direct lite/archive path is covered by the
smoke fixture; the non-direct triplex conversion path uses the same conservative
task-local representative model. If a removed row cannot be mapped to a retained
representative, it is classified as sort/representative dependent or unknown.
This is not a global pruning certificate.

## Hashes

All hashes are deterministic FNV-1a derived hex strings.

`request_key_hash` includes:

```text
task_id
scoreinfo_index
target_start
cutlength
score_prepass_score
score_prepass_query_end
score_prepass_ref_end
```

`descriptor_key_hash` includes:

```text
task_id
scoreinfo_index
target_start
cutlength
sw_score
query_begin
query_end
ref_begin
ref_end
```

`final_row_hash` hashes the lite row key produced by `fasim_make_lite_row`.

`cigar_hash` hashes the raw SSW/GASAL2 CIGAR integer vector.

No pointer addresses or container iteration order are hashed.

## Buckets

Duplicate/representative buckets:

```text
exact_request_duplicate
exact_descriptor_duplicate
same_final_row_different_descriptor
cross_flush_exact_duplicate
cigar_dependent_duplicate
representative_selection_dependent
sort_or_dominance_removed
unknown
```

Span buckets:

```text
pretraceback_span_provable
reverse_start_dependent_span
cigar_dependent_span
unknown
```

`exact_request_duplicate`, `exact_descriptor_duplicate`, and
`pretraceback_span_provable` are marked as pre-traceback decidable candidates,
but they are still not used to skip traceback in this PR.

`same_final_row_different_descriptor`, `cigar_dependent_duplicate`,
`representative_selection_dependent`, `sort_or_dominance_removed`, and
`cigar_dependent_span` are not safe for pre-traceback pruning without a separate
proof.

## Parser

Summarize stderr aggregate counters:

```bash
python3 scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py \
  --stderr run.stderr \
  --label smoke
```

Summarize capped TSV examples:

```bash
python3 scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py \
  --eligibility eligibility.tsv \
  --label sample
```

Required summary fields include:

```text
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
```

## Verification

Focused checks:

```bash
make build-fasim-gasal2 \
  FASIM_GASAL2_TARGET=$(pwd)/.tmp/fasim_longtarget_gasal2_direct \
  GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2

make check-fasim-gasal2-pretraceback-pruning-eligibility-parser

make check-fasim-gasal2-pretraceback-pruning-eligibility-smoke \
  GASAL2_DIR=/data/wenyujianData/LongTarget-exact-sim/.tmp/GASAL2 \
  DNA=/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa

python3 -m py_compile \
  scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py

bash -n \
  scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_parser.sh \
  scripts/check_fasim_gasal2_pretraceback_pruning_eligibility_smoke.sh
```

The smoke check compares baseline and telemetry-enabled lite outputs, checks the
top5 score/stability/nt contracts, verifies traceback request counts are
unchanged, and asserts the TSV export is capped.

## Smoke Result

Fixture:

```text
DNA: .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
RNA: H19.fa
mode: lite
direct convert: FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1
column archive probe: FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1
```

Observed output contract:

```text
traceback_requests = 175,193
baseline_rows = 8,291
candidate_rows = 8,291
missing_rows = 0
extra_rows = 0
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
```

Eligibility summary:

```text
eligibility_attempts = 175,193
retained_final_rows = 8,291
removed_attempts = 166,902
mapped_removed_attempts = 1,910
unmapped_removed_attempts = 164,992
unknown_eligibility_attempts = 0
pre_traceback_decidable_attempts = 22,886
post_traceback_only_attempts = 144,016
false_prune_shadow = 0
missing_rows_shadow = 0
extra_rows_shadow = 0
```

Bucket summary:

```text
same_final_row_different_descriptor   1,910
cigar_dependent_duplicate            82,092
sort_or_dominance_removed             1,145
pretraceback_span_provable           22,886
cigar_dependent_span                 58,869
```

Interpretation:

```text
taxonomy is output-inert on the smoke fixture
unknown = 0
most removed attempts are still post-traceback dependent
22,886 span-bound attempts are pretraceback-decidable candidates
no real pruning is enabled
```

## Decision

If exact request or exact descriptor duplicates dominate and a future shadow
simulation proves `false_prune_shadow=0`, `missing_rows_shadow=0`, and
`extra_rows_shadow=0`, the next PR can design a default-off lazy-traceback
shadow.

If most removals remain CIGAR-, representative-, or sort-dependent, keep CPU/GASAL2
traceback as-is for those buckets.

If output changes or unknown remains material, stop and improve telemetry before
any pruning work.
