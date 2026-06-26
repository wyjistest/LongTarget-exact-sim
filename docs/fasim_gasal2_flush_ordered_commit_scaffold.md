# Fasim GASAL2 Flush Ordered Commit Scaffold

## Scope

This checkpoint adds default-off telemetry for the ordered commit boundary
after the owned `FlushGpuResult` and flush-local precommit rows:

```bash
FASIM_GASAL2_FLUSH_ORDERED_COMMIT_SHADOW=1
```

It does not add worker threads, queues, double buffering, new CUDA streams, or
new output paths. It observes the current synchronous authority path.

Requesting this shadow mode also materializes the owned `FlushGpuResult`
boundary, because commit ordering and memory estimates need per-flush result
metadata.

## Boundary

The intended architecture is:

```text
FlushGpuResult
  -> finalize_flush(result) -> FlushFinalizedRows
  -> commit_flush(flush_id, rows)
```

This scaffold does not yet extract those functions. Instead it records that the
current path has:

```text
FlushGpuResult ready
precommit rows ready
legacy synchronous commit observed
```

`precommit rows` are flush-local rows before final global sort/de-dup. They are
not the final globally de-duplicated output row count.

## Metrics

When requested, stderr reports:

```text
benchmark.fasim_gasal2_ordered_commit_requested
benchmark.fasim_gasal2_ordered_commit_active
benchmark.fasim_gasal2_ordered_commit_disabled_reason
benchmark.fasim_gasal2_ordered_commit_flushes_ready
benchmark.fasim_gasal2_ordered_commit_flushes_committed
benchmark.fasim_gasal2_ordered_commit_direct_flushes_committed
benchmark.fasim_gasal2_ordered_commit_triplex_flushes_committed
benchmark.fasim_gasal2_ordered_commit_order_violations
benchmark.fasim_gasal2_ordered_commit_precommit_rows
benchmark.fasim_gasal2_ordered_commit_appended_rows
benchmark.fasim_gasal2_ordered_commit_archive_records
benchmark.fasim_gasal2_ordered_commit_result_bytes_p50
benchmark.fasim_gasal2_ordered_commit_result_bytes_p90
benchmark.fasim_gasal2_ordered_commit_result_bytes_max
benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p50
benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p90
benchmark.fasim_gasal2_ordered_commit_traceback_bytes_max
benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback
benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p50
benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p90
benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_max
benchmark.fasim_gasal2_ordered_commit_projected_two_slot_peak_bytes
benchmark.fasim_gasal2_ordered_commit_finalize_seconds
benchmark.fasim_gasal2_ordered_commit_write_task_seconds
benchmark.fasim_gasal2_ordered_commit_archive_seconds
benchmark.fasim_gasal2_ordered_commit_counter_seconds
benchmark.fasim_gasal2_ordered_commit_total_seconds
benchmark.fasim_gasal2_ordered_commit_missing_rows
benchmark.fasim_gasal2_ordered_commit_extra_rows
benchmark.fasim_gasal2_ordered_commit_cigar_mismatches
benchmark.fasim_gasal2_ordered_commit_counter_mismatches
benchmark.fasim_gasal2_ordered_commit_digest_mismatches
benchmark.fasim_gasal2_ordered_commit_decision
```

Expected material-workload decision:

```text
active=1
disabled_reason=none
flushes_ready > 0
flushes_committed = flushes_ready
order_violations = 0
precommit_rows > 0
decision=go_same_result_dual_finalizer_shadow_next
```

## Non-Claims

This checkpoint does not claim:

```text
extracted finalize_flush()
extracted commit_flush()
same-result dual finalizer comparison
thread-safe archive writer
thread-safe global counters
double-buffer readiness
wall-time speedup
```

`missing_rows`, `extra_rows`, `cigar_mismatches`, `counter_mismatches`, and
`digest_mismatches` remain zero-valued scaffold fields until the extracted
finalizer and shadow in-memory commit exist.

## Memory

The scaffold reports per-flush p50/p90/max values for:

```text
result bytes
traceback bytes
precommit row bytes
```

It also reports a conservative two-slot peak estimate:

```text
projected_two_slot_peak_bytes =
  2 * (max result bytes + max precommit row bytes)
```

`result_bytes` already includes traceback bytes, so traceback bytes are reported
separately for attribution and must not be added again when estimating two-slot
memory.

This replaces the earlier aggregate byte counters for two-slot sizing.

## Next Milestone

The next PR should implement same-result dual finalizer shadow:

```text
same FlushGpuResult
  legacy finalizer / commit authority
  extracted finalize_flush() + shadow in-memory commit
```

The shadow commit must not write real output files. It should compare row
order, row multiset, CIGAR digest, task-to-row ranges, counter deltas and
archive descriptors against the legacy authority path.

## Checks

```bash
make check-fasim-gasal2-flush-ordered-commit-scaffold
make check-fasim-gasal2-flush-ordered-commit-smoke
```

The smoke check runs a deterministic chr22 slice twice, with and without the
ordered-commit switch, and requires byte-identical lite output.
