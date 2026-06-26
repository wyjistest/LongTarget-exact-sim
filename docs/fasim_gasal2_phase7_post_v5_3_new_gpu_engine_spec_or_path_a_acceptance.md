# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Spec Or Path A Acceptance

This checkpoint turns the previous new-engine design into the next gate. It is
docs/spec only. It does not add runtime behavior, does not authorize a runtime
PR, and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md
previous_gate = phase7_new_gpu_engine_spec_or_path_a_acceptance
runtime_reduction_enabled = 0
runtime_pr_allowed = 0
first1_runtime_allowed = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Path A and Path B stay separate:

```text
Path A is allowed only with explicit user scoped acceptance.
Path B is allowed only as an implementation-ready spec before runtime code.
```

Current acceptance state:

```text
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_spec_checkpoint_defined = 1
path_b_runtime_implementation_allowed = 0
```

## Implementation-Ready Spec Requirements

The next Path B artifact must be a first1 implementation spec for a new
Fasim-compatible GPU scoreInfo/attempt engine. It must define exact layouts and
proof fields before any runtime implementation is allowed.

Required inputs:

```text
encoded query layout
encoded target layout
scoring config key
scoreInfo-compatible scoring mode
candidate ordering rule
skipped scoreInfo upper bound
skipped attempt score upper bound
skipped attempt nt upper bound
skipped attempt identity upper bound
skipped attempt stability upper bound
task output capacity
scoreInfo-local break-state
```

Required outputs:

```text
selected replay attempts
skipped-work certificate
fail-closed fallback counters
proof telemetry
```

The spec must explain how each skipped scoreInfo group or skipped attempt is
proven output-inert before runtime reduction. A proof that depends on final CPU
output membership is not valid runtime proof.

## First1 Gate

The first runnable implementation after this spec may be first1 shadow only.
It must pass all of these gates before any first64 or larger run:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
certificate_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Any first1 mismatch stops Path B until the spec or implementation explains and
fixes the mismatch. A correctness-clean first1 that does not reduce both
scoreInfo/preAlign work and Align-side work remains a checkpoint, not a broad
completion path.

## First64 Broad Gate

```text
first64_may_run_only_after_first1_passes = 1
```

The first64 or larger broad gate must require:

```text
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
same equality/reduction/accounting gates as first1
```

Only after this gate passes may Phase 6 add a `broad_replacement` row to the
workload matrix.

## Runtime Authority

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

The GPU may propose selected replay attempts only through a conservative
certificate. CPU replay and existing Fasim output code remain the semantic
authority.

## Current Decision

This checkpoint does not approve runtime work yet:

```text
current_path = Path B
current_phase = Phase 7
next_valid_gate = phase7_new_gpu_engine_first1_spec_or_path_a_acceptance
current_next_pr = fasim_new_gpu_engine_first1_spec_or_path_a_acceptance
```

Path A remains available only if the user explicitly accepts the scoped product
as the goal. Without that acceptance, Path B must continue through the new GPU
engine first1 spec gate before code.

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint makes the next required artifact concrete. It does not close
Path A or Path B.
