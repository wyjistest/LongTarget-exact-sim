# Fasim GASAL2 Phase 7 v3 Seed Path Stop

This checkpoint closes the current seed/index certificate path for broad
completion. It does not close the active goal. It prevents the roadmap from
continuing a path whose only low-attempt replay shape is oracle-only and
output-changing.

## Scope

```text
phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped
phase7_broad_restart_v3_seed_path_status =
  stopped_no_output_clean_non_oracle_reducer
runtime_authority = CPU aligner.Align()
runtime_default = off
```

No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.
Do not add a broad_replacement workload-matrix row from this stop checkpoint.

## Evidence Chain

The current seed/index path has useful coverage evidence:

```text
docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md
phase7_broad_restart_v3_attempt_coverage_seed_smoke =
  attempt_coverage_clean_needs_replay_preflight
phase7_broad_restart_v3_gate_v3_1_pass = 1
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls = 0
cpu_scoreinfo_reduced = 1
```

But the direct candidate set is still too large for Gate v3.2:

```text
reference_attempts = 2,872
raw_seed_hits = 1,051,822
candidate_attempts = 108,694
candidate_attempts_below_reference = 0
```

The oracle min-cover lower bound reduces Align attempts:

```text
docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md
phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go
reference_align_attempts = 2,872
candidate_min_cover_positions = 463
candidate_align_attempts = 463
candidate_align_attempts_lt_reference = 1
```

But that replay shape changes output:

```text
digest_match = 0
full_rows_equal = 0
missing_rows = 11
extra_rows = 9
phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0
```

It is also oracle-only:

```text
oracle_min_cover_uses_legacy_attempt_windows = 1
real_pre_scoreinfo_reducer_proven = 0
```

## Decision

```text
phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Do not continue the current seed/index path to first64. It has no current
non-oracle reducer that both preserves full output and reduces CPU-authority
Align attempts.

The next valid Phase 7 gate is:

```text
phase7_broad_restart_v3_next_gate =
  different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision
```

Any future Path B restart must be materially different and must prove all of
these on first1 before first64:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
real_pre_scoreinfo_reducer_proven = 1
fallback_accounting_clean = true
CPU aligner.Align() remains authority
GPU endpoint/CIGAR/traceback/output authority = false
```
