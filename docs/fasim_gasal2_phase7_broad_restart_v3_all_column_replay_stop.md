# Fasim GASAL2 Phase 7 v3 All-Column Replay Stop

This checkpoint closes the all-column certificate branch before CPU-authority
replay. It is a useful Gate v3.1 proof, but it is not a viable Gate v3.2
candidate.

It is not a broad replacement, not a runtime recommendation, and not permission
to use GASAL2 endpoint, CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Source Checkpoint

The preceding smoke is recorded in:

```text
docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md
phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate
```

That smoke proves that a pre-scoreInfo descriptor source can reduce CPU
scoreInfo calls by emitting every target end column and every target window:

```text
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
```

## Replay Preflight

The same all-column certificate explodes CPU-authority replay attempts:

```text
candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
```

Gate v3.2 requires:

```text
candidate_align_attempts < reference_align_attempts cannot pass
```

Therefore all-column CPU replay should not be run:

```text
do_not_run_all_column_cpu_replay = 1
phase7_broad_restart_v3_may_continue_to_first64 = 0
```

Running the replay would spend CPU `aligner.Align()` work on roughly 168.7
million candidate windows for a first1 smoke whose CPU authority baseline has
only 2,872 Align attempts. That violates the v3.2 purpose before correctness or
wall time is measured.

## Decision

```text
phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Do not add a broad_replacement workload-matrix row from this stop checkpoint.

The next valid Phase 7 v3 gate is:

```text
phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate
```

That next certificate must be narrower than all columns/all windows while still
preserving:

```text
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_align_attempts < reference_align_attempts
CPU aligner.Align() output authority
```
