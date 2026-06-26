# Fasim GASAL2 Flush Pipeline Wait-State Telemetry

## Scope

This checkpoint extends the default-off flush pipeline telemetry with GASAL2
wait-state counters. It is still telemetry-only.

It does not change scoring, endpoint selection, CIGAR, traceback, conversion,
sort/de-duplication, output semantics, archive schema, batch defaults, worker
defaults, scheduling, or queue structure.

## Added Fields

Per flush TSV rows now include:

```text
gasal2_score_poll_wait_seconds
gasal2_score_result_copy_seconds
gasal2_traceback_poll_wait_seconds
gasal2_traceback_result_copy_seconds
gasal2_traceback_cigar_vector_seconds
gasal2_traceback_cigar_string_seconds
gasal2_synchronous_wait_seconds
synchronous_flush_path
queue_supported
```

Aggregate metrics use the same prefix:

```text
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_score_poll_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_score_result_copy_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_poll_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_result_copy_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_cigar_vector_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_traceback_cigar_string_seconds
benchmark.fasim_gasal2_flush_pipeline_total_gasal2_synchronous_wait_seconds
benchmark.fasim_gasal2_flush_pipeline_queue_supported
benchmark.fasim_gasal2_flush_pipeline_synchronous_flush_path
```

## Timing Semantics

The GASAL2 bridge still uses the existing synchronous wait path. This telemetry
does not add per-flush `cudaDeviceSynchronize()` and does not create queues.

`gasal2_synchronous_wait_seconds` is calculated as the GASAL2 wait interval
minus result copy and CIGAR materialization deltas. It is a host-side estimate
of waiting for outstanding GASAL2 streams, not a CUDA event measurement.

Because the current path has no explicit producer/consumer queues:

```text
queue_supported=false
synchronous_flush_path=true
```

Queue depth and backpressure fields remain unavailable unless a future
pipeline refactor introduces actual queues.

## Decision

This checkpoint can distinguish:

```text
GASAL2 synchronous wait
GASAL2 result copy
CIGAR vector/string materialization
CPU convert/archive/sort host stages
```

It still cannot prove:

```text
GPU producer blocked by convert queue
CPU consumer idle on GPU queue
archive writer backpressure
true GPU kernel time by CUDA event
```

The correct next experiment is telemetry-off versus telemetry-on on chr22
full-plain to measure overhead and wait-state fractions before implementing
double buffering.

## chr22 Characterization

Fresh chr22/H19 rule-0 GASAL2 full-plain telemetry characterization:

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
work   = .tmp/characterize_fasim_gasal2_flush_wait_state_chr22

telemetry off wall = 69.050730 s
telemetry on wall  = 68.713739 s
overhead ratio     = 0.995120

flushes            = 94
GASAL2 requests    = 21,802,035
traceback requests =  6,910,419

score poll wait    =  8.444486 s
traceback poll wait=  6.575919 s
synchronous wait   = 15.020407 s
result copy        =  1.594199 s
CIGAR vector       =  1.230097 s
convert            = 15.361888 s

queue_supported        = 0
synchronous_flush_path = 1
decision               = telemetry_incomplete
```

The first telemetry-off run produced one fewer lite row than the telemetry-on
run, so byte equality was not used as the full-chr22 semantic gate. A second
telemetry-off repeat reproduced the telemetry-on sorted row set exactly:

```text
off lines       = 388,820
off2 lines      = 388,821
on lines        = 388,821

off vs off2 sorted equal = 0
off2 vs on sorted equal  = 1
```

This matches the existing chr22 repeatability caveat for this path: full chr22
row order and a small boundary row can vary between repeated runs. The
wait-state telemetry itself is therefore characterized as low-overhead and
row-set clean relative to a same-build repeat, but not as a byte-equality proof
for the nondeterministic full chr22 workload.

## Checks

```bash
make check-fasim-gasal2-flush-pipeline-parser
make check-fasim-gasal2-flush-pipeline-smoke
```
