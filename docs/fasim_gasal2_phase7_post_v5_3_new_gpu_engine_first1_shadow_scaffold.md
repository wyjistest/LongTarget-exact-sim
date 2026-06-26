# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Shadow Scaffold

This checkpoint adds a fail-closed runtime scaffold for the new GPU engine
first1 shadow gate. It is not a first1 pass, not a reducing runtime, and not a
completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold = fail_closed
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md
previous_gate = implement_new_gpu_engine_first1_shadow_or_path_a_acceptance
required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold is default-off. When requested, it records that the new engine
first1 shadow path has no certificate producer yet and therefore fails closed
to CPU authority.

## Runtime Telemetry Contract

Expected fail-closed telemetry:

```text
requested = 1
active = 0
gpu_scoreinfo_tasks = 0
gpu_candidate_groups = 0
gpu_replay_attempts = 0
gpu_skipped_groups = 0
gpu_skipped_attempts = 0
cpu_replay_attempts = 0
baseline_cpu_attempts = 0
missing_certificate_producer = 1
certificate_valid_before_d2h = 0
final_cpu_output_membership_required_for_certificate = 0
fallback_on_missing_bound = 1
fallback_to_full_cpu_replay = 1
certificate_false_negatives = 0
missing_required_attempts = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
full_rows_equal = 0
digest_match = 0
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
gate_first1_pass = 0
```

These zero equality fields are not mismatch evidence. They mean the scaffold
does not run a candidate replay and therefore cannot claim the first1 gate.

## New Engine Data Model Reminder

This scaffold reserves the first1 runtime surface for the data model from the
spec checkpoint:

```text
GpuScoreInfoTask
GpuCandidateGroup
GpuReplayAttempt
```

The old v5 CPU-authority replay uses `PreAlignCudaAttemptDescriptor`. It must
not be relabelled as this new engine.

## Decision

```text
new_gpu_engine_first1_shadow_gate_pass = 0
certificate_cuda_api_required = 1
path_a_user_acceptance_required = 1
next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance
```

The next Path B PR must add the certificate-producing CUDA API or record why
that API cannot be implemented. It must not run first64 from this fail-closed
scaffold.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint makes Phase 7.1 executable and observable. It does not prove
Path B and does not close the active goal.
