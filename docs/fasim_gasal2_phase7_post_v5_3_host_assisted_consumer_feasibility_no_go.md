# Fasim GASAL2 Phase 7 Post-v5.3 Host-Assisted Consumer Feasibility No-Go

This is a diagnostic checkpoint, not a completion claim.

## Scope

The probe tested whether a host-assisted consumer summary could reduce the v5
descriptor replay before investing in a true GPU-side consumer summary kernel.

```text
env:
  FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY=1

workload:
  NEAT1 first1

source:
  v5 CUDA attempt descriptors

authority:
  CPU aligner.Align()
```

The probe deliberately does not claim strict Phase 5 progress:

```text
gpu_consumer_reduces_before_host_transfer = 0
gpu endpoint/CIGAR/traceback/output authority = 0
```

## Result

The host-assisted feasibility probe is no-go for the broad path.

Observed telemetry:

```text
requested = 1
active = 0
host_assisted = 1
source_is_v5_descriptors = 1
gpu_consumer_reduces_before_host_transfer = 0
host_selected_attempts = 0
prefix_descriptor_attempts = 0
reference_align_attempts = 2872
candidate_align_attempts = 0
v5_candidate_align_attempts = 2872
candidate_align_attempts_less_than_v5 = 0
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 0
digest_match = 0
full_rows_equal = 0
gate_first1_pass = 0
```

The direct cause is the GASAL2 long-query guard:

```text
benchmark.fasim_gasal2_length_guard_fallbacks = 1
benchmark.fasim_gasal2_length_guard_last_query_len = 22767
benchmark.fasim_gasal2_length_guard_max_query_len = 2812
```

Because GASAL2 score-only selection cannot run for this NEAT1 long query, the
host-assisted selector produces no selected attempts. CPU replay receives no
prefix descriptors, so the candidate output is only the header and the lite
digest differs from the CPU baseline.

## Decision

```text
host-assisted consumer feasibility:
  no-go for NEAT1 first1 broad path

strict post-v5.3 GPU consumer summary:
  not reached

broad objective:
  still open

must_not_call_update_goal_complete:
  1
```

This result blocks the planned path:

```text
v5 descriptors
  -> GASAL2 score-only host selection
  -> scoreInfo-local prefix replay
  -> future GPU-side consumer summary
```

It fails before the strict GPU-side requirement because the long-query GASAL2
score-only selector cannot produce the summary rows needed for CPU replay.

## Next Valid Work

Do not continue by loosening the gate or by treating empty selected attempts as
a reduction.

The next Path B design must be materially different:

```text
1. avoid GASAL2_MAX_QUERY_LEN-dependent score-only selection for NEAT1-like
   long queries, or

2. use a scoreInfo-compatible GPU consumer that works on the same legacy byte
   scoreInfo stream without GASAL2 long-query score-only calls, or

3. return to Path A only if the user explicitly accepts scoped completion.
```

Any new broad path still has to pass:

```text
full_rows_equal = 1
digest_match = 1
candidate_wall_seconds < baseline_wall_seconds
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```
