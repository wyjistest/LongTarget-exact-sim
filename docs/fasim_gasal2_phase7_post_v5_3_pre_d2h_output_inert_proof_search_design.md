# Fasim GASAL2 Phase 7 Post-v5.3 Pre-D2H Output-Inert Proof Search Design

This document defines the next Path B design checkpoint after the stronger
task-frontier certificate feasibility no-go. It is a proof-search design only;
it does not add runtime behavior and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined
phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = design_only
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md
previous_status = stronger_task_frontier_certificate_feasibility_no_go
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why This Exists

The current stronger task-frontier certificate cannot be implemented as written:

```text
phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 0
do_not_implement_current_stronger_task_frontier_runtime = 1
```

The missing piece is not another selector. The missing piece is a pre-D2H proof
that skipped scoreInfo groups or attempts cannot affect full output.

Therefore the next Path B work must first search for a proof signal before
writing another reducing runtime.

## Design Goal

Build a diagnostic proof-search artifact for NEAT1 first1 that joins:

```text
pre-D2H descriptor fields
task / scoreInfo / attempt ordering
CPU-authority replay labels
external output row membership
```

The artifact may use CPU output labels only for offline discovery and
false-negative auditing. A future runtime proof may not depend on final CPU
output after replay.

## Candidate Proof Families

The proof search may evaluate only proof families that could be checked before
D2H in a future implementation:

```text
score upper bound dominance
nt upper bound dominance
identity/stability upper bound dominance
target-end fallback impossibility
task-local output capacity dominance
scoreInfo-local break-state dominance
bounded full-replay fallback when proof is unavailable
```

It must not evaluate these as passing proof families:

```text
first scoreInfo group per task
fixed prefix per scoreInfo
arbitrary sparse subset
final CPU output membership
post-replay digest equality
top5-only equality
```

## First Export Gate

The next implementation, if pursued, is a default-off diagnostic export:

```text
next_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1

next_required_gate =
  pre_d2h_output_inert_proof_search_first1_export
```

The first1 export gate may pass only if:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
proof_search_rows > 0
task_count > 0
scoreinfo_count > 0
attempt_count > 0
label_source = cpu_authority_external_output
runtime_reduction_enabled = 0
gpu_output_authority = 0
```

This gate is not allowed to claim speedup or broad replacement.

## Proof Acceptance Gate

A discovered proof candidate may advance to a runtime design only if the
first1 proof audit shows:

```text
candidate_proof_false_negatives = 0
candidate_proof_missing_required_attempts = 0
candidate_selected_attempts < v5_candidate_align_attempts
candidate_selected_attempts < reference_align_attempts
candidate_fallback_to_full_replay_for_unproven_tasks = allowed
candidate_uses_final_cpu_output_as_runtime_proof = 0
```

Then first64 proof-audit characterization is required before any reducing
runtime:

```text
first64_candidate_proof_false_negatives = 0
first64_candidate_selected_attempts < v5_candidate_align_attempts
first64_candidate_selected_attempts < reference_align_attempts
first64_runtime_reduction_enabled = 0
```

## Runtime Boundary

This design does not authorize:

```text
real reduction
first64 reducing runtime
broad_replacement workload matrix row
GPU endpoint authority
GPU CIGAR authority
GPU traceback authority
GPU output authority
GPU digest authority
```

Any future reducing runtime must be a separate checkpoint after proof audit
passes.

## Stop Conditions

Stop this proof-search line if any of these occur:

```text
no pre-D2H proof family has false negatives = 0
only final CPU output can explain safe skipped work
proof keeps all v5 attempts
proof reduces only top5 but changes full output
proof requires GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined
phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1
phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0
next_required_gate = pre_d2h_output_inert_proof_search_first1_export
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
