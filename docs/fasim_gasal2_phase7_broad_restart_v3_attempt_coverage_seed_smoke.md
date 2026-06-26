# Fasim GASAL2 Phase 7 v3 Attempt-Coverage Seed Smoke

This is a Phase 7 v3 descriptor-source checkpoint for the original broad
GASAL2/Fasim objective. It does not add a real runtime path and does not
change Fasim output.

## Scope

```text
phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight
phase7_broad_restart_v3_attempt_coverage_seed_status = gate_v3_1_pass_candidate_attempts_high
required_runtime_env = FASIM_GASAL2_PHASE7_V3_ATTEMPT_COVERAGE_SEED_CERTIFICATE
runtime_default = off
runtime_authority = CPU aligner.Align()
```

This source is a bounded seed/index certificate. It is checked against the
legacy CPU scoreInfo/attempt oracle for the smoke, but the candidate path is
recorded as a pre-scoreInfo source:

```text
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_after_cpu_scoreinfo_source = 0
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
```

No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.
Do not add a broad_replacement workload-matrix row from this runtime smoke.

## Runtime Result

Command:

```bash
make check-fasim-gasal2-phase7-v3-attempt-coverage-seed-runtime-smoke
```

NEAT1 first1 telemetry:

```text
phase7_v3_attempt_coverage_seed_runtime_smoke = attempt_coverage_clean

tasks = 48
reference_scoreinfos = 718
reference_attempts = 2,872
candidate_scoreinfos = 718
raw_seed_hits = 1,051,822
candidate_attempts = 108,694
candidate_min_cover_positions = 463
candidate_attempts_lt_all_column = 1
candidate_attempts_lt_raw_seed_hits = 1
candidate_min_cover_positions_lt_reference_attempts = 1
candidate_certificate_checked = 1
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls = 0
baseline_cpu_scoreinfo_calls = 718
cpu_scoreinfo_reduced = 1
```

The candidate attempt count is far below the stopped all-column replay scale:

```text
all_column_replay_attempts = 168,730,848
candidate_attempts = 108,694
```

It is still much larger than the legacy reference attempt count:

```text
reference_attempts = 2,872
candidate_attempts = 108,694
candidate_attempts_below_reference = 0
```

The oracle lower-bound reducer is promising but not a real path:

```text
candidate_min_cover_positions = 463
candidate_min_cover_positions_below_reference = 1
oracle_min_cover_uses_legacy_attempt_windows = 1
real_pre_scoreinfo_reducer_proven = 0
```

## Decision

```text
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This is a real improvement over the previous strong-seed checkpoint:

```text
previous strong seed:
  candidate_certificate_false_negatives = 0
  missing_required_attempts > 0

attempt-coverage seed:
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
```

It still cannot close the broad objective because the next phase requires a
CPU-authority replay or a replay preflight that does not explode Align-side
work.

## Next Gate

```text
phase7_broad_restart_v3_next_gate =
  oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer
```

Before first64 or any broad_replacement matrix promotion, the next PR must
show one of these:

```text
Option 1:
  first1 oracle min-cover replay shape probe is clean
  full_rows_equal = true
  digest_match = true
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  candidate_align_attempts < reference_align_attempts
  still marked oracle-only unless the reducer no longer depends on legacy
    attempt windows

Option 2:
  non-oracle candidate attempt count is reduced before replay
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
  candidate_attempts < reference_attempts
```

Do not continue to first64 until first1 replay or replay preflight proves both
correctness and Align-side work reduction.
