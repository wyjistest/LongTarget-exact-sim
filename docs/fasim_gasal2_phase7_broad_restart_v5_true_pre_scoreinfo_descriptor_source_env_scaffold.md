# Fasim GASAL2 Phase 7 v5 True Pre-ScoreInfo Descriptor Source Env Scaffold

This checkpoint adds a separate default-off env and telemetry surface for the
next true pre-scoreInfo descriptor source. It is a fail-closed scaffold, not a
runtime source and not a Gate v5.1 pass.

## Scope

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold = fail_closed_no_source
required_runtime_env = FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The env is intentionally separate from:

```text
FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER
```

That older env records the post-scoreInfo descriptor mirror and remains a
no-go scaffold because CPU scoreInfo/preAlign work has already happened.

## Runtime Evidence

Command:

```bash
make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env-runtime-smoke
```

Observed result:

```text
phase7_v5_true_pre_scoreinfo_descriptor_source_env_runtime_smoke = fail_closed_no_source
phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0
```

## Interpretation

The scaffold proves only that the next env is observable and fail-closed:

```text
requested = 1
active = 0
source_is_pre_scoreinfo = 0
scoreinfo_prealign_reduced = 0
gpu_descriptor_attempts = 0
gate_v5_1_pass = 0
```

This avoids reusing the post-scoreInfo mirror as the true source. A future
runtime may pass only after it actually emits compact descriptors before CPU
scoreInfo/preAlign work and keeps CPU `aligner.Align()` as authority.

## Next Gate

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
```

The next implementation must change these runtime facts:

```text
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
candidate_attempts_below_all_column_replay_scale = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

Until then, the broad objective remains open.
