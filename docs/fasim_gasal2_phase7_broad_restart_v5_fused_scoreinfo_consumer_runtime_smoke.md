# Fasim GASAL2 Phase 7 v5 Fused ScoreInfo Consumer Runtime Smoke

This checkpoint records the first runtime wiring for the Phase 7 v5 fused
scoreInfo consumer path.

It is a no-go scaffold checkpoint, not a broad completion checkpoint.

```text
phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke = post_scoreinfo_descriptor_scaffold_no_go
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_may_claim_completion = 0
phase7_broad_restart_v5_next_gate = true_pre_scoreinfo_fused_descriptor_source
phase7_broad_restart_v5_runtime_scaffold_next_gate = true_pre_scoreinfo_fused_descriptor_source
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Scope

The implemented runtime path is default-off:

```bash
FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER=1
```

This first scaffold records descriptor telemetry at the existing
post-scoreInfo attempt boundary:

```text
CPU preAlign has already produced scoreInfo rows.
The scaffold mirrors those rows into candidate attempt descriptors.
CPU aligner.Align() remains the only semantic authority.
GPU endpoint/CIGAR/traceback/output/digest authority remains forbidden.
```

This means the scaffold can prove descriptor accounting, but it cannot pass
Gate v5.1 because it does not reduce or replace scoreInfo/preAlign work.

## Evidence

Workload:

```text
NEAT1 first1
```

Command:

```bash
bash scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh
```

Observed result:

```text
v5 must reduce or replace scoreInfo/preAlign work
```

Telemetry:

```text
baseline:
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active = 0

candidate:
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested = 1
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active = 1
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_tasks = 48
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos = 718
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_attempts = 2872
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos = 718
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts = 2872
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_missing_required_attempts = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_cpu_align_authority = 1
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority = 0
  benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass = 0
```

## Decision

The runtime scaffold is wired correctly enough to show descriptor counts:

```text
requested = 1
active = 1
gpu_descriptor_attempts = 2872
descriptor_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

It is not a valid broad Path B source:

```text
scoreinfo_prealign_reduced = 0
gate_v5_1_pass = 0
```

This confirms the current scaffold is only a post-scoreInfo descriptor mirror.
It does not satisfy the v5 design requirement:

```text
GPU legacy byte scoreInfo computation
  -> GPU consumer state machine
  -> compact candidate attempt descriptors
  -> CPU aligner.Align() authority replay
```

## Next Gate

The next broad attempt must produce descriptors before CPU scoreInfo/preAlign
work:

```text
phase7_broad_restart_v5_next_gate = true_pre_scoreinfo_fused_descriptor_source
phase7_broad_restart_v5_runtime_scaffold_next_gate = true_pre_scoreinfo_fused_descriptor_source
```

A future gate may pass only if:

```text
gpu_descriptor_attempts > 0
scoreinfo_prealign_reduced = 1
descriptor_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

Until then, the broad objective remains open.
