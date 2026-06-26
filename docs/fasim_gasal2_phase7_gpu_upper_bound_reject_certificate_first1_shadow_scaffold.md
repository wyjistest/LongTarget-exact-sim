# Fasim GASAL2 Phase 7 GPU Upper-Bound Reject Certificate First1 Shadow Scaffold

This checkpoint implements the first fail-closed runtime scaffold for the
GPU upper-bound reject certificate design. It does not enable runtime
reduction, does not drop work, and does not complete the active broad goal.

## Scope

```text
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md
previous_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
required_runtime_env = FASIM_GASAL2_PHASE7_GPU_UPPER_BOUND_REJECT_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_upper_bound_reject_
path_b_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold observes the legacy first1 descriptor stream and records
conservative upper-bound certificate counts. The current scaffold does not use
certificates to skip scoreInfo/preAlign work or Align-side work.

## Runtime Contract

The first1 runtime smoke requires:

```text
requested = 1
active = 1
upper_bound_descriptors > 0
upper_bound_certificates > 0
reject_candidates_shadow
would_reject_scoreinfo_groups
would_reject_align_attempts
certificate_false_negatives = 0
baseline_rows_in_rejected_groups = 0
baseline_rows_in_rejected_attempts = 0
unsupported_descriptors = 0
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gate_first1_shadow_pass = 1
gate_first1_pass = 0
```

The current scaffold records non-reducing shadow certificates. It intentionally
keeps reject counts at zero until a consumer can prove that rejected work is
available before CPU work is performed and contains no baseline output rows.

```text
reject_candidates_shadow = 0
would_reject_scoreinfo_groups = 0
would_reject_align_attempts = 0
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
gpu_score_authority = 0
gpu_endpoint_authority = 0
gpu_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
```

Because the scaffold is fail-closed, CPU replay remains the only semantic path:

```text
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
```

## Decision

The scaffold is a valid Phase 7 first1 shadow checkpoint, but it is not a
reducing runtime. The next step must decide whether a safe pre-drop consumer
can exist or whether this design family is no-go.

```text
next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Forbidden

```text
no real opt-in
no runtime reduction
no runtime work drop
no scoreInfo/preAlign reduction claim
no Align-side reduction claim
no first64
no GPU score authority
no GPU endpoint authority
no GPU CIGAR authority
no GPU traceback authority
no GPU output authority
no GPU digest authority
no broad_replacement workload-matrix promotion
```
