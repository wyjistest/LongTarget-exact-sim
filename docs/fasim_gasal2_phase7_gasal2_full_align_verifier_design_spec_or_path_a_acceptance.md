# Fasim GASAL2 Phase 7 Full-Align Verifier Design Spec Or Path A Acceptance

This checkpoint accepts the next Path B design spec after the GPU-owned
scoreInfo consumer no-go fork. It is docs-only. It does not add a reducing
runtime, does not enable work drop, and does not complete the active broad
goal.

## Scope

```text
phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md
previous_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_full_align_verifier_spec_defined = 1
path_b_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_differs_from_gpu_owned_scoreinfo_consumer = 1
path_b_differs_from_scoreinfo_certificate_engine = 1
path_b_differs_from_post_v5_3_descriptor_stream = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A is still not accepted. The active path remains Path B.

## Design Intent

The stopped scoreInfo/frontier families could not prove before CPU replay that
skipped scoreInfo groups or skipped Align attempts were output-inert. This
design changes the unit of proof:

```text
GASAL2 produces untrusted full-align proposal data.
CPU verifier checks the proposal before CPU Align work can be skipped.
CPU aligner.Align() remains the shadow and fallback authority.
Runtime reduction is forbidden until a later first1 reducing gate accepts the
  verifier certificate.
```

The design is not a direct GASAL2 replacement claim. GASAL2 endpoint, CIGAR,
traceback, output, and digest fields are proposal data only.

## Input Descriptor

The first implementation gate must define a compact descriptor for each
alignment request:

```text
FullAlignVerifierRequest:
  request_id
  query_id
  target_id
  target_offset
  target_length
  translated_query_digest
  translated_target_window_digest
  scoring_config_key
  gap_config_key
  scoreinfo_group_id
  candidate_id
  output_slot_id
  legacy_request_order
```

Required descriptor properties:

```text
descriptor_identity_stable = 1
descriptor_uses_final_cpu_output_membership = 0
descriptor_uses_final_digest = 0
descriptor_allows_cpu_authority_replay = 1
descriptor_can_map_back_to_original_request = 1
```

## GPU Proposal Schema

The GPU proposal is the data GASAL2 claims for an alignment request. It is not
authority.

```text
Gasal2FullAlignProposal:
  request_id
  proposal_status
  proposal_fallback_reason
  score
  ref_end
  query_end
  ref_start
  query_start
  cigar_op_count
  cigar_bytes
  traceback_status
  traceback_score_witness
  local_max_witness
  reverse_start_witness
  scoring_config_key
  translated_query_digest
  translated_target_window_digest
```

Required proposal rules:

```text
proposal_may_be_missing = 1
proposal_missing_means_cpu_align_fallback = 1
proposal_score_authority = 0
proposal_endpoint_authority = 0
proposal_cigar_authority = 0
proposal_traceback_authority = 0
proposal_output_authority = 0
proposal_digest_authority = 0
```

## CPU Verifier Certificate

The CPU verifier certificate is the only possible bridge from an untrusted
proposal to a later CPU Align work-drop decision. The first implementation is
still shadow-only and must not consume the certificate for work drop.

```text
FullAlignVerifierCertificate:
  request_id
  proposal_seen
  proposal_verified
  verifier_failure_reason
  descriptor_identity_match
  scoring_config_match
  translated_query_digest_match
  translated_target_window_digest_match
  local_max_witness_verified
  reverse_start_witness_verified
  traceback_cigar_witness_verified
  coordinate_convention_verified
  row_identity_linkage_verified
  score_match_vs_cpu_align
  endpoint_match_vs_cpu_align
  cigar_match_vs_cpu_align
  full_row_match_vs_cpu_align
  digest_match_vs_cpu_align
```

The verifier must fail closed:

```text
verifier_failure_means_cpu_align_fallback = 1
certificate_consumed_before_cpu_align_skip = 0
certificate_consumed_before_cpu_replay_selection = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

## Failure Taxonomy

The first1 fail-closed shadow must report failure reasons precisely enough to
decide whether this design family can continue:

```text
verifier_failure_reason:
  none
  no_gpu_proposal
  gasal2_launch_or_allocation_failed
  unsupported_query_length
  unsupported_target_length
  unsupported_scoring_config
  proposal_status_failed
  descriptor_identity_mismatch
  translated_sequence_digest_mismatch
  scoring_config_mismatch
  score_mismatch
  endpoint_mismatch
  reverse_start_mismatch
  cigar_mismatch
  traceback_witness_mismatch
  coordinate_convention_mismatch
  row_identity_mismatch
  verifier_internal_error
```

Any non-`none` reason keeps CPU `aligner.Align()` as authority for that
request.

## First1 Fail-Closed Shadow Telemetry

The next runtime checkpoint may only collect first1 fail-closed shadow
telemetry:

```text
required_env = FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_full_align_verifier_
requested
active
descriptors
proposals
proposal_failures
verifier_pass
verifier_fail
cpu_align_fallbacks
score_mismatches
endpoint_mismatches
cigar_mismatches
full_row_mismatches
digest_mismatches
full_rows_equal
digest_match
missing_rows
extra_rows
triplex_mismatches
runtime_reduction_enabled
runtime_work_drop_enabled
gpu_endpoint_cigar_traceback_output_authority
gpu_output_digest_authority
```

Pass conditions for the first1 shadow:

```text
requested = 1
active = 1
proposals > 0
verifier_pass > 0 or verifier failure taxonomy complete
score_mismatches = 0
endpoint_mismatches = 0
cigar_mismatches = 0
full_rows_equal = 1
digest_match = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gpu_endpoint_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
gate_first1_shadow_pass = 1
```

## Future Reducing Gate

Only after the first1 fail-closed shadow passes may a separate first1 reducing
runtime be proposed. That future gate must prove:

```text
uses_cpu_verifier_certificate = 1
verifier_consumed_before_cpu_align_skip = 1
candidate_align_attempts < reference_align_attempts
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
external_digest_match = 1
external_full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

The broad goal still cannot close until a first64 or larger broad gate also
passes with wall-time win, scoreInfo/preAlign reduction, Align-side reduction,
fallback accounting clean, and full output equality.

## Stop Conditions

Stop this design family before any reducing runtime if:

```text
score, endpoint, CIGAR, full row, or digest drift appears
the CPU verifier cannot prove the proposal without rerunning full CPU Align
the proposal requires final CPU output membership as a runtime proof
the proposal is only a rename of a stopped descriptor/certificate family
the design has no plausible scoreInfo/preAlign replacement path for broad gate
```

## Required Next Gate

```text
phase7_full_align_verifier_design_spec_status = spec_defined
path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_execution_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Forbidden

```text
no real opt-in
no default behavior change
no runtime reduction in this design/spec checkpoint
no runtime work drop in this design/spec checkpoint
no first64 before first1 fail-closed shadow passes
no first64 before first1 reducing runtime passes
no broad_replacement matrix promotion
no promotion of the stopped GPU-owned scoreInfo consumer family
no promotion of the stopped scoreInfo certificate-engine family
no promotion of the stopped post-v5.3 descriptor-stream family
no GASAL2 endpoint authority
no GASAL2 CIGAR authority
no GASAL2 traceback authority
no GASAL2 output authority
no GASAL2 digest authority
no completion claim from this checkpoint
```

Global authority invariants remain:

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```
