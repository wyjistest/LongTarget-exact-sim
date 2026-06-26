# Fasim GASAL2 Flush Pipeline Backpressure Telemetry

## Scope

This checkpoint adds a default-off telemetry path for GASAL2-LongTarget
flush-level pipeline characterization.

It does not change default behavior, scoring, endpoint selection, CIGAR,
traceback, conversion, sort/de-duplication, output semantics, archive schema,
batch defaults, worker defaults, or scheduling.

Enable with:

```bash
FASIM_GASAL2_FLUSH_PIPELINE_TRACE=1
FASIM_GASAL2_FLUSH_PIPELINE_TRACE_EXPORT=/path/to/flush_pipeline.tsv
FASIM_GASAL2_FLUSH_PIPELINE_TRACE_JSON=/path/to/trace.json
FASIM_GASAL2_FLUSH_PIPELINE_TRACE_LIMIT=1024
FASIM_GASAL2_FLUSH_PIPELINE_TRACE_CHROME_LIMIT=256
```

## Runtime Output

When enabled, Fasim prints:

```text
benchmark.fasim_gasal2_flush_pipeline_requested
benchmark.fasim_gasal2_flush_pipeline_active
benchmark.fasim_gasal2_flush_pipeline_flushes
benchmark.fasim_gasal2_flush_pipeline_export_path
benchmark.fasim_gasal2_flush_pipeline_export_rows
benchmark.fasim_gasal2_flush_pipeline_export_truncated
benchmark.fasim_gasal2_flush_pipeline_chrome_trace_path
benchmark.fasim_gasal2_flush_pipeline_chrome_trace_events
benchmark.fasim_gasal2_flush_pipeline_chrome_trace_truncated
benchmark.fasim_gasal2_flush_pipeline_total_pack_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gpu_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_total_exact_column_seconds
benchmark.fasim_gasal2_flush_pipeline_total_traceback_seconds
benchmark.fasim_gasal2_flush_pipeline_total_d2h_seconds
benchmark.fasim_gasal2_flush_pipeline_total_convert_seconds
benchmark.fasim_gasal2_flush_pipeline_total_archive_write_seconds
benchmark.fasim_gasal2_flush_pipeline_total_sort_dedup_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_score_poll_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_score_result_copy_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_poll_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_result_copy_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_cigar_vector_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_cigar_string_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_synchronous_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_queue_supported
benchmark.fasim_gasal2_flush_pipeline_synchronous_flush_path
benchmark.fasim_gasal2_flush_pipeline_total_gpu_producer_blocked_seconds
benchmark.fasim_gasal2_flush_pipeline_total_cpu_consumer_idle_seconds
benchmark.fasim_gasal2_flush_pipeline_total_waiting_for_free_buffer_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gpu_inter_flush_idle_gap_seconds
benchmark.fasim_gasal2_flush_pipeline_decision
```

The per-flush TSV includes host-side timestamps for pack, GASAL2 score/traceback
host wait, exact-column, D2H approximation, convert, archive write, sort/de-dup,
work counters, archive bytes/blocks and explicit availability flags.

The wait-state fields split the GASAL2 bridge wait path into:

```text
gasal2_score_poll_wait_seconds
gasal2_score_result_copy_seconds
gasal2_traceback_poll_wait_seconds
gasal2_traceback_result_copy_seconds
gasal2_traceback_cigar_vector_seconds
gasal2_traceback_cigar_string_seconds
gasal2_synchronous_wait_seconds
synchronous_flush_path=true
queue_supported=false
```

`gasal2_synchronous_wait_seconds` is the bridge wait interval minus result copy
and CIGAR materialization deltas. It is a host-side synchronous wait estimate,
not a CUDA event timing.

Queue/backpressure concepts that are not explicit in the current serial flush
implementation are exported as unavailable, not as measured zero:

```text
input_queue_depth_available=false
ready_queue_depth_available=false
convert_queue_depth_available=false
archive_queue_depth_available=false
gpu_producer_blocked_available=false
cpu_consumer_idle_available=false
waiting_for_free_buffer_available=false
```

The Chrome Trace JSON is capped and contains lanes:

```text
Host pack
GPU stream
GASAL2 wait
GASAL2 copy
Exact-column
CPU convert
Archive writer
Sort/de-dup
```

GPU intervals currently use existing host-side wait boundaries. No extra global
CUDA synchronization is added for telemetry.

## Offline Summary

Use:

```bash
python3 scripts/summarize_fasim_gasal2_flush_pipeline.py \
  --flush-tsv /path/to/flush_pipeline.tsv \
  --chrome-trace /path/to/trace.json \
  --output-summary /path/to/summary.txt \
  --output-tsv /path/to/summary_flush.tsv
```

The summarizer reports flush wall percentiles, request/traceback/row totals,
stage totals, wall correlations and approximate pipeline simulations:

```text
current_makespan_seconds
ideal_two_buffer_makespan_seconds
ideal_three_buffer_makespan_seconds
convert_workers_1_makespan_seconds
convert_workers_2_makespan_seconds
convert_workers_4_makespan_seconds
simulated_two_buffer_speedup
simulated_three_buffer_speedup
simulated_convert_workers_2_speedup
simulated_convert_workers_4_speedup
decision
```

Simulation output is an estimate from measured per-flush durations, not measured
runtime.

## Smoke Result

Command:

```bash
bash scripts/check_fasim_gasal2_flush_pipeline_smoke.sh
```

Observed small-slice result:

```text
flush_pipeline_requested=1
flush_pipeline_active=1
flush_pipeline_flushes=3
flush_pipeline_export_rows=2
flush_pipeline_export_truncated=1
flush_pipeline_chrome_events=10
flush_pipeline_chrome_truncated=1
flush_pipeline_queue_supported=0
flush_pipeline_synchronous_flush_path=1
flush_pipeline_synchronous_wait_seconds=0.409484
total_flush_wall_seconds=1.449575
total_requests=445616
total_traceback_requests=138592
simulated_two_buffer_speedup=1.177587
decision=telemetry_incomplete
```

The smoke check compares telemetry-disabled and telemetry-enabled lite output
byte-for-byte. The digest was unchanged.

## Decision

Current decision is:

```text
telemetry_incomplete
```

This is intentional for the first checkpoint. The current code path has a
mostly serial flush model and does not expose real input, ready, convert or
archive queues. The telemetry can show per-flush timing and capped Chrome
traces, and it now separates GASAL2 synchronous wait from result copy/CIGAR
materialization. It still cannot prove GPU producer blocking, CPU consumer idle
time or archive queue backpressure as measured runtime facts because there are
no explicit producer/consumer queues on this path.

The next optimization should not implement double buffering solely from this
checkpoint. First run telemetry-off and telemetry-on chr22 full-plain
characterization to measure overhead and wait-state fractions; the current
chr22 result is recorded in `docs/fasim_gasal2_flush_pipeline_wait_state.md`.
If synchronous wait dominates and host-side pack/convert/archive cannot overlap
it, then a default-off double-buffer prototype is justified; otherwise continue
with traceback/exact-column kernel work.

## Checks

```bash
bash scripts/check_fasim_gasal2_flush_pipeline_parser.sh
bash scripts/check_fasim_gasal2_flush_pipeline_smoke.sh

make check-fasim-gasal2-flush-pipeline-parser
make check-fasim-gasal2-flush-pipeline-smoke
```
