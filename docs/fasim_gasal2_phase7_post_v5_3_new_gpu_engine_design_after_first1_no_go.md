# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Design After First1 No-Go

This checkpoint is the Path B design response after the current new GPU
engine certificate-producer line failed the first1 reducing-runtime gate. It
is docs/spec only. It does not add runtime behavior and does not complete the
active goal.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md
previous_gate = path_a_scoped_acceptance_or_new_engine_design_doc
runtime_reduction_enabled = 0
runtime_pr_allowed = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous checkpoint proved that the available certificate producer is not
a real Fasim runtime work-drop path:

```text
first1_runtime_reduction_gate_pass = 0
real_fasim_runtime_certificate_source = 0
real_fasim_runtime_work_drop_path = 0
prealign_cuda_emit_new_engine_skipped_work_certificates_runtime_call_count = 0
```

Therefore the next Path B step cannot reuse that line as a runtime
implementation.

## Design Decision

Path B may continue only with a real-source GPU engine spec:

```text
design_family = real_source_fasim_compatible_gpu_scoreinfo_attempt_engine
not_synthetic_certificate_producer_continuation = 1
not_v5_cpu_authority_replay_relabel = 1
not_current_descriptor_stream_continuation = 1
requires_real_fasim_runtime_certificate_source = 1
requires_real_fasim_runtime_work_drop_point = 1
```

The design must move the certificate source into the real Fasim scoreInfo /
preAlign execution path before work is dropped. A synthetic API call, offline
frontier export, final CPU output membership, or host-side proof after a full
descriptor dump is not runtime proof.

## Required Real-Source Spec

The next Path B artifact must be an implementation-ready first1 spec. It must
define all of these before code:

```text
real_runtime_hook_location
scoreInfo_task_construction_point
gpu_input_layout
gpu_candidate_group_layout
gpu_replay_attempt_layout
certificate_producer_location
certificate_consumer_location
work_drop_decision_point
fallback_to_full_cpu_replay_point
telemetry_namespace
```

The spec must also define the exact proof fields:

```text
skipped_scoreinfo_upper_bound_score
skipped_attempt_upper_bound_score
skipped_attempt_upper_bound_nt
skipped_attempt_upper_bound_identity
skipped_attempt_upper_bound_stability
scoreinfo_local_break_state
task_output_capacity
certificate_valid_before_d2h = 1
final_cpu_output_membership_required_for_certificate = 0
```

## First1 Gate

The first runnable Path B PR after this checkpoint may be first1 shadow only,
and only after the real-source spec exists. It must fail closed unless it has a
real runtime certificate source and a real work-drop point:

```text
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 1
runtime_certificate_is_synthetic = 0
fallback_to_full_cpu_replay_on_uncertainty = 1
```

It may advance only if all of these pass on the same first1 input:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
certificate_false_negatives = 0
missing_required_attempts = 0
candidate_wall_seconds < baseline_wall_seconds
```

Passing first1 only permits a first64 broad-gate proposal. It does not
complete the broad objective.

## Stop Rules

```text
do_not_run_first64_before_real_source_first1_pass = 1
do_not_reuse_synthetic_certificate_producer_as_runtime_proof = 1
do_not_use_final_cpu_output_membership_as_runtime_proof = 1
do_not_relabel_v5_cpu_authority_replay_as_new_engine = 1
do_not_promote_gpu_endpoint_cigar_traceback_output_digest_authority = 1
```

If the next first1 spec cannot define a real source and work-drop point, Path
B remains open and no runtime PR is allowed.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Current Decision

This checkpoint satisfies the current scope/design gate without closing the
goal:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_real_source_design_checkpoint_defined = 1
path_b_runtime_pr_allowed = 0
current_execution_gate = phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance
```

If Path A is explicitly accepted, move to the scoped close packet. Otherwise
Path B must continue with the real-source first1 spec before any runtime code.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by replacing the failed synthetic
certificate runtime line with a real-source design requirement. It does not
close Path A or Path B.
