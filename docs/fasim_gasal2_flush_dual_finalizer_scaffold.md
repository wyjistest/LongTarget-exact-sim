# Fasim GASAL2 Flush Dual Finalizer Shadow

## Scope

This checkpoint adds default-off telemetry for the same-result dual finalizer
shadow:

```bash
FASIM_GASAL2_FLUSH_DUAL_FINALIZER_SHADOW=1
```

It does not run GASAL2 twice. It does not add worker threads, queues, double
buffering, new CUDA streams, or new output paths.

Requesting this shadow also enables the owned `FlushGpuResult` and ordered
commit telemetry, because the comparison uses one immutable GPU result and one
ordered commit boundary.

## Current State

The comparison is now active for the normal triplex finalizer path:

```text
same FlushGpuResult
  legacy finalizer + real commit authority
  extracted side-effect-free triplex finalize shadow
  in-memory FlushFinalizedRows comparison
```

The shadow finalizer rebuilds flush-local precommit rows from the same owned
`FlushGpuResult`. It does not write output files, call the real archive writer,
mutate global counters, update cross-flush state, or run GASAL2 again.

Direct lite/archive-first finalizer shapes remain conservative and are reported
as unsupported:

```text
disabled_reason=unsupported_finalizer_shape
decision=go_extract_unsupported_finalizer_shape_next
```

Expected decision for the supported normal triplex path when clean:

```text
disabled_reason=none
decision=go_real_ordered_commit_opt_in_next
```

This is still a shadow checkpoint. The real output path remains the legacy
authority path.

## Metrics

When requested, stderr reports:

```text
benchmark.fasim_gasal2_dual_finalizer_requested
benchmark.fasim_gasal2_dual_finalizer_active
benchmark.fasim_gasal2_dual_finalizer_disabled_reason
benchmark.fasim_gasal2_dual_finalizer_result_boundary_ready_flushes
benchmark.fasim_gasal2_dual_finalizer_flushes_observed
benchmark.fasim_gasal2_dual_finalizer_flushes_compared
benchmark.fasim_gasal2_dual_finalizer_unsupported_flushes
benchmark.fasim_gasal2_dual_finalizer_legacy_rows
benchmark.fasim_gasal2_dual_finalizer_extracted_rows
benchmark.fasim_gasal2_dual_finalizer_missing_rows
benchmark.fasim_gasal2_dual_finalizer_extra_rows
benchmark.fasim_gasal2_dual_finalizer_order_mismatches
benchmark.fasim_gasal2_dual_finalizer_cigar_mismatches
benchmark.fasim_gasal2_dual_finalizer_coordinate_mismatches
benchmark.fasim_gasal2_dual_finalizer_counter_mismatches
benchmark.fasim_gasal2_dual_finalizer_archive_descriptor_mismatches
benchmark.fasim_gasal2_dual_finalizer_legacy_seconds
benchmark.fasim_gasal2_dual_finalizer_extracted_seconds
benchmark.fasim_gasal2_dual_finalizer_compare_seconds
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_flush_id
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_task_id
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_row_index
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_field
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_legacy_row
benchmark.fasim_gasal2_dual_finalizer_first_mismatch_extracted_row
benchmark.fasim_gasal2_dual_finalizer_decision
```

## FlushFinalizedRows

The shadow materializes a flush-local result object:

```text
FasimGasal2FlushFinalizedRows
  flush_id
  precommit_rows
  task_row_offsets
  task_row_counts
  ordered_rows_digest
  row_multiset_digest
  cigar_digest
  coordinate_digest
  owned_bytes
```

The comparison contract covers:

```text
row count
ordered row digest
row multiset digest
CIGAR digest
coordinate digest
task-to-row mapping
first mismatch provenance
```

The first mismatch fields are reserved for:

```text
first_mismatch_flush_id
first_mismatch_task_id
first_mismatch_row_index
first_mismatch_field
legacy_row_fingerprint
extracted_row_fingerprint
```

This is the point where any `precommit_rows` count mismatch, such as 16650 vs
16649 in separate smoke runs, must be explained within one run and one
`FlushGpuResult`.

## Smoke Result

On the chr22 slice smoke workload, the normal triplex path produces same-run
row equality. The exact precommit row count may vary across separate runs
because the full run still has existing nondeterminism; the dual-finalizer
contract is evaluated within one run and one `FlushGpuResult`.

```text
flushes_compared = 3
legacy_rows = extracted_rows
missing_rows = 0
extra_rows = 0
order_mismatches = 0
cigar_mismatches = 0
coordinate_mismatches = 0
counter_mismatches = 0
archive_descriptor_mismatches = 0
first_mismatch_field = none
```

The dual-finalizer shadow keeps the lite output byte-identical to the baseline.

## Checks

```bash
make check-fasim-gasal2-flush-dual-finalizer-scaffold
make check-fasim-gasal2-flush-dual-finalizer-smoke
```
