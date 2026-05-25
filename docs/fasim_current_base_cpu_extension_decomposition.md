# Fasim Current-Base CPU Extension Decomposition

This note documents the CPU extension telemetry added after the current-base
worker/preAlign sweep. It is instrumentation only: scoring, thresholds, output
records, non-overlap behavior, sharded scheduling, and GPU policy are unchanged.

## Scope

The current clean-base Fasim GPU path is still:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension / SSW alignment
  -> output
```

#145 showed that preAlign CUDA is short and CPU extension dominates the measured
work volume. This PR decomposes the CPU extension bucket so the next GPU decision
is based on evidence. It does not add Accelign, score shadowing, GPU traceback,
or any output-changing path.

## Fields

Each Fasim process emits these additional `benchmark.fasim_*` fields:

| field | meaning |
|---|---|
| `benchmark.fasim_extend_candidates` | Total `scoreInfo` candidates entering `fastSIM_extend_from_scoreinfo()`. |
| `benchmark.fasim_extend_cutlength_attempts` | Identity/cutlength loop attempts across all candidates. |
| `benchmark.fasim_extend_align_calls` | CPU `aligner.Align()` calls made inside extension. |
| `benchmark.fasim_extend_align_cells` | Approximate score-only DP cell volume: `query_length * candidate_window_length` per align call. |
| `benchmark.fasim_extend_align_seconds` | Wall seconds spent inside extension `aligner.Align()` calls. |
| `benchmark.fasim_extend_convert_calls` | Calls to `convertMyTriplex()` after nonzero extension alignments. |
| `benchmark.fasim_extend_convert_seconds` | Wall seconds spent converting alignments into triplex records. |
| `benchmark.fasim_extend_sort_unique_seconds` | Wall seconds spent sorting/deduplicating per-call triplex records. |
| `benchmark.fasim_extend_records_before_filter` | Deduplicated per-call triplex records before final identity/stability/nt filtering and top-N cap. |
| `benchmark.fasim_extend_records_emitted` | Records pushed from extension into the caller triplex list. |
| `benchmark.fasim_extend_empty_scoreinfo` | Extension calls that received no scoreInfo candidates. |

The existing `benchmark.fasim_extend_seconds` remains the outer wall seconds
around `fastSIM_extend_from_scoreinfo()` calls. The new sub-stage seconds are
process-local sums. In sharded reports, summed seconds can exceed wall time
because workers and extension threads run concurrently.

## Runner JSON

The sharded runner parses these fields through the existing telemetry parser and
records them at:

```text
per_shard[*].run.telemetry
per_worker[*].telemetry
sharded_telemetry
single_run.telemetry
```

The new count fields are summed across shards and workers. Seconds fields are
also summed, matching the existing `fasim_extend_seconds` behavior. Telemetry is
not part of the run configuration digest and does not affect resume, scheduling,
merge order, or output comparison.

## Small Smoke Signal

The local smoke workload is intentionally tiny and should not be treated as the
large-workload performance conclusion. It does show that the split is working:

```text
single process testDNA + H19:
  fasim_extend_seconds          0.024439610
  fasim_extend_align_calls      165
  fasim_extend_align_cells      31,446,596
  fasim_extend_align_seconds    0.024134012
  fasim_extend_convert_seconds  0.000187308
  fasim_extend_sort_unique      0.000039906
  fasim_extend_records_emitted  24

sharded smoke:
  fasim_extend_align_calls      239
  fasim_extend_align_cells      45,931,208
  fasim_extend_align_seconds    0.034251567
  fasim_extend_convert_seconds  0.000283863
```

On this small smoke, extension time is mostly `aligner.Align()` time. That is a
useful sanity check, not a replacement for the larger current-base workload
matrix.

## Decision Use

Use this telemetry as the gate before attempting score-only GPU alignment:

```text
If fasim_extend_align_seconds dominates:
  score-only batch alignment shadow is a reasonable next probe.

If convert/sort/output dominates:
  do not chase score-only GPU alignment first.

If align_cells is high but align_seconds is not:
  staging or orchestration may be a larger issue than DP compute.

If records_emitted grows with TOPK:
  higher TOPK may increase downstream CPU work even when preAlign CUDA is fast.
```

The first Accelign-style experiment, if justified by larger workload telemetry,
should remain shadow-only:

```text
CPU output remains authoritative
GPU score-only output cannot reject candidates
digest must remain unchanged
score mismatches and false rejects must be zero
buffer build, H2D, kernel, and D2H seconds must be reported separately
```

Do not use this telemetry to justify in-process multi-GPU, GPU CIGAR, or GPU
full traceback without a separate design and exactness gate.
