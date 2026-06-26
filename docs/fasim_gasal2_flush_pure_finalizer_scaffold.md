# Fasim GASAL2 Flush Pure Finalizer Scaffold

## Scope

This checkpoint adds default-off telemetry for the next boundary after the
owned `FlushGpuResult` scaffold:

```bash
FASIM_GASAL2_FLUSH_PURE_FINALIZER_SHADOW=1
```

It does not add worker threads, queues, double buffering, new CUDA streams, or
new output paths. It does not replace the legacy finalizer and does not perform
a second finalizer comparison yet.

Requesting this shadow mode also materializes the owned `FlushGpuResult`
boundary used by the previous scaffold, because pure finalization must consume
an independently owned GPU-result snapshot.

The goal is to classify whether the current synchronous flush path has enough
structure to extract:

```text
finalize_flush(result) -> FlushFinalizedRows
commit_flush(flush_id, rows)
```

## Current Boundary

The previous result-boundary scaffold established:

```text
FlushGpuResult
  owned task snapshots
  owned score-group mapping
  owned selected alignments by task
```

This checkpoint observes the CPU side immediately after conversion/filtering:

```text
direct/archive branch:
  directRowsByTask is flush-local before output/archive writes

non-direct branch:
  triplexesByTask is flush-local before write_task_triplexes()
```

Those row containers are close to the future `FlushFinalizedRows` payload, but
commit is still mixed into the same synchronous closure.

## Metrics

When requested, stderr reports:

```text
benchmark.fasim_gasal2_flush_pure_finalizer_requested
benchmark.fasim_gasal2_flush_pure_finalizer_active
benchmark.fasim_gasal2_flush_pure_finalizer_disabled_reason
benchmark.fasim_gasal2_flush_pure_finalizer_flushes_observed
benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_ready_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_missing_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_eligible_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_ineligible_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_local_rows_ready_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_direct_rows_local_ready_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_triplex_rows_local_ready_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_output_side_effect_blocker_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_archive_writer_blocker_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_global_task_triplex_commit_blocker_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_telemetry_global_counter_blocker_flushes
benchmark.fasim_gasal2_flush_pure_finalizer_precommit_rows
benchmark.fasim_gasal2_flush_pure_finalizer_rows_compared
benchmark.fasim_gasal2_flush_pure_finalizer_missing_rows
benchmark.fasim_gasal2_flush_pure_finalizer_extra_rows
benchmark.fasim_gasal2_flush_pure_finalizer_cigar_mismatches
benchmark.fasim_gasal2_flush_pure_finalizer_digest_mismatches
benchmark.fasim_gasal2_flush_pure_finalizer_decision
```

Expected material-workload decision while commit is still embedded:

```text
active=1
result_boundary_ready_flushes > 0
local_rows_ready_flushes > 0
eligible_flushes = 0
ineligible_flushes = flushes_observed
disabled_reason=ordered_commit_not_extracted
decision=go_ordered_commit_extraction_next
```

## Non-Claims

This checkpoint does not claim:

```text
pure CPU finalizer
same-result dual finalizer comparison
thread-safe finalization
thread-safe archive writer
ordered commit extraction
double-buffer readiness
wall-time speedup
```

`rows_compared`, `missing_rows`, `extra_rows`, `cigar_mismatches`, and
`digest_mismatches` remain zero-valued scaffold fields until an extracted
`finalize_flush()` implementation exists and is compared with the legacy
finalizer on the same `FlushGpuResult`.

## Blockers

The scaffold classifies the current blockers explicitly:

```text
output_side_effect_blocker_flushes
  direct Lite output rows are emitted in the same closure.

archive_writer_blocker_flushes
  column archive rows are written in the same closure.

global_task_triplex_commit_blocker_flushes
  non-direct rows are committed through write_task_triplexes().

telemetry_global_counter_blocker_flushes
  conversion and emission counters are updated from the current path.
```

The next milestone should extract a main-thread ordered commit boundary while
keeping row construction flush-local:

```text
FlushGpuResult
  -> finalize_flush(result) -> FlushFinalizedRows
  -> commit_flush(flush_id, rows)
```

After that, a same-result dual finalizer shadow can compare:

```text
legacy finalizer rows
extracted finalize_flush rows
```

without running GASAL2 twice.

## Checks

```bash
make check-fasim-gasal2-flush-pure-finalizer-scaffold
make check-fasim-gasal2-flush-pure-finalizer-smoke
```

The smoke check runs a deterministic chr22 slice twice, with and without the
pure-finalizer switch, and requires byte-identical lite output.
