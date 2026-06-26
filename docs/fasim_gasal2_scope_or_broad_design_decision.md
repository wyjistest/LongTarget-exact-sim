# Fasim GASAL2 Scope Or Broad Design Decision

This is the current decision packet for the active GASAL2/Fasim roadmap goal.
It records that the user accepted Path A scoped completion. It does not claim
the broad `aligner.Align()` replacement objective is complete.

## Current State

```text
scope_or_broad_design_decision_packet = defined
scope_or_broad_design_decision_required = 0
path_a_user_acceptance_required = 0
path_a_user_acceptance_recorded = 1
path_b_new_broad_architecture_required = 0
current_decision = path_a_scoped_completion_accepted
broad_objective_status = open
active_goal_completion_status = complete_scoped_path_a
completion_guard_cleared = 1
must_not_call_update_goal_complete = 0
```

The current v4 GPU legacy-byte scoreInfo source replay path is stopped for
broad completion:

```text
path_b_current_v4_source_replay_status = stopped_performance_no_go
current_v4_source_replay_must_not_continue = 1
broad_replacement_row_allowed = 0
gpu_endpoint_cigar_traceback_output_authority = 0
```

## Path A Choice

```text
path_a_choice = accept_scoped_completion
path_a_acceptance_document =
  docs/fasim_gasal2_path_a_scoped_completion_acceptance.md
```

Path A is accepted:

```text
The user explicitly accepts the narrowed scoped product contract.
The acceptance document records that acceptance.
Phase 0, Phase 1, Phase 5, Phase 6, and Phase 8 gates are rerun.
The goal may close only if scoped_completion_may_close_goal = 1.
```

Path A does not claim broad `aligner.Align()` replacement, long-query
NEAT1/MALAT1 production equivalence, GPU endpoint authority, GPU CIGAR
authority, GPU traceback authority, or GPU output authority.

## Path B Choice

```text
path_b_choice = pursue_different_gpu_execution_design
```

If Path B is selected in the future:

```text
Start a different GPU execution design.
Do not continue current v4 source replay.
Do not add a broad_replacement workload-matrix row before broad evidence passes.
Keep CPU aligner.Align() as score/endpoint/traceback/CIGAR/output authority.
```

The minimum future Path B evidence remains:

```text
full row-set/digest equality
candidate_wall_seconds < baseline_wall_seconds
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback accounting clean
gpu_endpoint_cigar_traceback_output_authority = 0
```

## Current Decision

```text
current_decision = path_a_scoped_completion_accepted
active_goal_completion_status = complete_scoped_path_a
```

Call `update_goal complete` only after the Path A acceptance, Phase 8, and
current-state gates pass. This close is scoped Path A completion, not broad
replacement completion.
