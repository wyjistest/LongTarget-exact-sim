# Fasim GASAL2 Phase 7 v3 Pre-ScoreInfo Descriptor-Source Smoke

This is the second runtime smoke for the Phase 7 v3 candidate-certificate
architecture.

It proves that a descriptor-source hook can run before CPU scoreInfo/preAlign
has already produced legacy scoreInfo groups. It does not pass Gate v3.1,
because it does not yet reduce CPU scoreInfo calls and does not check a
candidate certificate.

```text
phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Command

```bash
make check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env
make check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke
```

The runtime smoke uses a tiny synthetic FASTA pair. It verifies telemetry,
default-off behavior, and pre-scoreInfo descriptor-source placement only.

## Observed Smoke Result

```text
phase7_v3_pre_scoreinfo_descriptor_source_runtime_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_v3_descriptor_source_requested = 1
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
phase7_v3_descriptor_source_candidate_certificate_checked = 0
```

Interpretation:

```text
The v3 source is now positioned before CPU scoreInfo/preAlign.
The source can produce diagnostic candidate descriptors.
The source does not change output.
The source does not reduce CPU scoreInfo/preAlign work.
The source does not prove candidate-certificate coverage.
```

## Gate v3.1 Status

Gate v3.1 requires:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_certificate_checked = 1
full_output_authority = CPU aligner.Align()
```

Current status:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
pre_scoreinfo_source = 1
after_cpu_scoreinfo_source = 0
cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
cpu_scoreinfo_reduced = 0
candidate_certificate_checked = 0
```

Decision:

```text
phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  certificate_checked_scoreinfo_reducing_descriptor_source
```

## Allowed Continuation

The next implementation may continue only if it turns this pre-scoreInfo
source into a certified reducer:

```text
candidate_certificate_checked = 1
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
CPU aligner.Align() remains output authority
```

Do not continue by:

```text
claiming broad_replacement from descriptor counts only
continuing to first64 while cpu_scoreinfo_reduced = 0
using unchecked descriptor coverage
using GASAL2 endpoint/CIGAR/traceback/output as authority
```
