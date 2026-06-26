# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction First1 Shadow Scaffold

This checkpoint implements the first1 fail-closed shadow scaffold defined by
`docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md`.
It makes exact work-unit key telemetry observable. It does not reduce runtime
work, does not drop work, and does not complete the active broad goal.

## Scope

```text
phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
previous_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
previous_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
required_runtime_env = FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_
runtime_default = off
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Runtime Smoke Result

The targeted first1 smoke is:

```bash
make check-fasim-gasal2-phase7-gpu-exact-work-unit-compaction-first1-shadow-runtime-smoke
```

It compares baseline and candidate lite output bytes for NEAT1 first1 while
the candidate sets:

```text
FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW=1
```

Observed required telemetry:

```text
requested = 1
active = 1
scoreinfo_key_descriptors > 0
scoreinfo_unique_keys > 0
scoreinfo_duplicate_units = 0
align_key_descriptors > 0
align_unique_keys > 0
align_duplicate_attempts = 0
key_collisions = 0
cpu_key_validation_mismatches = 0
unsupported_key_descriptors = 0
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
cpu_align_authority = 1
gpu_score_authority = 0
gpu_endpoint_authority = 0
gpu_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
gate_first1_shadow_pass = 1
gate_first1_pass = 0
```

The current scaffold reports duplicate counts conservatively as zero. That is
intentional for this gate. The scaffold proves only that exact-key descriptors
are observable and fail-closed; it does not prove that a compaction consumer can
reduce CPU work.

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
fallback_to_full_cpu_replay = 1
```

## Decision

```text
path_b_gpu_exact_work_unit_compaction_first1_shadow_scaffold = 1
phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass = 1
phase7_gpu_exact_work_unit_compaction_gate_first1_pass = 0
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next gate must decide whether the observed exact-key descriptors contain
enough duplicate work, and whether key decisions are available early enough, to
justify a CPU-authority compaction consumer. If duplicate work is negligible,
or if keys cannot be consumed before duplicate CPU work is performed, this
family must record a no-go.

## Forbidden

```text
no real opt-in
no runtime reduction in this scaffold
no runtime work drop in this scaffold
no first64 before first1 reducing runtime passes
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
