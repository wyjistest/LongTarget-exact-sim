# Fasim GASAL2 Phase 7 v3 Descriptor-Source Smoke

This is the first runtime smoke for the Phase 7 v3 candidate-certificate
architecture.

It is not a broad gate pass, not a descriptor-source success, and not a
completion claim.

```text
phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source
phase7_broad_restart_v3_current_status = scaffold_no_go
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Command

```bash
make check-fasim-gasal2-phase7-v3-descriptor-source-env
make check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke
```

The runtime smoke uses a tiny synthetic FASTA pair. It verifies telemetry and
default-off behavior only.

## Observed Smoke Result

```text
phase7_v3_descriptor_source_runtime_smoke = current_no_pre_scoreinfo_source
phase7_v3_descriptor_source_requested = 1
phase7_v3_descriptor_source_active = 0
phase7_v3_descriptor_source_candidate_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
```

Interpretation:

```text
The v3 telemetry path is wired and default-off.
When requested, current code can observe CPU-authority scoreInfo/attempt
counts after CPU scoreInfo has already run.

The current code does not yet have a pre-scoreInfo GPU/native descriptor
source.
The current code does not produce candidate descriptors.
The current code does not reduce CPU scoreInfo/preAlign calls.
```

## Gate v3.1 Status

Gate v3.1 requires:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
full_output_authority = CPU aligner.Align()
```

Current status:

```text
gpu_candidate_scoreinfos = 0
gpu_candidate_attempts = 0
cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
pre_scoreinfo_source = 0
after_cpu_scoreinfo_source = 1
```

Decision:

```text
phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source
```

## Allowed Continuation

The next implementation may continue only by adding a real descriptor source
before CPU scoreInfo/preAlign has already done the broad work:

```text
GPU/native descriptor source
candidate descriptors > 0
candidate scoreInfo groups > 0
CPU scoreInfo calls lower than baseline
zero false-negative certificate against CPU authority
CPU aligner.Align() remains output authority
```

Do not continue by:

```text
deriving descriptors only from completed CPU frontier logs
reusing current Gate C oracle metrics as candidate descriptors
claiming all-attempt early-stop as v3
claiming broad_replacement from this smoke
using GASAL2 endpoint/CIGAR/traceback/output as authority
```
