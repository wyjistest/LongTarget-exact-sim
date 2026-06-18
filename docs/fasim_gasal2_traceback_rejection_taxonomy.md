# Fasim GASAL2 Traceback Rejection Taxonomy

This checkpoint adds telemetry for the current top5-focused GASAL2 path. It
answers where GASAL2 traceback work is rejected after execution without changing
runtime behavior.

## Scope

Added diagnostic env:

```bash
FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY=1
FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT=/path/to/taxonomy.tsv
FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT_LIMIT=100
```

The emitted counters use:

```text
benchmark.fasim_gasal2_traceback_rejection_taxonomy_*
```

This is telemetry-only. It does not skip traceback, add pruning, change output
semantics, change default behavior, or promote GASAL2 endpoint/CIGAR/traceback
as output authority.

## Bucket Model

The runtime classifier has two views:

```text
aggregate counters:
  conservative bucket counts derived from existing GASAL2 conversion funnel
  counters.

capped TSV export:
  sampled per-traceback-attempt rows from the conversion loop with task id,
  scoreInfo index, score, target size, bucket, and row metrics when available.
```

It is intentionally not a proof of safe pruning.

Current mutually budgeted buckets:

```text
retained_emitted
filtered_score
filtered_identity
filtered_stability
filtered_nt
invalid_span_bound
final_sort_dedup_removed
post_cigar_only
unknown
```

Reserved zero buckets are also printed for stable parser output:

```text
duplicate_descriptor
duplicate_row
final_nonoverlap_dominated
top5_frontier_dominated
```

Filter counters can overlap in the raw emit path, so the taxonomy assigns them
with a fixed priority to keep bucket totals bounded by traceback attempts. The
mapping is diagnostic and must not be used as a pruning contract without a
separate correctness proof.

The capped TSV export records attempt-level observations before final global
sort/dedup authority is applied. `emitted_row=1` means the attempt produced a row
that passed local emit thresholds. `final_row` is not used as a final global
authority in the TSV sample; use aggregate counters and output comparison for
final-row claims.

## Parser

The summarizer accepts either a capped TSV export or stderr counters:

```bash
python3 scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py \
  --stderr run.stderr \
  --label chr22-slice

python3 scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py \
  --taxonomy taxonomy.tsv \
  --label sample
```

It emits required summary fields:

```text
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
```

and a compact bucket table with traceback/request fractions.

## Smoke Result

Command:

```bash
make check-fasim-gasal2-traceback-rejection-taxonomy-smoke
```

Fixture:

```text
DNA: .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
RNA: H19.fa
mode: lite
```

Observed smoke output:

```text
traceback_requests = 175,193
baseline_rows = 8,291
candidate_rows = 8,291
missing_rows = 0
extra_rows = 0
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
taxonomy_attempts = 175,193
taxonomy_unknown_attempts = 0
taxonomy export lines = 26 with EXPORT_LIMIT=25
```

Bucket summary:

```text
retained_emitted          8,291
filtered_nt               8,360
invalid_span_bound       25,672
final_sort_dedup_removed 132,870
```

The taxonomy env did not change `benchmark.fasim_gasal2_traceback_requests` in
the smoke fixture. The export was capped and contained real per-attempt
`task_id` / `scoreinfo_index` rows rather than aggregate synthetic bucket rows.

## Interpretation

The smoke fixture shows that most executed traceback work is rejected after CIGAR
materialization and row sorting/dedup, not by file output. This supports the next
research question:

```text
Can any rejection reason be moved before traceback while preserving the selected
contract?
```

That is not answered by this PR. Full-output and top5-scoped contracts must
remain separate:

```text
Full-output mode:
  requires full .lite/TFOsorted row equality before pruning can be enabled.

Top5-scoped mode:
  may use a narrower top5 contract, but needs its own dynamic frontier/tie proof.
```

## Verification

Focused checks:

```bash
make check-fasim-gasal2-traceback-rejection-taxonomy-parser
make check-fasim-gasal2-traceback-rejection-taxonomy-smoke
python3 -m py_compile scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py
bash -n scripts/check_fasim_gasal2_traceback_rejection_taxonomy_parser.sh \
  scripts/check_fasim_gasal2_traceback_rejection_taxonomy_smoke.sh
```
