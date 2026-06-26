# Fasim GASAL2 Phase 7 GPU-Owned ScoreInfo Consumer First1 Shadow Scaffold

This checkpoint implements the first1 fail-closed shadow scaffold for the
GPU-owned scoreInfo consumer design. It is not a reducing runtime and does not
complete the active goal.

## Scope

```text
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md
previous_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
path_b_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold makes the GPU-owned scoreInfo consumer family observable on a
first1 fixture. It intentionally fails closed to full CPU replay.

## Runtime Gate

```text
required_runtime_env = FASIM_GASAL2_PHASE7_GPU_OWNED_SCOREINFO_CONSUMER_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_
```

Default behavior remains unchanged when the env is unset.

## Expected First1 Telemetry

The candidate run must report:

```text
requested = 1
active = 1
gpu_owned_scoreinfo_consumer_requested = 1
gpu_owned_scoreinfo_consumer_active = 1
gpu_owned_scoreinfo_states > 0
gpu_owned_attempt_frontier_attempts > 0
gpu_owned_replay_frontier_attempts > 0
gpu_owned_skipped_scoreinfo_groups = 0
gpu_owned_skipped_attempts = 0
cpu_replay_attempts > 0
baseline_cpu_attempts > 0
cpu_replay_attempts = baseline_cpu_attempts
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
certificate_produced_before_work_drop = 0
certificate_consumed_before_cpu_replay_selection = 0
certificate_false_negatives = 0
missing_required_attempts = 0
fallback_to_full_cpu_replay = 1
fallback_accounting_clean = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 0
digest_match = 0
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

`full_rows_equal` and `digest_match` stay zero because this scaffold does not
claim an external-output comparison. The runtime smoke separately verifies
that enabling this shadow path does not change the emitted lite output bytes.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

The GPU-owned shadow data is diagnostic only. It is not used for endpoint,
CIGAR, traceback, candidate state, final output, digest, or accept/reject
authority.

## Decision

```text
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

The next PR must either prove a valid pre-drop consumer for this GPU-owned
frontier or record no-go for this design family. It must not run first64 or
enable work drop until first1 reduction passes.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint is useful progress toward the broad objective, but it does not
prove runtime reduction, broad workload speedup, or goal completion.
