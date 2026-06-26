# GASAL2 Flush Extracted Finalizer Real Opt-In

This checkpoint turns the same-result dual-finalizer proof into a
default-off synchronous real path for the ordinary triplex finalizer shape.
It does not add threads, queues, a second slot, an asynchronous archive
writer, or new CUDA synchronization.

## Runtime Switches

```bash
FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER=1
FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE=1
```

`FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER=1` enables the extracted
flush-local finalizer as the committed path when the flush shape is
supported.

`FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE=1` only becomes active
when the real opt-in is also enabled. Validate mode runs the legacy
finalizer side path on the same `FlushGpuResult`, compares it against the
extracted finalizer, commits extracted rows on a clean comparison, and
falls back to legacy rows on mismatch.

## Supported Shape

Supported:

```text
owned FlushGpuResult
ordinary triplex finalizer
flush-local extracted rows
synchronous ordered commit
```

Unsupported shapes fail closed to the legacy finalizer:

```text
direct lite/archive-first finalizer
phase3 real CIGAR/Nt prefilter side effects
phase3 shadow side effects
taxonomy exporter side effects
pretraceback eligibility exporter side effects
missing FlushGpuResult
```

## Telemetry

The real opt-in automatically enables result-boundary and ordered-commit
telemetry because those are the ownership and commit boundaries that make
the path safe to characterize.

Required metrics:

```text
benchmark.fasim_gasal2_extracted_finalizer_requested
benchmark.fasim_gasal2_extracted_finalizer_active
benchmark.fasim_gasal2_extracted_finalizer_validate_requested
benchmark.fasim_gasal2_extracted_finalizer_validate_active
benchmark.fasim_gasal2_extracted_finalizer_disabled_reason
benchmark.fasim_gasal2_extracted_finalizer_result_boundary_ready_flushes
benchmark.fasim_gasal2_extracted_finalizer_flushes_observed
benchmark.fasim_gasal2_extracted_finalizer_eligible_flushes
benchmark.fasim_gasal2_extracted_finalizer_committed_flushes
benchmark.fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes
benchmark.fasim_gasal2_extracted_finalizer_legacy_fallback_flushes
benchmark.fasim_gasal2_extracted_finalizer_legacy_finalizer_executed
benchmark.fasim_gasal2_extracted_finalizer_extracted_finalizer_executed
benchmark.fasim_gasal2_extracted_finalizer_comparison_performed
benchmark.fasim_gasal2_extracted_finalizer_extracted_active_flushes
benchmark.fasim_gasal2_extracted_finalizer_legacy_rows
benchmark.fasim_gasal2_extracted_finalizer_extracted_rows
benchmark.fasim_gasal2_extracted_finalizer_committed_rows
benchmark.fasim_gasal2_extracted_finalizer_missing_rows
benchmark.fasim_gasal2_extracted_finalizer_extra_rows
benchmark.fasim_gasal2_extracted_finalizer_order_mismatches
benchmark.fasim_gasal2_extracted_finalizer_cigar_mismatches
benchmark.fasim_gasal2_extracted_finalizer_coordinate_mismatches
benchmark.fasim_gasal2_extracted_finalizer_counter_mismatches
benchmark.fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches
benchmark.fasim_gasal2_extracted_finalizer_legacy_seconds
benchmark.fasim_gasal2_extracted_finalizer_extracted_seconds
benchmark.fasim_gasal2_extracted_finalizer_compare_seconds
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_flush_id
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_task_id
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_row_index
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_field
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_legacy_row
benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_extracted_row
benchmark.fasim_gasal2_extracted_finalizer_decision
```

Expected clean decision:

```text
decision=real_extracted_active_clean_no_fallback
```

Decision values are intentionally specific:

```text
real_extracted_active_clean_no_fallback
real_extracted_active_with_legacy_fallback
validate_mismatch_fallback
unsupported_shape_legacy_fallback
not_requested
```

In non-validate mode, `legacy_rows=0` means the legacy finalizer was not
executed. Use these fields to disambiguate execution from row counts:

```text
legacy_finalizer_executed=0
comparison_performed=0
```

Validate mode should report:

```text
legacy_finalizer_executed>0
comparison_performed>0
```

Validate-only without the real opt-in must report:

```text
requested=0
active=0
validate_requested=1
validate_active=0
decision=not_requested
```

## Hard Gates

Small smoke:

```text
Lite byte-equal
missing / extra = 0
order mismatch = 0
CIGAR mismatch = 0
coordinate mismatch = 0
counter mismatch = 0
archive descriptor mismatch = 0
fallback = 0 for supported ordinary triplex shape
unsupported = 0 for supported ordinary triplex shape
```

The validation target is:

```bash
make check-fasim-gasal2-flush-extracted-finalizer-smoke
```

## chr22 Characterization

The full chr22 characterization should run sequentially on one GPU:

```bash
make characterize-fasim-gasal2-flush-extracted-finalizer-chr22
make check-fasim-gasal2-flush-extracted-finalizer-chr22-result
```

It runs:

```text
legacy baseline
extracted finalizer
extracted + validate
```

Default repeats are three per case. Validate mode is a correctness audit
and should not be used for performance claims.

The required interpretation is:

```text
extracted non-validate overhead < 1-2% against legacy median
validate same-result comparison clean
unsupported/fallback flushes = 0 for ordinary triplex shape
top5 score / stability / Nt-score equal against legacy
```

Because full-run byte-level nondeterminism has been observed, the strongest
correctness evidence remains the validate-mode same-`FlushGpuResult`
comparison. Independent-run byte equality is recorded but is not the sole
gate.
