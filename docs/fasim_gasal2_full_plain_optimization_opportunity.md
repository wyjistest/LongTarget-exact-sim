# Fasim GASAL2 Full Plain Optimization Opportunity

This checkpoint summarizes the remaining optimization headroom after the
CPU-vs-GASAL2 full plain chr22 gate.

It does not change runtime behavior. It does not claim full-row equivalence.
The accepted contract remains:

```text
CPU full plain .lite
vs
GASAL2 full plain .lite

Required:
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
  GASAL2 active = 1
  GASAL2 fallbacks = 0

Not required:
  full row-set equality
```

## chr22 Result Used

Input result:

```text
work = .tmp/measure_cpu_vs_gasal2_full_chr22_plain
```

Measured values:

```text
cpu_wall_seconds = 2275.937806
gasal2_wall_seconds = 70.154883
run_wall_speedup = 32.441616

gasal2_requests = 21,802,059
gasal2_traceback_requests = 6,910,419
traceback_requests_per_gasal2_request = 0.316962
traceback_requests_per_output_row = 17.772706

gasal2_total_seconds = 29.463600
gasal2_extend_wall_seconds = 40.421600
gasal2_convert_wall_seconds = 8.354580
exact_column_wall_seconds = 11.532200
output_write_seconds = 0.568368
flush_total_seconds = 64.488200

top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
full_rows_equal = false
```

## Decision

```text
decision = traceback_reduction_is_primary_remaining_optimization
next_action = prototype_or_characterize_top5_limited_traceback
```

The output writer is not the useful target now: `output_write_seconds` is less
than one second in a 70 second run. Archive/compression work remains useful for
storage, but it cannot explain or materially improve this fast-path wall time.

The remaining wall time is dominated by the GASAL2 flush/traceback path and host
orchestration around it. The strongest next optimization candidate is therefore
to reduce how many candidate alignments require traceback under the top5
contract, while keeping the three top5 summaries identical.

## Hard Gate For Any Follow-up

Any traceback-limited prototype must report:

```text
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
gasal2_fallbacks = 0
gasal2_traceback_requests reduced materially
wall_seconds improves
```

It must not claim:

```text
full .lite/TFOsorted equivalence
aligner.Align() replacement
endpoint/CIGAR/traceback authority
```

## Check

```bash
WORK=.tmp/measure_cpu_vs_gasal2_full_chr22_plain \
make check-fasim-gasal2-full-plain-optimization-opportunity
```
