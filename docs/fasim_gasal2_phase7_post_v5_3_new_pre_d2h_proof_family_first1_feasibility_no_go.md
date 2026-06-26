# Fasim GASAL2 Phase 7 Post-v5.3 New Pre-D2H Proof Family First1 Feasibility No-Go

This checkpoint records the first feasibility review after
`docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md`.
It is not a runtime implementation and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md
previous_gate = implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance
runtime_default = off
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous decision required a new first1 proof family if Path B continued.
This review checks whether the current pre-D2H descriptor stream can support
that proof family without adding final-output authority or replay-derived
safety.

## Descriptor Stream Reviewed

The current pre-D2H source is:

```text
current_descriptor_stream = PreAlignCudaAttemptDescriptor
```

Its available fields are:

```text
taskIndex
scoreInfoPosition
scoreInfoScore
scoreInfoOrder
attemptOrder
targetStart
cutlength
targetEndRequiredForFallback
ntMinLength
scoringConfigKey
overflowFlag
```

These fields are sufficient to replay CPU `aligner.Align()` attempts from the
legacy-byte CUDA scoreInfo stream. They are not sufficient to prove that a
skipped scoreInfo group or skipped attempt is output-inert before host transfer.

## Missing Proof Inputs

The proof families listed in the previous design require conservative bounds
for skipped work. Those inputs are not present in the current descriptor
stream:

```text
skipped_scoreinfo_score_upper_bound = missing
skipped_attempt_score_upper_bound = missing
skipped_attempt_nt_upper_bound = missing
skipped_attempt_identity_upper_bound = missing
skipped_attempt_stability_upper_bound = missing
task_output_capacity = missing
scoreInfo-local break-state = missing
```

Therefore:

```text
current_descriptor_stream_can_prove_output_inert_skips = 0
```

Using CPU final output after replay to label skipped work remains useful for
offline analysis, but it is not a runtime proof. The runtime cannot decide to
skip work based on a result that is only known after the skipped work has been
replayed or compared externally.

## Acceptance Result

```text
accepted_pre_d2h_proof_families = 0
candidate_proof_false_negatives = unproven
candidate_proof_missing_required_attempts = unproven
candidate_selected_attempts_lt_v5_candidate_align_attempts = unproven
candidate_selected_attempts_lt_reference_align_attempts = unproven
candidate_uses_final_cpu_output_as_runtime_proof = forbidden
```

The current descriptor stream cannot support a new first1 proof-family smoke
that would be meaningfully different from the stopped fixed-prefix,
task-frontier, or aggregate proof-search paths.

## Decision

```text
new_pre_d2h_proof_family_first1_smoke_allowed = 0
reducing_runtime_allowed = 0
do_not_implement_reducing_runtime_from_current_descriptor_stream = 1
do_not_run_first64_from_current_descriptor_stream = 1
different_gpu_execution_design_required = 1
path_a_user_acceptance_required = 1
```

The next valid move is either:

```text
different_gpu_execution_design_required = 1
```

or:

```text
path_a_user_acceptance_required = 1
```

The different design must add a genuinely new pre-D2H proof signal or change
the execution shape enough that skipped work can be proven safe before any
runtime reduction. Reusing the current aggregate proof-search export, fixed
prefixes, first scoreInfo group per task, or final CPU output membership is not
allowed.

## Current Cursor

```text
current_execution_gate = different_gpu_execution_design_or_path_a_scope_acceptance
current_next_pr = fasim_design_different_gpu_execution_design_or_scope_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```
