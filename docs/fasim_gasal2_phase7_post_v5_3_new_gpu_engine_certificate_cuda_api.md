# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Certificate CUDA API

This checkpoint adds the fail-closed CUDA API surface for the new GPU engine
skipped-work certificate. It is not a certificate producer, not a first1 pass,
not a reducing runtime, and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_certificate_cuda_api = fail_closed_api_scaffold
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md
previous_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance
required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_CERTIFICATE_CUDA_API
telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_
new_cuda_api = prealign_cuda_emit_new_engine_skipped_work_certificates
runtime_reduction_enabled = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The API is default-off. When requested, it records that the new certificate API
exists but that no certificate producer is active yet.

## CUDA Data Surface

The API names the new-engine records from the first1 spec without reusing the
old v5 replay stream as a pass:

```text
GpuScoreInfoTask -> PreAlignCudaNewEngineScoreInfoTask
GpuCandidateGroup -> PreAlignCudaNewEngineCandidateGroup
GpuReplayAttempt -> PreAlignCudaNewEngineReplayAttempt
skipped-work certificate -> PreAlignCudaNewEngineSkippedWorkCertificate
```

Required certificate fields:

```text
skipped_scoreinfo_upper_bound_score
skipped_attempt_upper_bound_score
skipped_attempt_upper_bound_nt
skipped_attempt_upper_bound_identity
skipped_attempt_upper_bound_stability
task_output_capacity_exhausted
scoreinfo_local_break_state
certificate_valid_before_d2h
final_cpu_output_membership_required_for_certificate
```

The current implementation is deliberately fail-closed:

```text
certificate_producer_active = 0
certificate_valid_before_d2h = 0
final_cpu_output_membership_required_for_certificate = 0
certificate_cuda_api_gate_pass = 0
```

This is a valid API checkpoint only. It does not satisfy Phase 7.2's producer
pass condition.

## Runtime Telemetry Contract

Expected requested telemetry:

```text
requested = 1
active = 0
certificate_producer_active = 0
certificate_valid_before_d2h = 0
final_cpu_output_membership_required_for_certificate = 0
skipped_groups = 0
skipped_attempts = 0
conservative_fallback_groups = 0
certificate_false_negatives = 0
certificate_missing_required_attempts = 0
skipped_scoreinfo_upper_bound_score = 0
skipped_attempt_upper_bound_score = 0
skipped_attempt_upper_bound_nt = 0
skipped_attempt_upper_bound_identity = 0
skipped_attempt_upper_bound_stability = 0
task_output_capacity_exhausted = 0
scoreinfo_local_break_state = 0
runtime_reduction_enabled = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
certificate_cuda_api_gate_pass = 0
```

## Authority Model

```text
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

CPU `aligner.Align()` remains the semantic authority. GPU certificates are not
endpoint, CIGAR, traceback, output, or digest authority.

## Decision

```text
certificate_cuda_api_gate_pass = 0
certificate_producer_first1_required = 1
path_a_user_acceptance_required = 1
next_valid_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance
```

The next Path B PR must implement a real pre-D2H certificate producer for
first1 or record why it cannot be done. It must not run first64 from this API
scaffold.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the current cursor from API definition to certificate
producer work. It does not prove Path B and does not close the active goal.
