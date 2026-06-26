# Fasim GASAL2 Flush Pipeline Backpressure Goal

This document is a copy-ready `/goal` prompt for the next narrow
GASAL2-LongTarget milestone after the chromosome-level tail-latency
characterization.

The previous checkpoint showed that H19/hg38-primary `rule=0` chromosome shards
do not have a severe KegAlign-style shard tail:

```text
max / median shard wall ratio = 1.863266
top 1 shard wall fraction     = 8.1108%
top 3 shard wall fraction     = 22.6178%
decision                      = tail_latency_not_material
```

Shard wall is almost fully explained by GASAL2 requests, traceback requests,
and convert seconds. The next question is therefore inside each shard:

```text
Is wall time limited by GPU work, CPU conversion/finalization, archive/output
backpressure, pack starvation, or poor flush overlap?
```

## Goal Prompt

```text
/goal

Create a default-off telemetry-only PR that characterizes GASAL2-LongTarget
flush-level GPU/CPU pipeline backpressure.

Base:
  current GASAL2-LongTarget stack after the hg38 primary rule=0 archive-first
  and tail-latency characterization checkpoints.

Working branch suggestion:
  fasim-gasal2-flush-pipeline-backpressure

Objective:
  Determine whether current GASAL2-LongTarget wall time is limited by GPU
  compute, CPU convert/finalization, archive writer backpressure, host pack
  starvation, free-buffer starvation, or insufficient overlap between flushes.

Do not:
  - change default behavior
  - change output semantics
  - change scoring, thresholds, endpoint, CIGAR, traceback, conversion, sort,
    de-duplication, non-overlap, or archive schema semantics
  - add real double-buffering or triple-buffering
  - add real scheduler changes
  - change GASAL2 batch defaults
  - change worker defaults
  - enable MPS/MIG by default
  - implement diagonal partitioning
  - promote GASAL2 endpoint/CIGAR/traceback/score/digest as authority
  - claim full aligner.Align() replacement
  - force extra cudaDeviceSynchronize() for telemetry
  - introduce per-flush uncapped huge logs by default
  - infer flush-level behavior only from chromosome-level correlations

Prior evidence:
  H19 hg38 primary rule=0 GASAL2 archive-first:
    outer wall                  = 2677.003204 s
    sum shard wall              = 5265.515529 s
    GASAL2 requests             = 1,578,141,056
    traceback requests          =   489,063,766
    GASAL2 rows                 =    19,075,153
    archive-first TFOA          =   671.05 MB
    gzip TFOA                   =   269.51 MB
    fallbacks                   = 0

  H19 hg38 primary rule=0 Fasim vs GASAL2:
    Fasim rows                  = 19,059,562
    GASAL2 rows                 = 19,075,153
    common rows                 = 18,840,974
    overlap vs Fasim            = 98.8531%
    sum shard speedup           = 21.4664x

  Tail-latency characterization:
    tail_latency_decision       = tail_latency_not_material
    wall_corr_gasal2_requests   = 0.999872
    wall_corr_traceback_requests= 0.999853
    wall_corr_convert_seconds   = 0.999866

Interpretation:
  Current evidence does not justify diagonal partitioning as the next step.
  The next milestone must look inside each shard at flush-level producer and
  consumer timing.

Primary question:
  For each flush, where is time spent and which component is waiting?

Telemetry must be default-off:
  Suggested env:
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE=1
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_EXPORT=/path/to/flush_pipeline.tsv
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_JSON=/path/to/trace.json
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_LIMIT=N
    FASIM_GASAL2_FLUSH_PIPELINE_TRACE_CHROME_LIMIT=N

  Suggested benchmark prefix:
    benchmark.fasim_gasal2_flush_pipeline_*

Do not reuse historical inactive env names unless they still exist in current
source.

Required per-flush timeline fields:
  flush_id
  shard_name
  worker_id
  gpu_id
  flush_sequence
  pack_start_ns
  pack_end_ns
  wait_for_free_buffer_start_ns
  wait_for_free_buffer_end_ns
  h2d_start_ns
  h2d_end_ns
  gasal2_score_submit_start_ns
  gasal2_score_submit_end_ns
  gasal2_score_wait_start_ns
  gasal2_score_wait_end_ns
  exact_column_start_ns
  exact_column_end_ns
  traceback_pack_start_ns
  traceback_pack_end_ns
  traceback_submit_start_ns
  traceback_submit_end_ns
  traceback_wait_start_ns
  traceback_wait_end_ns
  d2h_start_ns
  d2h_end_ns
  convert_start_ns
  convert_end_ns
  archive_enqueue_start_ns
  archive_enqueue_end_ns
  archive_write_start_ns
  archive_write_end_ns
  sort_dedup_start_ns
  sort_dedup_end_ns
  flush_complete_ns

Use host timestamps for host stages. Use CUDA events only where they fit the
existing stream/synchronization structure. If a GPU interval cannot be measured
without adding synchronization, report the best existing host-side wait interval
and set:
  gpu_event_timing_available=false

Required per-flush work counters:
  gasal2_requests
  dp_cells
  scoreinfo_tasks
  selected_scoreinfos
  traceback_requests
  traceback_cigar_raw_ops
  traceback_cigar_merged_ops
  converted_candidates
  emitted_rows
  final_rows_after_sort_dedup
  dedup_removed_rows
  archive_bytes
  archive_blocks

Required queue/backpressure counters:
  input_queue_depth_at_start
  input_queue_depth_at_end
  ready_queue_depth_at_start
  ready_queue_depth_at_end
  convert_queue_depth_at_start
  convert_queue_depth_at_end
  archive_queue_depth_at_start
  archive_queue_depth_at_end
  gpu_producer_blocked_seconds
  cpu_consumer_idle_seconds
  archive_writer_blocked_seconds
  waiting_for_free_buffer_seconds
  gpu_inter_flush_idle_gap_seconds
  host_pack_gap_seconds

If the current implementation has no explicit queue for a concept, report:
  field_available=false
or use 0 only when the value is truly measured as zero. Do not confuse
"not modeled" with zero.

Required aggregate benchmark counters:
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
  benchmark.fasim_gasal2_flush_pipeline_total_gpu_producer_blocked_seconds
  benchmark.fasim_gasal2_flush_pipeline_total_cpu_consumer_idle_seconds
  benchmark.fasim_gasal2_flush_pipeline_total_waiting_for_free_buffer_seconds
  benchmark.fasim_gasal2_flush_pipeline_total_gpu_inter_flush_idle_gap_seconds
  benchmark.fasim_gasal2_flush_pipeline_decision

Chrome Trace JSON:
  Export a capped trace suitable for chrome://tracing or Perfetto.

  Required lanes:
    Host pack
    GPU stream
    Exact-column
    CPU convert
    Archive writer
    Sort/de-dup

  Event fields:
    name
    cat
    ph = "X"
    ts  microseconds
    dur microseconds
    pid = shard or process
    tid = lane
    args:
      flush_id
      requests
      traceback_requests
      rows
      archive_bytes

  The trace must be capped by flush count or event count to avoid huge files.

Offline pipeline simulation:
  Add a summarizer that reads the flush TSV and estimates:
    current_makespan_seconds
    ideal_two_buffer_makespan_seconds
    ideal_three_buffer_makespan_seconds
    convert_workers_1_makespan_seconds
    convert_workers_2_makespan_seconds
    convert_workers_4_makespan_seconds
    archive_writer_is_bottleneck
    convert_is_bottleneck
    gpu_is_bottleneck
    pack_is_bottleneck

  The simulation can be approximate, but it must clearly state assumptions.
  At minimum it should use measured per-flush durations:
    pack_seconds
    gpu_path_seconds
    exact_column_seconds
    traceback_seconds
    convert_seconds
    archive_write_seconds
    sort_dedup_seconds

  Do not present simulation estimates as measured runtime.

Required result tables:
  1. Per-flush TSV:
     flush_id
     requests
     traceback_requests
     rows
     pack_seconds
     gpu_path_seconds
     exact_column_seconds
     traceback_seconds
     d2h_seconds
     convert_seconds
     archive_write_seconds
     sort_dedup_seconds
     flush_wall_seconds
     gpu_producer_blocked_seconds
     cpu_consumer_idle_seconds
     waiting_for_free_buffer_seconds
     archive_queue_depth_max
     decision_hint

  2. Summary key=value:
     flushes
     total_flush_wall_seconds
     p50_flush_wall_seconds
     p90_flush_wall_seconds
     p99_flush_wall_seconds
     max_flush_wall_seconds
     max_to_median_flush_wall_ratio
     top_1pct_flush_wall_fraction
     total_requests
     total_traceback_requests
     total_rows
     total_pack_seconds
     total_gpu_path_seconds
     total_exact_column_seconds
     total_traceback_seconds
     total_convert_seconds
     total_archive_write_seconds
     total_sort_dedup_seconds
     total_gpu_producer_blocked_seconds
     total_cpu_consumer_idle_seconds
     total_waiting_for_free_buffer_seconds
     wall_corr_requests
     wall_corr_tracebacks
     wall_corr_rows
     wall_corr_convert_seconds
     wall_corr_archive_write_seconds
     simulated_two_buffer_speedup
     simulated_three_buffer_speedup
     simulated_convert_workers_2_speedup
     simulated_convert_workers_4_speedup
     decision

Decision rules:
  If GPU idle or producer-blocked time overlaps convert/archive queue pressure:
    decision = pipeline_overlap_candidate
    next = default-off double/triple buffer plus convert/archive worker pool

  If CPU consumer is idle while GPU path dominates:
    decision = gpu_critical_path
    next = traceback/exact-column/kernel optimization, not pipeline refactor

  If host pack gaps precede GPU idle:
    decision = pack_starvation_candidate
    next = pinned buffer and next-flush prepack shadow

  If archive queue is the only growing queue:
    decision = archive_backpressure_candidate
    next = bounded spool or independent archive writer

  If stages are already substantially overlapped and simulated speedup is small:
    decision = pipeline_refactor_no_go
    next = traceback/exact-column kernel or algorithmic reduction

  If telemetry cannot distinguish waiting states:
    decision = telemetry_incomplete
    next = add the missing low-overhead counters before optimization

Suggested workloads:
  1. chr22 H19 hg38 primary rule=0 archive-first
     Purpose:
       direct comparison with previous chr22 70s GASAL2 and 33min Fasim result.

  2. chr1 or chr2 H19 hg38 primary rule=0 archive-first
     Purpose:
       largest shard; tests long-running steady-state pipeline.

  3. chr21 H19 hg38 primary rule=0 archive-first
     Purpose:
       smaller shard; tests whether overhead dominates.

  Optional:
    full hg38 primary 24-shard run only after the above traces are bounded and
    not too large.

Required scripts:
  - scripts/summarize_fasim_gasal2_flush_pipeline.py
  - scripts/check_fasim_gasal2_flush_pipeline_parser.sh
  - scripts/check_fasim_gasal2_flush_pipeline_smoke.sh

Required docs:
  - docs/fasim_gasal2_flush_pipeline_backpressure.md

Suggested Make targets:
  - check-fasim-gasal2-flush-pipeline-parser
  - check-fasim-gasal2-flush-pipeline-smoke

Implementation notes:
  - Prefer existing local timing helpers and metrics style.
  - Keep exports capped by default.
  - For Chrome Trace, use microsecond timestamps.
  - Use monotonic host clock for host intervals.
  - If CUDA events are added, record them without changing the existing
    synchronization semantics.
  - Any timing field not available in the current architecture must be marked
    unavailable, not silently reported as zero.
  - Parser tests should use tiny synthetic TSV/JSON fixtures.
  - Smoke tests should use a tiny target slice and low trace limits.

Hard gates:
  - Telemetry disabled path has zero behavior change.
  - Smoke output row count/digest remains unchanged with telemetry enabled.
  - No new default env is required for normal GASAL2 runs.
  - Chrome Trace export is capped.
  - Per-flush TSV export is capped.
  - No extra global CUDA synchronization is introduced for telemetry.
  - Documentation clearly says this PR does not implement real pipelining.
```

## Reviewer Notes

This goal intentionally follows the chromosome-level tail-latency result:

```text
Tail at chromosome-shard granularity is not material.
Flush-level GPU/CPU overlap remains unknown.
```

The purpose of the next PR is to decide whether a pipeline refactor is worth
doing. It should not implement the refactor itself.
