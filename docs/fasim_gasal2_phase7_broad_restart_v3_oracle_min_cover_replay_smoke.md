# Fasim GASAL2 Phase 7 v3 Oracle Min-Cover Replay Smoke

This checkpoint tests the replay shape implied by the attempt-coverage seed
certificate. It is an oracle-only shape probe: the min-cover set depends on
legacy CPU attempt windows, so it is not a real pre-scoreInfo reducer.

## Scope

```text
phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go
phase7_broad_restart_v3_oracle_min_cover_replay_status = oracle_shape_probe_no_go
required_runtime_env = FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY
runtime_default = off
runtime_authority = CPU aligner.Align()
```

No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.
Do not add a broad_replacement workload-matrix row from this runtime smoke.

## Runtime Result

Command:

```bash
bash scripts/check_fasim_gasal2_phase7_v3_oracle_min_cover_replay_runtime_smoke.sh
```

NEAT1 first1 telemetry:

```text
reference_align_attempts = 2,872
candidate_min_cover_positions = 463
candidate_align_attempts = 463
skipped_attempts = 2,409
candidate_align_attempts_lt_reference = 1
digest_match = 0
full_rows_equal = 0
missing_rows = 11
extra_rows = 9
```

## Decision

```text
phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The oracle min-cover shape reduces CPU Align attempts, but it does not preserve
the full output contract. Covering every legacy attempt window with a seed
position is not equivalent to replaying the legacy attempt sequence.

## Next Gate

```text
phase7_broad_restart_v3_next_gate =
  non_oracle_candidate_reducer_or_stop_seed_path
```

Do not continue this oracle min-cover replay shape to first64. Future work must
either design a non-oracle reducer that preserves output rows and reduces
Align-side attempts, or stop the seed/index path for broad completion.
