# Fasim GASAL2 Multi-Segment Target Reuse Phase 3

## Decision

Phase 3 is an evidence-complete `no_go`. During Phase 8 closure, Phase 4 is
classified as dependency `no_go` because its microbatch design requires the
persistent target/context boundary that Phase 3 proved unavailable. Execution
proceeded to the independent Phase 5 exact-column optimization.

No persistent runtime mode was added. The existing per-segment process path
and all defaults remain unchanged.

## Measured Baseline

The profile reuses the completed KCNQ1OT1 max4, shift-0, chr22-full run. It
does not rerun chr22.

```text
source_artifact=.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full/grids/shift_0
tracked_receipt=docs/fasim_gasal2_multi_segment_setup_profile.tsv
segments=4
processes=4
target_read_passes=4
fallbacks=0
```

Aggregate result:

```text
wall_seconds=334.641191
flush_total_seconds=312.530900
nonflush_wall_seconds=22.110291
nonflush_wall_percent=6.61
host_setup_observed_seconds=17.684555
host_setup_observed_percent=5.28

fasta_read_seconds=0.696883
cut_sequence_seconds=0.032151
transfer_string_seconds=5.772050
transfer_table_seconds_nested=5.720110
src_transform_seconds=2.500824
encode_seconds=7.882560
cuda_query_init_seconds=0.800087
gasal2_init_seconds=2.697896
gasal2_fill_seconds=2.722217
```

`transfer_table_seconds` is measured inside `transfer_string_seconds` and is
not added a second time. `gasal2_init_seconds` occurs in flush execution and
is also reported separately rather than added to non-flush wall.

The conservative end-to-end ceiling for eliminating everything outside the
measured flushes is 6.61%. The explicitly identified host setup components are
5.28% of wall. Target/context setup is therefore material but is not the
dominant wall-time component.

## Current Architecture

### Query entry point

`Fasim-LongTarget.cpp` accepts one `-f2` path and calls `readRna` once. That
function consumes the first line as the name and concatenates every remaining
line as sequence. A multi-record query FASTA would concatenate subsequent
headers into the sequence; it is not a valid multi-query entry point.

The normal-triplex TFOsorted streaming body is local to `main` and owns query
state, target input, output files, CUDA query objects, finalizers, and all
per-run telemetry. There is no callable per-query engine or segment-manifest
entry point that can safely be invoked repeatedly in one process.

### GASAL2 storage

`gasal2_align_bridge.cpp` already has process-global score and traceback
`BridgeState` objects. `ensure_state` reuses their allocations when the next
batch fits existing capacities. This reuse is lost only because the segmented
runner launches a new process for each query segment.

The bridge does not expose an owner object, target digest binding, explicit
reset, or explicit destruction/error recovery API suitable for a multi-query
runtime. Its statistics are also process-global and cumulative.

### Target payload

Both score and traceback paths call `gasal_host_batch_fill(..., TARGET)` for
every selected alignment batch. The bridge stores target pointers/views in
`FasimGasal2Attempt`, not stable resident-target IDs plus offsets.

Measured target payload:

```text
score_target_bytes=2852527109
traceback_target_bytes=2134964220
gasal2_target_batch_bytes=4987491329

score_requests_min=10285794
score_requests_max=11378192
traceback_requests_min=7244354
traceback_requests_max=8609636
target_batches_query_dependent=1
```

Each query segment selects a different request set. The approximately 4.99 GB
of aggregate target-batch payload is not one fixed batch that can be uploaded
once and replayed for all segments. A true one-copy contract requires a new
resident target representation and offset/length indirection in the GASAL2
input/kernel path.

## Missing Evidence

The current telemetry records target bytes and initialization time, but not:

```text
target_h2d_copy_count=unavailable
context_creation_events=unavailable
device_alloc_count=unavailable
device_alloc_bytes=unavailable
workspace_initializations=unavailable
peak_device_memory_bytes=unavailable
device_memory_leak=unavailable
```

Unavailable values are not reported as zero. Adding counters alone would not
create the missing persistent target contract.

## Gate Evaluation

| Phase 3 hard gate | Result |
|---|---|
| full row-set equal | not run; no valid persistent candidate |
| all three top5 equal | not run; no valid persistent candidate |
| fallbacks = 0 | baseline pass |
| N-segment target reads = 1 | fail: 4 |
| N-segment target transforms = 1 | fail: each process rebuilds transforms |
| N-segment context creations = 1 | unavailable; process boundary prevents reuse |
| device memory leak = 0 | unavailable |
| default path unchanged = 1 | pass |
| persistent B=1 wall <= legacy x 1.03 | not run |

The hard gate cannot pass. A host-only manifest wrapper would still repack and
copy query-dependent target batches, so it would not satisfy the required
device-resident target/context contract. Such a wrapper is intentionally not
introduced as a misleading scaffold.

## Alternatives Considered

1. Re-enter the existing `main` once per segment in one process. This could
   preserve the process-global GASAL2 allocation, but target parsing,
   transforms, batch packing, and target H2D remain per query; global stats and
   failure cleanup are not query-safe.
2. Extract the 17k-line streaming body into a reentrant query engine and cache
   host target transforms. This could approach the 5-7% setup ceiling, but it
   still does not make target batches device resident.
3. Add resident target IDs and offset/length indirection to GASAL2. This is a
   new execution-engine contract with Phase 4-sized memory and kernel work,
   not a bounded B=1 scaffold.

Given the measured ceiling and the missing device contract, options 1 and 2
would weaken the specified hard gate, while option 3 exceeds Phase 3 scope.
The correct decision is `no_go`, not a broad refactor labeled as reuse.

## Consequences

```text
phase_3_status=no_go
phase_4_status=no_go
production_defaults=unchanged
multi_segment_context_active=0
ownership_work_drop=0
next_active_phase=5
```

This final Phase 4 classification does not claim that a microbatch candidate
was implemented. It records that the specified Phase 4 architecture cannot be
entered without violating its hard prerequisite; it is no longer an unresolved
external blocker.

Phase 5 is independent and can optimize exact-column traceback/CIGAR work
without requiring persistent multi-segment state.

## Verification

```bash
python3 tests/check_analyze_fasim_gasal2_multi_segment_setup.py
make check-fasim-gasal2-multi-segment-context-phase3
```
