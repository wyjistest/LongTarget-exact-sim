# Fasim GASAL2 Phase 7 v3 All-Column Certificate Smoke

This is the first Phase 7 v3 smoke that satisfies the descriptor-source part of
Gate v3.1 without calling CPU scoreInfo in the candidate source.

It is not a broad replacement, not a performance candidate, and not permission
to use GASAL2 endpoint, CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate
phase7_broad_restart_v3_current_status = gate_v3_1_pass_attempt_overgenerate
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Validation Commands

```bash
make check-fasim-gasal2-phase7-v3-all-column-certificate-env
make check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke
make check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-certificate-smoke
```

## Runtime Smoke

The smoke uses NEAT1 first1 and enables:

```text
FASIM_GASAL2_PHASE7_V3_ALL_COLUMN_CERTIFICATE=1
```

Observed result:

```text
phase7_v3_all_column_certificate_runtime_smoke = scoreinfo_reducing_all_column_certificate
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
```

## Certificate Shape

The certificate covers every target end column.

For a target length `N`, the descriptor source emits:

```text
candidate scoreInfo descriptors = N
candidate attempt descriptors = N * (N + 1) / 2
```

The attempt descriptor set covers every target window.

That means any legacy scoreInfo position and any legacy-derived target window
is included by construction. Therefore this smoke can record:

```text
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls = 0
baseline_cpu_scoreinfo_calls > 0
cpu_scoreinfo_reduced = 1
```

## Interpretation

This is intentionally overgenerating and is not a performance candidate.

It proves a real pre-scoreInfo candidate-certificate source exists, but it
does not yet prove that the candidate set is small enough for CPU-authority
replay. CPU `aligner.Align()` remains the authority for score, endpoint,
traceback, CIGAR, output rows, and digest.

## Gate Status

```text
Gate v3.1:
  pass

Gate v3.2:
  not attempted
  not passed

NEAT1 first64 broad gate:
  not allowed

broad_replacement workload-matrix row:
  forbidden
```

Do not add a broad_replacement workload-matrix row from this smoke.

## Decision

```text
phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate
phase7_broad_restart_v3_current_status = gate_v3_1_pass_attempt_overgenerate
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate = all_column_certificate_cpu_replay_first1
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next valid step is CPU-authority replay on NEAT1 first1:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
```

If all-column replay cannot reduce Align-side attempts, this all-column
certificate is only a v3.1 scaffold and not a viable broad architecture.

## Replay Stop Update

The follow-up replay preflight is recorded in:

```text
docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md
phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go
candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
do_not_run_all_column_cpu_replay = 1
phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate
```

That stop checkpoint supersedes CPU replay as the next action. The all-column
certificate remains a Gate v3.1 proof only.
