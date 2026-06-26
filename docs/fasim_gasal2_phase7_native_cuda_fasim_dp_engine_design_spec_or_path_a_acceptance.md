# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine Design Spec Or Path A Acceptance

This checkpoint records the next Path B design after the GASAL2 full-align
verifier family stopped. It is docs-only. It does not add runtime behavior,
does not authorize work drop, and does not complete the active broad goal.

## Scope

```text
phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md
previous_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_native_cuda_fasim_dp_engine_spec_defined = 1
design_family = native_cuda_fasim_dp_certificate_engine
not_gasal2_full_align_verifier_continuation = 1
not_gasal2_align_replacement = 1
not_gpu_owned_scoreinfo_consumer_continuation = 1
not_scoreinfo_certificate_engine_continuation = 1
not_post_v5_3_descriptor_stream_continuation = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A remains available only if the user explicitly accepts the scoped
completion packet in `docs/fasim_gasal2_path_a_scoped_completion_acceptance.md`.
No such acceptance is recorded here. Therefore the active broad objective
stays open.

## Design Boundary

The stopped GASAL2 full-align verifier family produced descriptors but no
GASAL2 full-align proposals that a verifier could consume. This spec therefore
does not continue GASAL2 proposal semantics. The next Path B design must target
Fasim/SSW compatibility directly:

```text
native_scoreinfo_byte_dp_layout
native_forward_score_endpoint_layout
native_reverse_start_layout
native_traceback_cigar_witness_layout
pre_drop_certificate_field_math
consumer_decision_point_before_cpu_align_skip
fallback_accounting_schema
first1_shadow_inputs
first1_shadow_expected_telemetry
```

CPU `aligner.Align()` remains the verifier and fallback authority. GPU
certificate data is only proof material for a later fail-closed consumer gate.
No GPU result is final score, endpoint, CIGAR, traceback, output, or digest
authority.

```text
CPU aligner.Align() remains verifier and fallback authority.
GPU certificate may only prove that CPU work can be skipped at a later gate.
No GPU result is final score, endpoint, CIGAR, traceback, output, or digest authority.
```

## Native DP Components

The design family is a native CUDA/Fasim-compatible DP certificate engine. It
must model Fasim's existing byte scoreInfo, forward/reverse alignment, and
traceback contracts rather than trying to adapt GASAL2's alignment output.

```text
FasimByteScoreInfoTile:
  request_id
  scoreinfo_id
  translated_query_digest
  translated_target_window_digest
  byte_saturation_mode
  window_of_5_cluster_id
  legacy_request_order

FasimForwardEndpointWitness:
  request_id
  candidate_id
  score
  ref_end
  query_end
  local_max_tie_policy_id
  local_max_witness

FasimReverseStartWitness:
  request_id
  candidate_id
  ref_start
  query_start
  reverse_start_policy_id
  reverse_start_witness

FasimTracebackCigarWitness:
  request_id
  candidate_id
  traceback_policy_id
  cigar_op_count
  cigar_bytes
  cigar_encoding_digest
```

Each component must be tied to the same legacy request order that CPU Fasim
would use. A later runtime gate may only consume a certificate before any CPU
Align skip if the certificate can be checked without using final CPU output
membership or final digest membership.

## Certificate Schema

The certificate is not final output. It is a compact proof object that lets a
later CPU-side consumer decide whether a request is safe to skip or must fall
back to full CPU replay.

```text
FasimDpCertificate:
  request_id
  scoreinfo_id
  candidate_id
  legacy_request_order
  translated_query_digest
  translated_target_window_digest
  byte_saturation_mode
  window_of_5_cluster_id
  local_max_tie_policy_id
  reverse_start_policy_id
  traceback_policy_id
  cigar_encoding_digest
  certificate_valid_before_cpu_align_skip
  certificate_consumed_before_cpu_align_skip = 0
  certificate_consumed_before_cpu_replay_selection = 0
```

The first spec checkpoint still forbids consumption:

```text
certificate_consumed_before_cpu_align_skip = 0
certificate_consumed_before_cpu_replay_selection = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

The later consumer must fail closed on any uncertainty:

```text
fallback_on_scoreinfo_byte_mismatch = 1
fallback_on_endpoint_mismatch = 1
fallback_on_reverse_start_mismatch = 1
fallback_on_cigar_mismatch = 1
fallback_on_row_identity_uncertainty = 1
fallback_on_missing_required_attempt = 1
fallback_on_certificate_false_negative = 1
```

## First1 Shadow Contract

The next runtime checkpoint is first1-only and fail-closed. It may observe
native CUDA/Fasim DP certificate production, but it must not skip CPU work.

```text
required_env = FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_native_cuda_fasim_dp_engine_
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

Expected first1 telemetry:

```text
requested = 1
active = 1
native_scoreinfo_tiles
forward_endpoint_witnesses
reverse_start_witnesses
traceback_cigar_witnesses
certificates
certificate_false_negatives
missing_required_attempts
scoreinfo_byte_mismatches
endpoint_mismatches
reverse_start_mismatches
cigar_mismatches
full_row_mismatches
digest_mismatches
cpu_align_fallbacks
```

The first1 shadow is acceptable only as a proof-producing scaffold if all
certificate and equivalence gates are clean:

```text
requested = 1
active = 1
certificates > 0
certificate_false_negatives = 0
missing_required_attempts = 0
scoreinfo_byte_mismatches = 0
endpoint_mismatches = 0
reverse_start_mismatches = 0
cigar_mismatches = 0
full_rows_equal = 1
digest_match = 1
gate_first1_shadow_pass = 1
```

Even a clean first1 shadow still does not prove runtime reduction:

```text
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
```

A later runtime-reduction gate must additionally prove:

```text
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
candidate_wall_seconds < baseline_wall_seconds
fallback_accounting_clean = 1
```

## Decision

```text
phase7_native_cuda_fasim_dp_engine_design_spec_status = spec_defined
path_b_native_cuda_fasim_dp_engine_spec_defined = 1
path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines the next genuinely different Path B design family and
allows only a first1 fail-closed shadow scaffold. It does not prove that the
engine is implementable, equivalent, fast, or complete.

## Forbidden

```text
no real opt-in
no runtime reduction in this design/spec checkpoint
no runtime work drop in this design/spec checkpoint
no first64 before first1 fail-closed shadow passes
no GASAL2 proposal semantics
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
```

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU score authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```
