# Fasim GASAL2 Phase 7 v3 Strong Seed Smoke

This checkpoint strengthens the previous seed/index descriptor source. It is
still default-off and diagnostic-only.

```text
required_runtime_env = FASIM_GASAL2_PHASE7_V3_STRONG_SEED_CERTIFICATE_SOURCE
```

CPU `aligner.Align()` remains the output authority:

```text
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

## Result

Validation command:

```bash
make check-fasim-gasal2-phase7-v3-strong-seed-runtime-smoke
```

Observed result:

```text
phase7_broad_restart_v3_strong_seed_smoke = task_coverage_clean_attempt_coverage_missing
phase7_broad_restart_v3_strong_seed_status = runtime_smoke_no_go_attempt_coverage
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_scoreinfos_ge_baseline = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Interpretation

This is progress over the previous seed smoke:

```text
previous seed smoke:
  candidate_certificate_false_negatives_gt_zero = 1
  missing_required_attempts_gt_zero = 1

strong seed smoke:
  candidate_certificate_false_negatives = 0
  missing_required_attempts_gt_zero = 1
```

So the stronger seed source covers every baseline scoreInfo task on NEAT1
first1, but it still does not prove that every required align attempt is
covered.

## Decision

This checkpoint does not pass Gate v3.1 because attempt coverage remains
missing. It must not continue to first1 CPU-authority replay or first64 broad
gate yet.

```text
Do not add a broad_replacement workload-matrix row from this runtime smoke.
phase7_broad_restart_v3_next_gate = attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next Path B attempt must either:

```text
prove missing_required_attempts = 0 for the seed/index source
or
return to a different exact scoreInfo-compatible execution source
```
