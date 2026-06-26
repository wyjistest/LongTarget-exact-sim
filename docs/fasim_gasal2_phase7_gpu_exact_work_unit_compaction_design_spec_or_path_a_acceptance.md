# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction Design Spec Or Path A Acceptance

This checkpoint defines the next Path B design after the GPU upper-bound reject
certificate family stopped. It is docs-only. It does not add runtime behavior,
does not authorize work drop, and does not complete the active broad goal.

## Scope

```text
phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md
previous_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_gpu_exact_work_unit_compaction_spec_defined = 1
design_family = gpu_exact_work_unit_compaction_replay
not_gpu_upper_bound_reject_certificate_continuation = 1
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

The stopped Path B families tried to create row-accepting proof, scoreInfo
proof, full-align proposal proof, native-DP proof, or negative reject proof.
This design changes the proof shape. The GPU may only help form exact
equivalence classes of legacy work units. CPU authority still computes the
semantic result for each unique work unit, and ordered CPU replay expands that
result to duplicate members.

```text
proof_shape = exact_input_equivalence_compaction
gpu_accepts_rows = 0
gpu_rejects_rows = 0
gpu_emits_final_rows = 0
gpu_endpoint_cigar_traceback_required = 0
cpu_authority_replay_required = 1
fallback_to_full_cpu_replay_on_uncertainty = 1
```

This is useful only if a later gate proves that many legacy work units have
identical translated inputs and identical scoring/output context before CPU
scoreInfo/preAlign or CPU Align work is performed. If no meaningful duplicate
work exists, this design family must stop.

## Exact-Key Contract

The GPU-side key builder may group work only by exact input identity. It is not
a score, endpoint, CIGAR, traceback, output, digest, accept, or reject
decision.

```text
ExactWorkUnitKey:
  work_kind
  legacy_request_order
  translated_query_digest
  translated_target_window_digest
  target_window_offset
  target_window_length
  strand
  scoring_config_key
  gap_config_key
  threshold_config_key
  translation_config_key
  output_context_key
```

Two work units may share CPU semantic results only when every key component is
identical and CPU validation recomputes the same key:

```text
exact_key_match_required = 1
cpu_key_validation_required = 1
cpu_key_validation_uses_translated_inputs = 1
cpu_key_validation_uses_scoring_config = 1
cpu_key_validation_uses_threshold_config = 1
cpu_key_validation_uses_output_context = 1
key_collision_fallback_to_full_cpu_replay = 1
unsupported_key_fallback_to_full_cpu_replay = 1
```

Hash equality is insufficient by itself:

```text
hash_match_only_is_not_proof = 1
digest_collision_fallback_to_full_cpu_replay = 1
canonical_key_bytes_must_match = 1
```

## Reduction Shape

This design can only reduce work through CPU-authority memoization over exact
equivalence classes:

```text
scoreinfo_prealign_compaction:
  run CPU scoreInfo/preAlign once per unique scoreInfo key
  replay the CPU result to duplicate scoreInfo members in legacy order

align_candidate_compaction:
  run CPU aligner.Align() once per unique Align key
  replay the CPU Align result to duplicate Align members in legacy order
```

The broad objective requires both reduction paths to be proven before any broad
replacement claim:

```text
requires_scoreinfo_prealign_reduction_plan = 1
requires_align_side_reduction_plan = 1
requires_ordered_replay_plan = 1
requires_cpu_authority_result_cache = 1
```

No broad replacement claim is allowed from key collection alone:

```text
key_collection_only_is_shadow = 1
duplicate_count_only_is_not_runtime_reduction = 1
```

## First1 Shadow Contract

The next runtime checkpoint is first1-only and fail-closed. It may produce and
log exact-key compaction telemetry, but it must not skip CPU work.

```text
required_env = FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

Expected first1 telemetry:

```text
requested = 1
active = 1
scoreinfo_key_descriptors
scoreinfo_unique_keys
scoreinfo_duplicate_units
align_key_descriptors
align_unique_keys
align_duplicate_attempts
key_collisions
cpu_key_validation_mismatches
unsupported_key_descriptors
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
```

The first1 shadow is acceptable only if exact-key telemetry is observable and
the CPU authority path remains unchanged:

```text
requested = 1
active = 1
scoreinfo_key_descriptors > 0
align_key_descriptors > 0
key_collisions = 0
cpu_key_validation_mismatches = 0
full_rows_equal = 1
digest_match = 1
gate_first1_shadow_pass = 1
```

Even a clean first1 shadow still does not prove runtime reduction:

```text
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
```

A later runtime-reduction gate must additionally prove:

```text
scoreinfo_duplicate_units > 0
align_duplicate_attempts > 0
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
candidate_wall_seconds < baseline_wall_seconds
fallback_accounting_clean = 1
```

## Decision

```text
phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined
path_b_gpu_exact_work_unit_compaction_spec_defined = 1
path_b_gpu_exact_work_unit_compaction_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Forbidden

```text
no real opt-in
no runtime reduction in this design/spec checkpoint
no runtime work drop in this design/spec checkpoint
no first64 before first1 fail-closed shadow passes
no GPU accept decision
no GPU reject decision
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no final CPU output membership proof
no top5-only contract
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
