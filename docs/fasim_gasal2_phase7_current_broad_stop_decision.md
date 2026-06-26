# Fasim GASAL2 Phase 7 Current Broad Stop Decision

This document is the stop checkpoint for the current broad GASAL2/Fasim
architecture family. It does not close the active goal. It records that the
current tested broad sources cannot satisfy Path B.

```text
phase7_current_broad_stop_decision = current_broad_sources_no_go
```

## Authority

```text
CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.
GASAL2 output authority = 0
no GPU endpoint authority
no GPU CIGAR or traceback authority
no broad_replacement workload-matrix row may be added from current evidence.
```

## Stopped Current Sources

```text
co-designed broad replacement-consumer:
  decision = broad_path_current_architecture_no_go
  candidate_vs_baseline = 0.301413x
  align_attempts_not_reduced

attempt-consumer shadow:
  decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go
  digest clean
  candidate_vs_baseline = 0.148434x
  cpu align attempts not reduced

emission-only consumer shadow:
  decision = emission_only_consumer_shadow_correctness_no_go
  align attempts reduced
  triplex_mismatches = 4,404
  candidate_vs_baseline = 0.157653x

frontier early-stop runtime:
  decision = phase7_frontier_early_stop_runtime_first1_no_go
  missing_rows = 7
  extra_rows = 5
  triplex_mismatches = 12

all-attempt early-stop runtime:
  first1 correctness clean
  first64 correctness clean
  align_attempt_reduction = 71,889
  scoreInfo/preAlign work is still CPU work
  wall time is near parity, not a broad win

Gate C current source:
  decision = phase7_gate_c_first1_no_go
  digest_match = 1
  full_rows_equal = 1
  gpu_candidate_scoreinfos = 0
  gpu_candidate_attempts = 0
  scoreinfo_reduced = 0
  current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
  gate_c_first64_allowed = 0
```

## Decision

```text
current_broad_sources_status = stopped
phase7_current_broad_sources_may_continue = 0
phase7_new_architecture_required = 1
phase7_current_broad_stop_reason =
  no current source reduces or replaces scoreInfo/preAlign work and Align-side
  work while preserving the full claimed output contract and beating CPU
  authority
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Allowed Continuation

Path B can continue only with a materially different architecture:

```text
new descriptor source or new consumer architecture
full output/digest clean on the claimed scope
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
candidate wall time beats CPU authority
fallback accounting clean
CPU aligner.Align() remains authority unless separately proven otherwise
```

Otherwise the only completion route is Path A, and Path A requires explicit
user acceptance of the scoped product contract.
