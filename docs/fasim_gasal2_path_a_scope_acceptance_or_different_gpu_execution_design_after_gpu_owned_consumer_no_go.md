# Fasim GASAL2 Path A Scope Acceptance Or Different GPU Execution Design After GPU-Owned Consumer No-Go

This checkpoint executes the fork after the GPU-owned scoreInfo consumer
first1 shadow consumer no-go. It is a docs-only gate. It does not add runtime
code, does not enable work drop, and does not complete the active broad goal.

## Scope

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md
previous_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go
user_scope_acceptance_recorded = 0
scoped_completion_may_close_goal = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A is not recorded as accepted in this checkpoint. The active path remains
Path B.

## Stopped Family

The previous GPU-owned scoreInfo consumer line is stopped:

```text
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate
accepted_gpu_owned_scoreinfo_consumer = 0
accepted_pre_drop_frontier_certificate = 0
certificate_produced_before_work_drop = 0
certificate_consumed_before_cpu_replay_selection = 0
cpu_replay_attempts = baseline_cpu_attempts
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
path_b_gpu_owned_scoreinfo_consumer_family_stopped = 1
```

The stopped line must not be promoted by renaming its fail-closed telemetry,
using final CPU output membership as a runtime proof, or claiming top5-only
evidence as complete-row broad replacement evidence.

## Different Path B Design

Because Path A is not accepted, this checkpoint defines a different Path B
design family:

```text
path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status = design_defined
path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_differs_from_gpu_owned_scoreinfo_consumer = 1
path_b_differs_from_scoreinfo_certificate_engine = 1
path_b_differs_from_post_v5_3_descriptor_stream = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
```

The new family changes the unit of proof. Instead of trying to drop CPU work
from scoreInfo/frontier summaries, the GPU must propose a complete
Fasim-compatible alignment result plus a CPU-checkable certificate:

```text
GPU proposal:
  score
  ref/query end
  ref/query start
  CIGAR path
  scoreInfo/candidate linkage
  original request identity

CPU verifier certificate:
  scoring parameters
  translated query/ref identity
  local maximum witness
  reverse-start witness
  traceback/CIGAR path score witness
  coordinate convention witness
  row identity linkage
```

The CPU verifier is not allowed to trust GASAL2 output by assertion. It must
either prove that the proposed result is Fasim-compatible or fall back to CPU
`aligner.Align()`.

## Why This Is Different

The stopped GPU-owned consumer family observed a candidate frontier but could
not prove that skipped scoreInfo groups or align attempts were output-inert
before the CPU replay decision. The new family is different in three ways:

```text
1. It targets the expensive Align-side DP result directly instead of only
   summarizing scoreInfo/frontier state.

2. It requires a CPU-checkable alignment certificate before any CPU Align work
   can be skipped.

3. It treats GASAL2 endpoint/CIGAR/traceback as untrusted proposal data until
   the CPU verifier and CPU aligner.Align() shadow agree on full rows/digest.
```

This design is allowed only because it starts as a fail-closed proof design.
It is not a claim that direct GASAL2 replacement is already feasible.

## Required Next Gate

```text
next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

The next PR must write the implementation spec for the fail-closed first1
shadow. It must not implement a reducing runtime.

## Required First1 Shadow Spec

The next spec must define:

```text
input descriptor:
  request_id
  query identity
  target identity
  translated sequence digests
  scoring config key
  CPU authority output slot

GPU proposal fields:
  score
  ref_end
  query_end
  ref_start
  query_start
  CIGAR
  traceback status
  GASAL2 status/fallback reason

CPU verifier fields:
  proposal_verified
  verifier_failure_reason
  score_match_vs_cpu_align
  endpoint_match_vs_cpu_align
  cigar_match_vs_cpu_align
  full_row_match_vs_cpu_align
  digest_match_vs_cpu_align

fail-closed telemetry:
  requested
  active
  proposals
  verifier_pass
  verifier_fail
  cpu_align_fallbacks
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
```

## Future Advancement Gates

The broad goal remains open until a later implementation passes all of these
gates:

```text
Phase 7c first1 fail-closed shadow:
  proposals > 0
  verifier_pass > 0 or verifier failure taxonomy complete
  score_mismatches = 0
  endpoint_mismatches = 0
  cigar_mismatches = 0
  full_rows_equal = 1
  digest_match = 1
  runtime_reduction_enabled = 0

Phase 7d first1 reducing runtime:
  verifier is consumed before CPU Align work is skipped
  CPU aligner.Align() fallback is used for unverified proposals
  candidate_align_attempts < reference_align_attempts
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls or scoreInfo work is
    otherwise replaced by a proven GPU source
  full_rows_equal = 1
  digest_match = 1
  fallback_accounting_clean = 1

Phase 7e first64 broad gate:
  full_rows_equal = 1
  digest_match = 1
  candidate_wall_seconds < baseline_wall_seconds
  scoreInfo_prealign_reduced = 1
  align_side_reduced = 1
  fallback_accounting_clean = 1
```

If the first1 fail-closed shadow cannot produce CIGAR/full-row equality, this
new family must stop before any reducing runtime work.

## Forbidden

```text
no real opt-in
no default behavior change
no first64 before first1 passes
no runtime work drop in the design/spec checkpoint
no promotion of the stopped GPU-owned scoreInfo consumer family
no promotion of the stopped scoreInfo certificate-engine family
no promotion of the stopped post-v5.3 descriptor-stream family
no GASAL2 endpoint authority
no GASAL2 CIGAR authority
no GASAL2 traceback authority
no GASAL2 output authority
no GASAL2 digest authority
no completion claim from this checkpoint
```

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```
