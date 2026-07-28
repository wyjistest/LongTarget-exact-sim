# SSW Oracle Telemetry Specification

## Role

Oracle trace is opt-in diagnostic evidence for L0-L6. It does not change the
published result, define a weaker equality contract, or authorize a GPU path.
The schema is `schemas/ssw_oracle_call.schema.json`.

## Environment

```text
FASIM_SSW_ORACLE_TRACE=1
FASIM_SSW_ORACLE_TRACE_DIR=/absolute/or/relative/directory
FASIM_SSW_ORACLE_TRACE_FILTER=substring[,substring...]
FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS=0|1
```

- Missing, empty, or `0` trace activation means disabled.
- `TRACE_DIR` is mandatory when enabled. Parent directories are created.
- Empty filter or `*` records every key. Otherwise a record is written when
  its stable record key or workload key contains any comma-separated token.
- Full columns `0` records count/max/digest; `1` additionally records the
  integer vectors.
- Existing trace files are never overwritten. A collision is a hard trace
  error, so formal repetitions use physically separate directories.

The Phase 2 regression runner fixes `FASIM_EXTEND_THREADS=1`. Multi-thread
tracing is supported for distinct keys, but deterministic cross-thread file
ordering is not a contract and duplicate keys fail rather than race-overwrite.

## Record mapping

One pre-align record covers:

```text
L0 translated-input identity and effective scoring
L1 byte/word per-column maxima
L2 strict threshold, grouping, tie rule, ordered scoreInfos
```

One alignment record covers:

```text
L0 query and attempt-window identity
L1 forward/reverse byte or word DP-pass identities
L2 attempt key and threshold/best/last selection reason
L3 score1/score2 and forward endpoints
L4 reverse-derived starts
L5 all band widths/maxima plus canonical CIGAR and traceback stop rule
L6 converted LongTarget rows that survive local emission filters, including
   coordinates, aligned/ungapped sequences, derived metrics and row digest
```

The record itself contains no timestamps or process IDs, allowing byte-stable
fixtures. Raw execution receipts carry time, command, binary, environment,
input, output, and SHA-256 provenance separately.

## Default-off invariant

When trace is disabled:

- no trace directory or file is created;
- no trace text is written to stdout or stderr;
- no runtime parameter, endpoint, CIGAR, selection, or output path changes;
- authority output must be byte-identical to paired trace-on execution.

Phase 2 proves this with five paired observations for both hq10/ht02 and
hq11/ht02. Trace output is filtered to the pre-align context and known
historical mismatch call; filter choice does not alter computation.

## Phase 7 forward-hybrid telemetry

The F binary requires a new path in
`FASIM_SSW_FORWARD_HYBRID_TELEMETRY_PATH`. A missing path or an existing path
is a hard error. One successful process writes one schema-version-1 TSV row.

Identity and call fields are:

```text
backend, status, device, flushes, tasks, scoreinfos, attempts, selected
cpu_prealign_calls, cpu_forward_calls, cpu_reverse_calls
cpu_banded_sw_calls, cpu_continuation_calls, cpu_failures, fallback_calls
```

GPU phase fields are:

```text
gpu_packing_seconds, gpu_h2d_seconds
gpu_prealign_kernel_seconds, gpu_selection_kernel_seconds
gpu_forward_kernel_seconds, gpu_endpoint_reduce_seconds
gpu_d2h_seconds, gpu_unattributed_overhead_seconds
gpu_preselect_seconds, gpu_forward_seconds, backend_total_seconds
host_input_bytes, device_input_bytes
device_workspace_peak_bytes, device_output_bytes
```

CPU and downstream fields are:

```text
cpu_substring_seconds, cpu_continuation_seconds
cpu_reverse_start_seconds, cpu_banded_traceback_seconds, cpu_cigar_seconds
downstream_conversion_seconds, cluster_sort_seconds, filter_seconds
```

All times are nonnegative steady-clock seconds. Transfer byte counts are
accumulated across flushes; workspace is the maximum requested by one flush.
The required success invariant is:

```text
selected = cpu_continuation_calls
cpu_prealign_calls = 0
cpu_forward_calls = 0
cpu_reverse_calls = cpu_continuation_calls
cpu_banded_sw_calls = cpu_continuation_calls
cpu_failures = 0
fallback_calls = 0
error = none
```

Outer attempt receipts separately record argv, environment, source and binary
identity, input/output SHA-256, stdout/stderr, resource usage, GPU samples, and
an artifact manifest. Telemetry cannot turn a failed process into a successful
attempt.

## Stable hq10/hq11 anchors

The formal runner freezes anchors using only the already-known mismatch
coordinates and current source-defined attempt identity:

```text
hq10: rule 5, strand 0, scoreInfo 3, identity round 0,
      target window 512+69, selected best_fallback,
      1-based query 1697-1752, target 525-581, score 68

hq11: rule 12, strand 1, scoreInfo 17, identity round 0,
      target window 2169+84, selected threshold,
      1-based query 726-791, target 2192-2253, score 93
```

These are regression fixtures from consumed Phase 2 evidence, not fresh
promotion data. Query/gene names are never used by the runtime selection path.
