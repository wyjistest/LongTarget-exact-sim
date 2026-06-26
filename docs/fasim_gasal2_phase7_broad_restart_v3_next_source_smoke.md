# Fasim GASAL2 Phase 7 v3 Next Source Smoke

This checkpoint runs the first allowed next-source runtime smoke after the
existing exact-column GPU scoreInfo source was ruled out.

The source tested here is a minimal seed/index certificate source:

```text
required_runtime_env = FASIM_GASAL2_PHASE7_V3_SEED_CERTIFICATE_SOURCE
```

It is default-off, diagnostic-only, and does not use GASAL2/GPU endpoint,
CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_next_source_smoke = seed_certificate_fail_closed
phase7_broad_restart_v3_next_source_status = runtime_smoke_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Runtime Shape

The smoke runs on NEAT1 first1. It builds seed descriptors before CPU scoreInfo
work and records them through the existing Phase 7 v3 descriptor telemetry.

The seed source is intentionally not used for output:

```text
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

## Result

Validation command:

```bash
make check-fasim-gasal2-phase7-v3-next-source-runtime-smoke
```

Observed result:

```text
phase7_v3_next_source_runtime_smoke = seed_certificate_fail_closed
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
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_broad_gate_pass = 0
```

Interpretation:

```text
seed descriptor source:
  active
  pre-scoreInfo
  narrower than all-column replay
  CPU scoreInfo calls bypassed in the candidate source

certificate:
  checked
  false negatives remain
  missing required attempts remain
  fail-closed
```

## Decision

This is useful plumbing and a real seed/index-source smoke, but it is not a
valid v3.1 certificate because false negatives and missing required attempts
are non-zero.

Do not continue this source to first1 CPU-authority replay or first64 broad
gate in its current form.

```text
Do not add a broad_replacement workload-matrix row from this runtime smoke.
phase7_broad_restart_v3_next_gate = stronger_seed_certificate_or_different_exact_scoreinfo_source
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next Path B attempt must either strengthen this seed/index certificate so
that:

```text
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
```

or return to a different exact scoreInfo-compatible GPU execution source.
