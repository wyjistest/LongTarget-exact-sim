# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Certificate Producer First1

This checkpoint implements the first narrow certificate producer for the new
GPU engine API. It is a synthetic first1 API gate, not a reducing Fasim
runtime, not a first64 gate, and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_certificate_producer_first1 = producer_first1_synthetic_gate
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md
previous_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance
runtime_reduction_enabled = 0
first1_runtime_reduction_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The producer is deliberately limited to the CUDA API surface:

```text
input:
  PreAlignCudaNewEngineScoreInfoTask
  PreAlignCudaNewEngineCandidateGroup
  PreAlignCudaNewEngineReplayAttempt

output:
  PreAlignCudaNewEngineSkippedWorkCertificate
  PreAlignCudaNewEngineCertificateResult
```

It does not consume real Fasim output and does not select final records.

## First1 Producer Gate

The synthetic gate proves that the API can produce a conservative certificate
before D2H and without final CPU output membership:

```text
certificate_producer_active = 1
certificate_valid_before_d2h = 1
final_cpu_output_membership_required_for_certificate = 0
certificate_false_negatives = 0
certificate_missing_required_attempts = 0
skipped_groups = 1
skipped_attempts = 1
conservative_fallback_groups = 0
certificate_cuda_api_gate_pass = 1
```

This is still not the Phase 7.3 runtime reduction gate. It only removes the
previous blocker where the certificate API existed but always reported
`certificate_producer_active = 0`.

## Authority Model

```text
output_authority_changed = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

CPU `aligner.Align()` remains the semantic authority for any future runtime
replay. GPU certificates are proof metadata only.

## Decision

```text
next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go
current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go
```

The next Path B checkpoint must either use this certificate path in a real
first1 shadow runtime that preserves full output and reduces work, or record a
no-go. It must not run first64 before first1 runtime reduction passes.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances Phase 7.2 from API scaffold to certificate producer
surface. It does not close Path A or Path B.
