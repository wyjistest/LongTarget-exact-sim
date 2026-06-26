# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Pre-Drop Work-Drop Proof Design

This checkpoint defines the next Path B gate after the real-source certificate
source first1 checkpoint. It is a design-only checkpoint, not a runtime
reduction PR, not a work-drop implementation, not a first1 pass, not a first64
authorization, and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined
design_only = 1
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
previous_gate = design_pre_drop_output_inert_work_drop_proof
real_source_certificate_source_gate_pass = 1
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
source_is_pre_drop = 1
gate_first1_source_pass = 1
gate_first1_pass = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

The real-source checkpoint proved that the runtime can observe non-synthetic
certificate candidate inputs before dropping work. It did not prove that any
candidate is safe to skip. This document defines the missing proof gate.

## Required Proof Shape

```text
proof_must_be_pre_drop = 1
proof_must_be_output_inert = 1
proof_must_not_use_final_cpu_output_membership = 1
proof_must_not_use_top5_only_contract = 1
proof_must_cover_complete_row_set = 1
certificate_production_separate_from_consumption = 1
consumer_must_fail_closed = 1
fallback_to_full_cpu_replay = 1
```

The proof must be available before the consumer skips any scoreInfo or
align-attempt work. The proof may compare against CPU authority in shadow
telemetry, but it must not use final CPU output membership as the runtime reason
for a skip.

## First1 Proof Shadow Contract

The next implementation checkpoint must be first1-only and shadow-first. It may
compute proof telemetry and make a hypothetical drop decision, but the actual
runtime must still fall back to full CPU replay until this gate passes.

required_future_telemetry:

```text
uses_pre_drop_output_inert_proof
candidate_proof_false_negatives
candidate_proof_missing_required_attempts
candidate_uses_final_cpu_output_as_runtime_proof
gate_first1_proof_pass
scoreInfo_prealign_reduced
align_side_reduced
full_rows_equal
digest_match
```

Pass conditions for the future first1 proof shadow:

```text
uses_pre_drop_output_inert_proof = 1
candidate_proof_false_negatives = 0
candidate_proof_missing_required_attempts = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
gate_first1_proof_pass = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

Only a later reducing-runtime checkpoint may enable a real work drop, and only
after the proof shadow gate passes.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Stop Conditions

Stop Path B for this design family if any of these are true:

```text
the proof needs final CPU output membership
the proof is only top5-safe
the proof changes the complete row set
the proof cannot reduce both scoreInfo/preAlign and Align-side work
the proof requires GPU endpoint/CIGAR/traceback/output/digest authority
```

## Decision

```text
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_gate = defined
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the active goal by defining the missing proof gate. It
does not prove work-drop safety and does not close the active goal.
