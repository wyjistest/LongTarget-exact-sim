# Fasim GASAL2 Phase 7 v5 True Pre-ScoreInfo Descriptor Source Runtime Smoke

This checkpoint records the strict first1 Gate v5.1 runtime result for the
true pre-scoreInfo descriptor-source path.

It is a runtime pass checkpoint, not a completion claim.

## Result

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
  gate_v5_1_pass_first1

strict_gate_target =
  check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
```

Observed telemetry from the passing first1 runtime smoke:

```text
phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_tasks > 0
phase7_v5_true_pre_scoreinfo_descriptor_source_reference_scoreinfos > 0
phase7_v5_true_pre_scoreinfo_descriptor_source_reference_attempts > 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos > 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts > 0
phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1
```

The strict Gate v5.1 checker now passes:

```bash
make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
```

## What This Proves

```text
default-off v5 descriptor-source runtime is observable
CUDA emits compact candidate attempt descriptors
descriptor emission happens before CPU scoreInfo/preAlign validation
CPU preAlign is used only after emission as validation authority
descriptor_false_negatives = 0 for first1
missing_required_attempts = 0 for first1
candidate attempts stay below all-column replay scale
CPU aligner.Align() remains authority
GPU endpoint/CIGAR/traceback/output authority remains forbidden
```

## What This Does Not Prove

```text
not broad completion
not first64 performance
not full-output replacement
not Align-side reduction proof
not workload-matrix broad_replacement promotion
not GPU endpoint/CIGAR/traceback/output authority
```

## Boundary

Do not continue with:

```text
v4 host-visible source replay as v5
post-scoreInfo descriptor scaffolds as broad evidence
CPU aligner.preAlign() as descriptor source
CPU legacy scoreInfo rows as descriptor source
GPU endpoint/CIGAR/traceback/output authority
```

CPU `aligner.Align()` remains the endpoint, CIGAR, traceback, output, and
digest authority.

## Next Required Gate

```text
next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1
```

The next Path B artifact must use the v5.1 descriptors as candidate attempts
and prove CPU-authority replay equality:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced or replaced
CPU aligner.Align() authority replay = 1
GPU endpoint/CIGAR/traceback/output authority = 0
```

## Decision

```text
broad_objective_status = open
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_gate_v5_2_pass = 0
must_not_call_update_goal_complete = 1
```
