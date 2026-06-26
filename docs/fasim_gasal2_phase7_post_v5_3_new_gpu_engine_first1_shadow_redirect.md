# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Shadow Redirect

This checkpoint reviews whether an existing Phase 7 v5 runtime can satisfy the
new GPU engine first1 shadow gate. It is a redirect checkpoint, not a runtime
implementation and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md
previous_gate = phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance
runtime_reduction_enabled = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Existing Runtime Reviewed

The existing runtime reviewed here is:

```text
reviewed_existing_runtime = FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY
reviewed_existing_source = PreAlignCudaAttemptDescriptor
existing_v5_cpu_authority_replay_first1_gate_pass = 1
```

That gate is useful evidence for the older v5 descriptor path: first1 replay
can reduce CPU align attempts while preserving output under CPU
`aligner.Align()` authority. It is not evidence that the new engine first1 spec
has been implemented.

## Why It Does Not Satisfy The New Spec

The new first1 spec requires a pre-D2H skipped-work certificate. The existing
`PreAlignCudaAttemptDescriptor` path exports replay descriptors but does not
prove that skipped scoreInfo groups or skipped attempts are output-inert before
host transfer.

```text
existing_v5_cpu_authority_replay_matches_new_engine_spec = 0
reason = missing_pre_d2h_skipped_work_certificate
```

Missing certificate inputs:

```text
skipped_scoreinfo_upper_bound_score = missing
skipped_attempt_upper_bound_score = missing
skipped_attempt_upper_bound_nt = missing
skipped_attempt_upper_bound_identity = missing
skipped_attempt_upper_bound_stability = missing
task_output_capacity_exhausted = missing
scoreinfo_local_break_state = missing
certificate_valid_before_d2h = 0
final_cpu_output_membership_required_for_certificate = forbidden
```

The old v5 path may still be used as historical evidence, but it must not be
relabelled as the new engine.

## Decision

```text
new_gpu_engine_first1_shadow_gate_pass = 0
do_not_relabel_v5_cpu_authority_replay_as_new_engine = 1
do_not_run_first64_from_v5_replay_for_new_engine = 1
do_not_add_broad_replacement_row_from_v5_replay = 1
```

The next valid move remains one of these:

```text
path_a_user_acceptance_required = 1
path_b_new_engine_runtime_required = 1
```

If Path B continues, the next runtime must implement the new engine first1
shadow contract directly: explicit `GpuScoreInfoTask`,
`GpuCandidateGroup`, `GpuReplayAttempt`, conservative skipped-work
certificate, fail-closed counters, and first1 telemetry.

## Current Cursor

```text
next_valid_gate = implement_new_gpu_engine_first1_shadow_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_first1_shadow_runtime_or_path_a_acceptance
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

This checkpoint keeps the broad objective open. It prevents a clean older v5
first1 result from being promoted into a new-engine claim without the required
certificate.
