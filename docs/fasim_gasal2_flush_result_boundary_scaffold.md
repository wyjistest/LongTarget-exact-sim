# Fasim GASAL2 Flush Result Boundary Scaffold

## Scope

This checkpoint adds a default-off synchronous `FlushGpuResult` boundary
scaffold for the GASAL2 flush path.

Runtime switch:

```bash
FASIM_GASAL2_FLUSH_RESULT_BOUNDARY_SHADOW=1
```

It does not add worker threads, queues, double buffering, new CUDA streams, or
new output paths. Execution order remains:

```text
build requests
run GASAL2 score/traceback
materialize FlushGpuResult
CPU finalize
legacy ordered output/commit
```

## Boundary

The scaffold introduces an owned, synchronous result snapshot:

```text
FasimGasal2FlushGpuResult
  flush_id
  request_count
  traceback_request_count
  task_count
  owned task snapshots
  owned score-group mapping
  owned selected alignments by task
  selected digest
  result/traceback byte estimates
```

The finalizer reads selected alignments through this owned result when the
shadow switch is enabled. With the switch disabled, it reads the original local
`replaySelectedByTask` vector exactly as before.

This is still not the final async-ready object: target sequence storage,
archive commit state, and fully pure row finalization remain in the legacy
closure. The point of this checkpoint is to establish the first ownership
boundary without changing scheduling or output semantics.

## Metrics

When requested, stderr reports:

```text
benchmark.fasim_gasal2_flush_result_boundary_requested
benchmark.fasim_gasal2_flush_result_boundary_active
benchmark.fasim_gasal2_flush_result_boundary_disabled_reason
benchmark.fasim_gasal2_flush_result_boundary_flushes
benchmark.fasim_gasal2_flush_result_boundary_materialized_flushes
benchmark.fasim_gasal2_flush_result_boundary_finalizer_consumed_result_flushes
benchmark.fasim_gasal2_flush_result_boundary_task_backing_owned_flushes
benchmark.fasim_gasal2_flush_result_boundary_score_group_mapping_owned_flushes
benchmark.fasim_gasal2_flush_result_boundary_selected_by_task_owned_flushes
benchmark.fasim_gasal2_flush_result_boundary_task_count
benchmark.fasim_gasal2_flush_result_boundary_score_groups
benchmark.fasim_gasal2_flush_result_boundary_selected_alignments
benchmark.fasim_gasal2_flush_result_boundary_result_bytes
benchmark.fasim_gasal2_flush_result_boundary_traceback_bytes
benchmark.fasim_gasal2_flush_result_boundary_result_bytes_includes_traceback
benchmark.fasim_gasal2_flush_result_boundary_materialize_seconds
benchmark.fasim_gasal2_flush_result_boundary_cigar_seconds
benchmark.fasim_gasal2_flush_result_boundary_finalize_seconds
benchmark.fasim_gasal2_flush_result_boundary_commit_seconds
benchmark.fasim_gasal2_flush_result_boundary_rows_compared
benchmark.fasim_gasal2_flush_result_boundary_missing_rows
benchmark.fasim_gasal2_flush_result_boundary_extra_rows
benchmark.fasim_gasal2_flush_result_boundary_cigar_mismatches
benchmark.fasim_gasal2_flush_result_boundary_digest_mismatches
benchmark.fasim_gasal2_flush_result_boundary_result_digest
benchmark.fasim_gasal2_flush_result_boundary_decision
```

Expected material-workload decision:

```text
active=1
disabled_reason=none
materialized_flushes > 0
finalizer_consumed_result_flushes = materialized_flushes
decision=go_pure_finalizer_extraction_next
```

## Non-Claims

This checkpoint does not claim:

```text
pure CPU finalizer
ordered commit extraction
thread-safe archive writer
double-buffer readiness
wall-time speedup
```

`rows_compared`, `missing_rows`, `extra_rows`, `cigar_mismatches`, and
`digest_mismatches` remain zero-valued scaffold fields until a second
finalizer implementation exists to compare against the legacy finalizer on the
same result object.

## Next Milestone

The next PR should extract:

```text
finalize_flush(result) -> FlushFinalizedRows
commit_flush(flush_id, rows)
```

The finalizer must avoid direct writes to global output streams and archive
writers. Commit remains main-thread and ordered by `flush_id`.

After that, a bounded two-slot state machine can be implemented:

```text
FREE -> GPU_SUBMITTED -> GPU_READY -> CPU_FINALIZING -> COMMIT_READY -> COMMITTED -> FREE
```

## Checks

```bash
make check-fasim-gasal2-flush-result-boundary-scaffold
make check-fasim-gasal2-flush-result-boundary-smoke
```

The smoke check runs a deterministic chr22 slice twice, with and without the
result-boundary switch, and requires byte-identical lite output.
