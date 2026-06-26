# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate Design Spec Or Path A Acceptance

This checkpoint defines the next Path B design after the native CUDA/Fasim DP
engine family stopped. It is docs-only. It does not add runtime behavior, does
not authorize work drop, and does not complete the active broad goal.

## Scope

```text
phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md
previous_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_gpu_upper_bound_reject_certificate_spec_defined = 1
design_family = gpu_upper_bound_reject_certificate_engine
not_native_cuda_fasim_dp_engine_continuation = 1
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

The stopped families all tried to create positive proof: a scoreInfo source, a
candidate consumer, a full-align proposal, or a native DP certificate. This
design changes the proof shape. The GPU may only produce conservative reject
certificates that prove a scoreInfo/preAlign group or Align-side candidate
cannot possibly contribute a valid output row.

```text
proof_shape = negative_upper_bound_reject_certificate
gpu_accepts_rows = 0
gpu_emits_final_rows = 0
gpu_endpoint_cigar_traceback_required = 0
cpu_authority_replay_required = 1
fallback_to_full_cpu_replay_on_uncertainty = 1
```

The design is useful only if a later gate proves that rejected work is
output-inert before CPU scoreInfo/preAlign or CPU Align work is performed.
This spec does not consume certificates.

## Bound Math

The first certificate family is deliberately conservative. For each translated
query and target window, the GPU computes an upper bound on possible matching
nucleotides and possible local-alignment score:

```text
max_possible_nt = sum_base min(query_base_count[base], target_base_count[base])
max_possible_score = max_possible_nt * max_positive_match_score
```

This ignores mismatch and gap penalties, so it is an overestimate. It can only
reject work when the overestimate is already below the required threshold:

```text
safe_reject_by_nt = max_possible_nt < required_nt_min
safe_reject_by_score = max_possible_score < required_score_threshold
reject_safe = safe_reject_by_nt or safe_reject_by_score
```

Any unsupported translation, ambiguous base handling uncertainty, unknown
threshold, or scoring-config mismatch must disable rejection and fall back to
the full CPU path:

```text
fallback_on_unsupported_alphabet = 1
fallback_on_ambiguous_bound_uncertainty = 1
fallback_on_unknown_threshold = 1
fallback_on_scoring_config_mismatch = 1
fallback_on_sequence_digest_mismatch = 1
```

Optional qgram or seed bounds may be logged as diagnostics, but they may not be
used for runtime rejection until a later proof shows they are conservative for
Fasim's translated sequence and scoring contract:

```text
qgram_bound_diagnostic_only = 1
qgram_bound_may_reject_runtime = 0
```

## Descriptor Schema

The design requires descriptors before CPU work is dropped. A descriptor must
identify the exact legacy work unit that may be rejected:

```text
UpperBoundRejectDescriptor:
  request_id
  group_id
  scoreinfo_id
  candidate_id
  legacy_request_order
  translated_query_digest
  translated_target_window_digest
  target_window_offset
  target_window_length
  scoring_config_key
  required_nt_min
  required_score_threshold
  output_slot_id
```

Descriptors may be emitted at two levels:

```text
scoreinfo_prealign_group_descriptor:
  can reduce scoreInfo/preAlign work only after false-negative-free proof

align_candidate_descriptor:
  can reduce Align-side work only after false-negative-free proof
```

The broad objective requires both reduction paths to be proven before any broad
replacement claim:

```text
requires_scoreinfo_prealign_reduction_plan = 1
requires_align_side_reduction_plan = 1
```

## Certificate Schema

The certificate is a CPU-checkable proof object. It is not final output and it
is not a row accept decision.

```text
UpperBoundRejectCertificate:
  request_id
  group_id
  scoreinfo_id
  candidate_id
  legacy_request_order
  translated_query_digest
  translated_target_window_digest
  scoring_config_key
  query_base_counts
  target_base_counts
  max_possible_nt
  max_possible_score
  required_nt_min
  required_score_threshold
  safe_reject_by_nt
  safe_reject_by_score
  reject_safe
  certificate_valid_before_scoreinfo_or_align_skip
  certificate_consumed_before_scoreinfo_skip = 0
  certificate_consumed_before_align_skip = 0
```

The CPU checker must be able to recompute the certificate math without using
final output membership or final digest membership:

```text
cpu_checker_recomputes_counts = 1
cpu_checker_recomputes_bounds = 1
cpu_checker_does_not_use_final_output_membership = 1
cpu_checker_does_not_use_final_digest_membership = 1
```

## First1 Shadow Contract

The next runtime checkpoint is first1-only and fail-closed. It may produce and
log certificates, but it must not skip CPU work.

```text
required_env = FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_upper_bound_reject_
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

Expected first1 telemetry:

```text
requested = 1
active = 1
upper_bound_descriptors
upper_bound_certificates
reject_candidates_shadow
would_reject_scoreinfo_groups
would_reject_align_attempts
certificate_false_negatives
baseline_rows_in_rejected_groups
baseline_rows_in_rejected_attempts
unsupported_descriptors
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
```

The first1 shadow is acceptable only if the negative certificate is
false-negative-free while CPU authority still performs all work:

```text
requested = 1
active = 1
upper_bound_descriptors > 0
upper_bound_certificates > 0
certificate_false_negatives = 0
baseline_rows_in_rejected_groups = 0
baseline_rows_in_rejected_attempts = 0
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
phase7_gpu_upper_bound_reject_certificate_design_spec_status = spec_defined
path_b_gpu_upper_bound_reject_certificate_spec_defined = 1
path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint defines a different Path B family and allows only a first1
fail-closed shadow scaffold. It does not prove that the certificate rejects
enough work, that it is fast, or that the broad objective is complete.

## Forbidden

```text
no real opt-in
no runtime reduction in this design/spec checkpoint
no runtime work drop in this design/spec checkpoint
no first64 before first1 fail-closed shadow passes
no GPU accept decision
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no qgram runtime rejection without a conservative proof
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
