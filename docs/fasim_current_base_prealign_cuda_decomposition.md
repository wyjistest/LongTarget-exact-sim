# Fasim Current-Base preAlign CUDA Decomposition

This note documents the telemetry added for the current clean
`cuda-p0.2-initial-handoff-pipeline` Fasim path. It is instrumentation only:
scoring, thresholds, output records, non-overlap behavior, scheduling, and
multi-GPU policy are unchanged.

## Scope

The active GPU path in this branch remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension / SSW alignment
  -> output
```

This is not the historical final speed-stack path. Do not infer
`FASIM_GPU_DP_COLUMN_AUTO`, `FASIM_TRANSFERSTRING_TABLE`, or `FASIM_SSW_*`
behavior from this telemetry unless those implementations are integrated into
the current base separately.

## Fasim Stderr Fields

Each Fasim process now emits stable stderr lines named
`benchmark.fasim_*` before normal exit:

| field | meaning |
|---|---|
| `benchmark.fasim_prealign_cuda_requested` | `1` when `FASIM_ENABLE_PREALIGN_CUDA=1` requested the current preAlign path. |
| `benchmark.fasim_prealign_cuda_active` | `1` when at least one preAlign CUDA batch completed successfully. |
| `benchmark.fasim_prealign_cuda_device` | Primary CUDA device recorded by the Fasim process. In sharded runs this is logical device `0` inside the worker. |
| `benchmark.fasim_prealign_cuda_devices` | Number of CUDA devices visible to the in-process preAlign path. Recommended sharded workers report `1`. |
| `benchmark.fasim_prealign_cuda_tasks` | Total preAlign tasks sent to CUDA across successful batches. |
| `benchmark.fasim_prealign_cuda_batches` | Successful preAlign CUDA batch calls. |
| `benchmark.fasim_prealign_cuda_topk` | Effective topK used after current caps/defaults. |
| `benchmark.fasim_prealign_cuda_max_tasks` | Effective max tasks per GPU batch. |
| `benchmark.fasim_prealign_cuda_peak_suppress_bp` | CPU peak suppression radius used after CUDA returns peaks. |
| `benchmark.fasim_prealign_cuda_h2d_seconds` | Host-to-device copy wall seconds inside successful preAlign batch calls. |
| `benchmark.fasim_prealign_cuda_kernel_seconds` | CUDA event-measured kernel seconds. This also backs the legacy `gpuSeconds` batch result field. |
| `benchmark.fasim_prealign_cuda_d2h_seconds` | Device-to-host copy wall seconds inside successful preAlign batch calls. |
| `benchmark.fasim_prealign_cuda_total_seconds` | Wall seconds for successful preAlign batch calls after input validation. |
| `benchmark.fasim_extend_threads` | Effective CPU extension thread count in the current process. |
| `benchmark.fasim_extend_seconds` | Wall seconds spent inside CUDA-path `fastSIM_extend_from_scoreinfo()` calls. |
| `benchmark.fasim_extend_candidates` | Total `scoreInfo` candidates entering `fastSIM_extend_from_scoreinfo()`. |
| `benchmark.fasim_extend_cutlength_attempts` | Total identity/cutlength loop attempts inside extension. |
| `benchmark.fasim_extend_align_calls` | CPU `aligner.Align()` calls made during extension. |
| `benchmark.fasim_extend_align_cells` | Approximate extension alignment cells, computed as query length times candidate window length for each `aligner.Align()` call. |
| `benchmark.fasim_extend_align_seconds` | Wall seconds spent inside extension `aligner.Align()` calls. |
| `benchmark.fasim_extend_convert_calls` | Calls to `convertMyTriplex()` after a nonzero extension alignment. |
| `benchmark.fasim_extend_convert_seconds` | Wall seconds spent in `convertMyTriplex()`. |
| `benchmark.fasim_extend_sort_unique_seconds` | Wall seconds spent in the per-call triplex sort/unique block. |
| `benchmark.fasim_extend_records_before_filter` | Deduplicated per-call triplex records before the final identity/stability/nt filter and top-N cap. |
| `benchmark.fasim_extend_records_emitted` | Records pushed from extension into the caller's triplex list. |
| `benchmark.fasim_extend_empty_scoreinfo` | Count of extension calls that received no scoreInfo candidates. |
| `benchmark.fasim_output_seconds` | Wall seconds spent writing CUDA-path output buffers. |
| `benchmark.fasim_prealign_cuda_fallbacks` | Count of CUDA batch failures that forced CPU fallback for the current process. |

The seconds are process-local sums. In multi-worker reports, summed seconds can
exceed wall time because workers run concurrently.

## Runner JSON

The sharded runner parses `benchmark.fasim_*` lines from each worker stderr log.
It records the parsed data in these locations:

```text
per_shard[*].run.telemetry
per_worker[*].telemetry
sharded_telemetry
single_run.telemetry
```

`per_worker[*].telemetry` is the sum of that worker's shard telemetry.
`sharded_telemetry` is the sum of all completed shard runs. Active/requested
flags aggregate with max semantics. Device/config fields are kept when stable;
when a field differs across shards, the runner records the distinct values as a
string list.

Telemetry is not part of the run configuration digest and does not affect
resume compatibility, digest comparison, output merge order, or shard
assignment.

## Use

Use the telemetry to decide which knob to tune next:

- If `fasim_extend_seconds` dominates, tune `FASIM_EXTEND_THREADS`, worker
  density, and CPU affinity first.
- If `fasim_extend_align_seconds` dominates `fasim_extend_seconds`, the next
  GPU feasibility probe should be score-only batch alignment shadowing. CPU
  traceback/CIGAR/output must remain authoritative until digest gates prove
  otherwise.
- If `fasim_extend_convert_seconds`, `fasim_extend_sort_unique_seconds`, or
  output seconds dominate, do not chase score-only GPU alignment first.
- If `fasim_prealign_cuda_kernel_seconds` dominates while GPU utilization is low,
  inspect `FASIM_PREALIGN_CUDA_TOPK`, `FASIM_PREALIGN_CUDA_MAX_TASKS`, and batch
  shape.
- If H2D/D2H dominates, inspect batch packing and host/device staging.
- If `per_worker[*].wall_seconds` is imbalanced while telemetry is balanced,
  inspect shard assignment and output/merge behavior.

The recommended multi-GPU model remains process-level sharding, with each Fasim
worker seeing one CUDA device.
