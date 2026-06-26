# Fasim GASAL2 Phase 7 Full-Align Verifier First1 Shadow Scaffold

This checkpoint implements the first1 fail-closed shadow scaffold for the
GASAL2 full-align verifier design. It is observable at runtime, but it does not
produce an accepted verifier result, drop work, or change output.

## Scope

```text
phase7_gasal2_full_align_verifier_first1_shadow_scaffold = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md
previous_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
required_runtime_env = FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_full_align_verifier_
path_b_full_align_verifier_first1_shadow_scaffold = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The scaffold reuses the current first1 descriptor source only to count the CPU
Align attempt descriptors that a future verifier would need to cover. It
intentionally emits zero GASAL2 full-align proposals and falls back to full CPU
replay.

## Runtime Gate

Default behavior remains unchanged when the env is unset:

```text
FASIM_GASAL2_PHASE7_FULL_ALIGN_VERIFIER_FIRST1_SHADOW=1
```

When enabled on the first1 smoke fixture, the candidate output bytes must remain
identical to the baseline.

## Expected First1 Telemetry

The candidate run must report:

```text
requested = 1
active = 1
descriptors > 0
proposals = 0
proposal_failures = descriptors
verifier_pass = 0
verifier_fail = 0
cpu_align_fallbacks = descriptors
score_mismatches = 0
endpoint_mismatches = 0
cigar_mismatches = 0
full_row_mismatches = 0
digest_mismatches = 0
full_rows_equal = 0
digest_match = 0
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
gate_first1_shadow_pass = 0
```

`full_rows_equal` and `digest_match` stay zero because this scaffold does not
claim a full external-output comparison. The runtime smoke separately verifies
that enabling the scaffold leaves emitted lite output unchanged.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

The GASAL2 full-align verifier path is diagnostic only at this checkpoint.
GASAL2 endpoint, CIGAR, traceback, output, and digest authority remain
forbidden.

## Decision

```text
phase7_full_align_verifier_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
next_valid_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
```

The next checkpoint must either implement a real first1 verifier consumer that
can prove output-inert work drop before any CPU Align work is skipped, or record
no-go for this full-align verifier design family.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This is progress toward the broad objective, but it does not prove runtime
reduction, broad workload speedup, or goal completion.
