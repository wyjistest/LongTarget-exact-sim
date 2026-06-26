# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Reducing Runtime No-Go

This checkpoint records the Phase 7.3 review after the new GPU engine
certificate producer first1 checkpoint. It is not a runtime implementation and
not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md
previous_gate = first1_reducing_runtime_with_certificate_or_no_go
runtime_reduction_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous checkpoint proved that the CUDA API can produce a conservative
synthetic certificate:

```text
certificate_producer_active = 1
certificate_valid_before_d2h = 1
certificate_producer_is_synthetic_api_gate = 1
```

That is not enough to reduce Fasim runtime work. Phase 7.3 requires a real
Fasim path that uses the certificate before dropping scoreInfo/preAlign or
Align-side work. That path is not present.

## Runtime Audit

The current runtime files expose telemetry and the CUDA API surface, but they
do not call the certificate API from a real Fasim work-dropping path:

```text
real_fasim_runtime_certificate_source = 0
real_fasim_runtime_work_drop_path = 0
prealign_cuda_emit_new_engine_skipped_work_certificates_runtime_call_count = 0
```

The available producer remains a synthetic API gate. It is useful for proving
the structure of:

```text
PreAlignCudaNewEngineScoreInfoTask
PreAlignCudaNewEngineCandidateGroup
PreAlignCudaNewEngineReplayAttempt
PreAlignCudaNewEngineSkippedWorkCertificate
```

It does not prove that skipped Fasim work is output-inert in the real scoreInfo
state machine, and it does not reduce CPU replay attempts.

## Phase 7.3 Gate Result

The first1 reducing runtime gate does not pass:

```text
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
candidate_wall_seconds_lt_baseline_wall_seconds = 0
full_rows_equal = unproven
digest_match = unproven
missing_rows = unproven
extra_rows = unproven
```

This is a no-go because a pass requires all of:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
```

## Stop Rules

```text
no_first64_from_failed_first1 = 1
do_not_relabel_synthetic_certificate_as_runtime_reduction = 1
do_not_use_final_cpu_output_membership_as_runtime_proof = 1
```

The current line must not run a first64 broad gate, because first1 has not
passed. It must also not call the producer checkpoint a runtime reduction. A
certificate emitted only by synthetic test data is not a proof that real Fasim
work can be skipped.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Decision

The current broad Path B implementation line has no safe runtime PR:

```text
path_b_current_implementation_available = 0
path_b_runtime_pr_allowed = 0
path_b_different_gpu_execution_design_required = 1
path_a_user_acceptance_required = 1
```

The next valid work is:

```text
next_valid_work = path_a_scoped_acceptance_or_new_engine_design_doc
current_execution_gate = path_a_scoped_acceptance_or_new_engine_design_doc
current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
```

If Path B continues, the next artifact must be docs/spec first and must define
a genuinely different GPU execution design with a real Fasim runtime
certificate source. If Path A is chosen, the next artifact must record explicit
scoped acceptance and keep the original broad objective out of the completion
claim.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint closes only the current Phase 7.3 attempt. It does not close
Path A or Path B.
