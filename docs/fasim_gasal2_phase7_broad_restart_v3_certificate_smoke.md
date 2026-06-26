# Fasim GASAL2 Phase 7 v3 Certificate Smoke

This is the third runtime smoke for the Phase 7 v3 candidate-certificate
restart. It is a certificate plumbing checkpoint only.

It does not pass Gate v3.1, does not reduce CPU scoreInfo/preAlign work, and
does not allow a broad-replacement workload claim.

```text
phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction
phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Validation Commands

```bash
make check-fasim-gasal2-phase7-v3-certificate-env
make check-fasim-gasal2-phase7-v3-certificate-runtime-smoke
make check-fasim-gasal2-roadmap-phase7-broad-restart-v3-certificate-smoke
```

## Runtime Smoke

The smoke enables:

```text
FASIM_GASAL2_PHASE7_V3_PRE_SCOREINFO_DESCRIPTOR_SOURCE=1
FASIM_GASAL2_PHASE7_V3_CERTIFICATE_CHECK=1
```

Observed result:

```text
phase7_v3_certificate_runtime_smoke = certificate_checked_no_scoreinfo_reduction
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
```

## Interpretation

This is a task-level scaffold certificate.

It proves only that the v3 pre-scoreInfo descriptor hook can be paired with an
explicit certificate-check telemetry path on a tiny fixture. It does not prove
full legacy scoreInfo/attempt coverage.

The certificate currently checks no real scoreInfo-local legacy candidate set.
It therefore cannot justify skipping CPU scoreInfo/preAlign. CPU
`aligner.Align()` remains the authority for score, endpoint, traceback, CIGAR,
output rows, and digest.

## Gate v3.1 Status

Gate v3.1 still fails:

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
candidate_certificate_checked = 1
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
cpu_scoreinfo_reduced = 0
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
```

It does not reduce CPU scoreInfo/preAlign work.
It does not pass Gate v3.1.

## Decision

```text
phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction
phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate = scoreinfo_reducing_candidate_certificate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Do not add a broad_replacement workload-matrix row from this smoke.

The next valid v3 step must make the certificate scoreInfo-reducing:

```text
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate descriptors generated before CPU scoreInfo/preAlign
CPU aligner.Align() remains output authority
```
