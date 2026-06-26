# Fasim GASAL2 Phase 7 v3 Narrow Certificate Smoke

This checkpoint wires the default-off narrow-certificate runtime path after the
all-column replay stop. It is intentionally fail-closed: the runtime source is
bounded and scoreInfo-reducing, but it does not prove certificate coverage.

It is not a broad replacement, not a performance claim, and not permission to
use GASAL2 endpoint, CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_narrow_certificate_smoke = bounded_probe_no_go_missing_certificate
phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Runtime Env

```text
required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
```

The env is default-off and diagnostic only. It does not change the output
authority path.

## Validation Commands

```bash
make check-fasim-gasal2-phase7-v3-narrow-certificate-env
make check-fasim-gasal2-phase7-v3-narrow-certificate-runtime-smoke
make check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-smoke
```

## Runtime Smoke

The smoke runs NEAT1 first1 baseline and candidate cases. The candidate enables
only:

```text
FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE=1
```

Observed result:

```text
phase7_v3_narrow_certificate_runtime_smoke = bounded_probe_no_go_missing_certificate
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
```

## Interpretation

The bounded probe proves only the runtime plumbing:

```text
pre-scoreInfo descriptor source exists
candidate descriptors are non-empty
candidate attempts are below the all-column replay count
candidate CPU scoreInfo calls are zero
```

It does not prove the certificate contract:

```text
candidate_certificate_false_negatives > 0
missing_required_attempts > 0
```

Therefore Gate v3.1 must remain failed:

```text
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
```

CPU aligner.Align() output authority remains required:

```text
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

## Decision

```text
phase7_broad_restart_v3_narrow_certificate_smoke = bounded_probe_no_go_missing_certificate
phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Do not add a broad_replacement workload-matrix row from this runtime smoke.

The next valid v3 step must replace the bounded placeholder with a real narrow
certificate that proves:

```text
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_attempts < reference_align_attempts before v3.2 can pass
CPU aligner.Align() output authority
```
