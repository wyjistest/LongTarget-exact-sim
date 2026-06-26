# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source Certificate Source First1

This checkpoint implements the Phase 7.2 source-only gate from
`docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md`. It proves that
the new GPU-engine line can observe a non-synthetic certificate candidate source
from the real Fasim runtime path before any work is dropped.

It is not a runtime-reduction PR, not a first1 reducing-runtime pass, not a
first64 authorization, and not a completion claim.

## Scope

```text
phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1 =
  source_only_pre_drop_runtime_hook
previous_checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md
required_runtime_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE
telemetry_prefix =
  benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The source is the real Fasim streaming scoreInfo descriptor producer:

```text
source_location =
  after real runtime task construction and before any descriptor consumer/drop
source_is_pre_drop = 1
source_is_legacy_byte_cuda = 1
runtime_certificate_is_synthetic = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
```

This checkpoint may use CPU authority only to compare the source descriptor set
against the legacy required-attempt descriptor set. It must not use final CPU
output membership as the source or as a runtime proof.

## Required Telemetry

For the first1 runtime smoke, the env-on row must report:

```text
requested = 1
active = 1
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
source_is_pre_drop = 1
source_is_legacy_byte_cuda = 1
candidate_uses_final_cpu_output_as_runtime_proof = 0
source_task_count > 0
source_scoreinfo_count > 0
source_attempt_count > 0
reference_scoreinfo_count > 0
reference_attempt_count > 0
missing_certificate = 0
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 1
certificate_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
full_rows_equal = 0
digest_match = 0
gate_first1_source_pass = 1
gate_first1_pass = 0
```

The zero equality fields mean no candidate reducing runtime was run. Output
bytes must still match the CPU baseline because this source-only hook falls back
to the normal CPU replay path.

## Decision

```text
real_source_certificate_source_gate_pass = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = design_pre_drop_output_inert_work_drop_proof
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_design
```

Phase 7.3 must define an output-inert work-drop proof before any runtime work
is skipped. Do not run first64 from this checkpoint.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the active goal by proving the Phase 7.2 source exists.
It does not prove work-drop safety and does not close the active goal.
